"""Trust evaluation engine — multi-dimensional scoring before generation."""

from __future__ import annotations

from typing import Any

from app.agent.context_reasoner import context_reasoner
from app.services.datahub import datahub_service
from app.workflow.base import BaseStage
from app.workflow.models import TrustDimensions, WorkflowState, WorkflowStep

# Minimum overall trust to pass into SQL generation
MIN_TRUST_FOR_GENERATION = 40


class TrustWorkflow(BaseStage):
    id = "trust"
    label = "Evaluating trust"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        evaluations: list[dict[str, Any]] = []

        for cand in state.raw_candidates:
            urn = cand.get("urn", "")
            if not urn:
                continue
            meta, _ = await datahub_service.get_entity(urn)
            up_nodes = await datahub_service.get_lineage(urn, upstream=True, max_hops=2)
            down_nodes = await datahub_service.get_lineage(urn, upstream=False, max_hops=2)

            base = context_reasoner.evaluate_candidate(
                meta, state.prompt, upstream_nodes=up_nodes, downstream_nodes=down_nodes
            )

            dims = self._dimensions(meta, base, state, up_nodes, down_nodes)
            overall = dims.overall()
            # Blend with legacy score for continuity
            blended = round(0.55 * base["trust_score"] + 0.45 * overall, 1)
            risk_score = round(100 - blended, 1)

            recommendation = "use"
            if base["is_deprecated"]:
                recommendation = "reject"
            elif blended < MIN_TRUST_FOR_GENERATION:
                recommendation = "caution"
            elif blended >= 75:
                recommendation = "preferred"

            rank_why = list(base.get("selection_reasons") or [])
            if dims.certification >= 80:
                rank_why.insert(0, "High certification dimension.")
            if dims.business_relevance >= 70:
                rank_why.append("Strong business relevance to prompt.")
            if dims.popularity >= 60:
                rank_why.append("Downstream popularity indicates active usage.")

            eval_row = {
                **base,
                "trust_score": blended,
                "trust_dimensions": dims.to_dict(),
                "risk_score": risk_score,
                "recommendation": recommendation,
                "rank_explanation": rank_why or base.get("rejection_reasons") or ["Scored from DataHub graph signals."],
                "confidence": min(0.99, blended / 100.0),
                "search_rank": cand.get("_search_rank"),
                "upstream_nodes": up_nodes,
                "downstream_nodes": down_nodes,
                "raw_meta": meta,
            }
            evaluations.append(eval_row)
            step.logs.append(
                f"Ranked {base.get('name')}: trust={blended} risk={risk_score} rec={recommendation}"
            )

        if not evaluations:
            raise RuntimeError("No evaluable DataHub candidates after trust enrichment.")

        evaluations.sort(key=lambda x: x["trust_score"], reverse=True)
        state.candidate_evaluations = evaluations

        # Prefer non-deprecated high-trust; never feed low-trust into generator unless override
        trusted = [e for e in evaluations if e["recommendation"] in ("preferred", "use") and not e["is_deprecated"]]
        if not trusted and state.allow_deprecated_override:
            trusted = evaluations[:1]
        if not trusted:
            # Still select top but warn heavily
            selected = evaluations[0]
            state.global_warnings.append(
                f"No high-trust candidates; proceeding with '{selected.get('name')}' "
                f"(trust {selected['trust_score']}) under caution."
            )
        else:
            selected = trusted[0]

        state.selected_candidate = selected
        step.complete(
            message=(
                f"Selected '{selected.get('name')}' "
                f"(Trust {selected['trust_score']}/100, Risk {selected['risk_score']}/100)."
            ),
            outputs={
                "selected_urn": selected.get("urn"),
                "selected_name": selected.get("name"),
                "trust_score": selected["trust_score"],
                "risk_score": selected["risk_score"],
                "recommendation": selected["recommendation"],
                "dimensions": selected.get("trust_dimensions"),
                "rankings": [
                    {
                        "name": e.get("name"),
                        "trust_score": e["trust_score"],
                        "recommendation": e["recommendation"],
                        "why": (e.get("rank_explanation") or [])[:3],
                    }
                    for e in evaluations
                ],
            },
            reasoning_summary="; ".join((selected.get("rank_explanation") or [])[:3]),
            trust_score=selected["trust_score"],
            warnings=state.global_warnings[-1:] if state.global_warnings else None,
        )
        return state

    def _dimensions(
        self,
        meta: dict[str, Any],
        base: dict[str, Any],
        state: WorkflowState,
        up_nodes: list,
        down_nodes: list,
    ) -> TrustDimensions:
        fields = (meta.get("schemaMetadata") or {}).get("fields") or []
        desc = ""
        props = meta.get("properties") or meta.get("datasetProperties") or {}
        if isinstance(props, dict):
            desc = props.get("description") or ""

        docs_score = 80.0 if len(desc) > 40 else (40.0 if desc else 10.0)
        schema_score = min(100.0, 20.0 + len(fields) * 5.0)
        ownership_score = 90.0 if base.get("owners") else 15.0
        cert_score = 95.0 if base.get("is_certified") else 25.0
        glossary_score = min(100.0, 20.0 + 25.0 * len(base.get("glossary_terms") or []))
        quality_score = 70.0 if base.get("quality_signals") else 35.0
        # Freshness proxy: non-deprecated + health
        freshness = 30.0 if base.get("is_deprecated") else 65.0
        if base.get("quality_signals"):
            freshness = min(100.0, freshness + 20.0)
        popularity = min(100.0, 20.0 + 8.0 * len(down_nodes))
        lineage_conf = min(100.0, 40.0 + 5.0 * len(up_nodes) + 3.0 * len(down_nodes))
        if base.get("upstream_risks"):
            lineage_conf = max(0.0, lineage_conf - 25.0)
        pii_gov = 50.0
        if base.get("pii_fields"):
            pii_gov = 75.0  # identified — can be governed
        usage = min(100.0, 25.0 + 10.0 * len(down_nodes))

        # Business relevance from intent domain / keywords
        relevance = 40.0
        intent = state.intent
        if intent and intent.business_domain and base.get("domain"):
            if intent.business_domain.lower() in str(base.get("domain")).lower():
                relevance = 90.0
            else:
                relevance = 45.0
        if intent and intent.target_dataset_hint:
            if intent.target_dataset_hint.lower() in (base.get("name") or "").lower():
                relevance = max(relevance, 95.0)
        matched = base.get("selection_reasons") or []
        if any("Matched" in r for r in matched):
            relevance = max(relevance, 80.0)

        return TrustDimensions(
            ownership=ownership_score,
            certification=cert_score,
            documentation=docs_score,
            quality=quality_score,
            freshness=freshness,
            popularity=popularity,
            schema_completeness=schema_score,
            pii_governance=pii_gov,
            glossary_coverage=glossary_score,
            business_relevance=relevance,
            lineage_confidence=lineage_conf,
            usage_statistics=usage,
        )
