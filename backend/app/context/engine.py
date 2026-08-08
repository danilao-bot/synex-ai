"""Engineering Context Engine — sole knowledge source for the Generator."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.context.compress import compress_package
from app.context.models import ContextManifest, ContextPackage, RankedContextItem
from app.context.pattern_library import PatternLibrary
from app.context.ranking import rank_and_filter, score_item
from app.context.sql_profiler import profile_queries
from app.context.vocabulary import resolve_vocabulary, vocabulary_prompt_block
from app.services.datahub import datahub_service

logger = logging.getLogger(__name__)


class ContextEngine:
    """
    Discover → rank → merge → dedupe → compress.
    The LLM must never search DataHub; only this engine may.
    """

    async def build(
        self,
        *,
        prompt: str,
        selected: dict[str, Any],
        enriched: Any,
        lineage_report: dict[str, Any] | None = None,
        quality_report: dict[str, Any] | None = None,
        candidate_evaluations: list[dict[str, Any]] | None = None,
        engineering_memory: dict[str, Any] | None = None,
        validation_rules: list[str] | None = None,
        global_warnings: list[str] | None = None,
    ) -> ContextPackage:
        lineage_report = lineage_report or {}
        quality_report = quality_report or {}
        candidate_evaluations = candidate_evaluations or []
        engineering_memory = engineering_memory or {}
        validation_rules = validation_rules or []
        global_warnings = list(global_warnings or [])

        urn = selected.get("urn") or getattr(enriched, "urn", "")
        name = selected.get("name") or getattr(enriched, "name", "")
        trust = float(selected.get("trust_score") or 50)
        source = getattr(enriched, "metadata_source", None) or "ack"
        is_certified = bool(selected.get("is_certified") or getattr(enriched, "is_certified", False))
        is_deprecated = bool(selected.get("is_deprecated") or getattr(enriched, "is_deprecated", False))

        # --- Mandatory production query intelligence ---
        queries = list(getattr(enriched, "sample_queries", None) or [])
        if urn:
            try:
                more = await datahub_service.get_dataset_queries(urn)
                for q in more or []:
                    if q and q not in queries:
                        queries.append(q)
            except Exception as exc:
                logger.debug("get_dataset_queries refresh failed: %s", exc)
                global_warnings.append("Production query retrieval partially unavailable.")

        sql_profile = profile_queries(queries)
        library = PatternLibrary()
        library.ingest_profile(sql_profile)
        library.ingest_memory(engineering_memory)

        # --- Documentation intelligence (search + grep) ---
        docs = list(getattr(enriched, "documents", None) or [])
        try:
            searched = await datahub_service.search_documents(prompt)
            for d in searched or []:
                if d and d not in docs:
                    docs.append(d)
        except Exception:
            pass
        try:
            grepped = await datahub_service.grep_documents(prompt)
            for d in grepped or []:
                if d and d not in docs:
                    docs.append(d)
        except Exception:
            pass

        # --- Institutional memory ---
        memory = list(getattr(enriched, "institutional_memory", None) or [])
        if is_deprecated:
            memory.append("Dataset is DEPRECATED — prefer alternate certified assets when available.")
        if selected.get("upstream_risks"):
            memory.extend([f"Known issue: {r}" for r in selected["upstream_risks"][:3]])

        # --- Ownership intelligence ---
        owners = list(getattr(enriched, "owners", None) or selected.get("owners") or [])
        ownership = self._ownership_bundle(owners, selected)

        # --- Glossary + business definitions ---
        glossary_terms = list(getattr(enriched, "glossary_terms", None) or selected.get("glossary_terms") or [])
        glossary = [{"name": t, "definition": t} for t in glossary_terms]
        business_definitions = [f"{t} (approved glossary term)" for t in glossary_terms]

        domain = getattr(enriched, "domain", None) or selected.get("domain")
        schema_fields = list(getattr(enriched, "schema_fields", None) or [])
        pii_fields = list(selected.get("pii_fields") or getattr(enriched, "pii_fields", None) or [])

        vocabulary = resolve_vocabulary(
            prompt,
            glossary_terms=glossary_terms,
            schema_fields=schema_fields,
            dataset_name=name,
            domain=domain,
        )

        # --- Rank every knowledge item ---
        ownership_conf = 0.9 if owners else 0.2
        quality_score = 70.0 if (quality_report.get("validation_status") == "pass") else 40.0
        glossary_cov = min(100.0, 20.0 * len(glossary_terms))
        lineage_conf = float((selected.get("trust_dimensions") or {}).get("lineage_confidence") or 50)
        popularity = min(100.0, 20.0 + 5.0 * int(lineage_report.get("downstream_impact_count") or 0))

        items: list[RankedContextItem] = []
        for q in queries[:8]:
            items.append(
                score_item(
                    "production_sql",
                    q,
                    prompt,
                    trust_score=trust,
                    is_certified=is_certified,
                    is_deprecated=is_deprecated,
                    ownership_confidence=ownership_conf,
                    quality_score=quality_score,
                    glossary_coverage=glossary_cov,
                    lineage_confidence=lineage_conf,
                    popularity=popularity,
                    source=source,
                )
            )
        for d in docs[:10]:
            items.append(
                score_item(
                    "document",
                    d,
                    prompt,
                    trust_score=trust,
                    is_certified=is_certified,
                    is_deprecated=is_deprecated,
                    ownership_confidence=ownership_conf,
                    quality_score=quality_score,
                    glossary_coverage=glossary_cov,
                    lineage_confidence=lineage_conf,
                    popularity=popularity,
                    source=source,
                )
            )
        for m in memory[:8]:
            items.append(
                score_item(
                    "memory",
                    m,
                    prompt,
                    trust_score=trust,
                    is_certified=is_certified,
                    is_deprecated=is_deprecated,
                    ownership_confidence=ownership_conf,
                    quality_score=quality_score,
                    glossary_coverage=glossary_cov,
                    lineage_confidence=lineage_conf,
                    popularity=popularity,
                    source=source,
                )
            )
        for g in glossary_terms:
            items.append(
                score_item(
                    "glossary",
                    g,
                    prompt,
                    trust_score=trust,
                    is_certified=is_certified,
                    ownership_confidence=ownership_conf,
                    quality_score=quality_score,
                    glossary_coverage=glossary_cov,
                    lineage_confidence=lineage_conf,
                    popularity=popularity,
                    source=source,
                )
            )
        if ownership.get("summary"):
            items.append(
                score_item(
                    "ownership",
                    ownership["summary"],
                    prompt,
                    trust_score=trust,
                    ownership_confidence=ownership_conf,
                    quality_score=quality_score,
                    source=source,
                )
            )
        for sig in (getattr(enriched, "quality_signals", None) or quality_report.get("quality_signals") or [])[:6]:
            items.append(
                score_item(
                    "quality",
                    str(sig),
                    prompt,
                    trust_score=trust,
                    quality_score=quality_score,
                    source=source,
                )
            )
        safer = lineage_report.get("safer_choice_reason")
        if safer:
            items.append(
                score_item(
                    "lineage",
                    safer,
                    prompt,
                    trust_score=trust,
                    lineage_confidence=lineage_conf,
                    popularity=popularity,
                    source=source,
                )
            )

        # Dedupe by content prefix
        deduped: list[RankedContextItem] = []
        seen: set[str] = set()
        for it in items:
            key = f"{it.kind}:{it.content[:160].lower()}"
            if key in seen:
                continue
            seen.add(key)
            deduped.append(it)

        kept, dropped = rank_and_filter(deduped, min_score=35.0, limit=40)

        recommended_joins = list(sql_profile.common_joins[:6])
        for up in (lineage_report.get("upstream_names") or [])[:4]:
            hint = f"Upstream dependency candidate join: {up}"
            if hint not in recommended_joins:
                recommended_joins.append(hint)

        lineage_nodes = len(lineage_report.get("upstream") or []) + len(lineage_report.get("downstream") or [])
        manifest = ContextManifest(
            candidate_datasets=len(candidate_evaluations) or 1,
            production_sql_examples=len(queries),
            glossary_definitions=len(glossary_terms),
            ownership_records=len(owners),
            documentation_pages=len(docs),
            institutional_memory_entries=len(memory),
            lineage_nodes=lineage_nodes,
            quality_signals=len(getattr(enriched, "quality_signals", None) or []),
            vocabulary_mappings=len(vocabulary),
            trust_score=trust,
            context_items_kept=len(kept),
            context_items_dropped=len(dropped),
        )
        manifest.items = manifest.to_checklist()

        trust_breakdown = {
            "overall": trust,
            "risk_score": selected.get("risk_score"),
            "dimensions": selected.get("trust_dimensions"),
            "recommendation": selected.get("recommendation"),
        }

        compressed = compress_package(
            prompt=prompt,
            selected_name=name,
            selected_urn=urn,
            schema_fields=schema_fields,
            pii_fields=pii_fields,
            sql_profile=sql_profile,
            pattern_library=library,
            vocabulary_block=vocabulary_prompt_block(vocabulary),
            kept_items=kept,
            ownership=ownership,
            domain=domain,
            trust_breakdown=trust_breakdown,
            warnings=global_warnings,
            lineage_summary=(
                f"up={len(lineage_report.get('upstream') or [])} "
                f"down={len(lineage_report.get('downstream') or [])}; "
                f"{safer or ''}"
            ),
            quality_summary=str(quality_report.get("validation_status") or "unknown"),
            validation_rules=validation_rules,
            engineering_memory=engineering_memory,
        )

        rankings = [
            {
                "name": e.get("name"),
                "urn": e.get("urn"),
                "trust_score": e.get("trust_score"),
                "recommendation": e.get("recommendation"),
                "why": (e.get("rank_explanation") or e.get("selection_reasons") or [])[:3],
            }
            for e in candidate_evaluations[:8]
        ]

        knowledge_refs = []
        knowledge_refs.extend([f"sql:{i+1}" for i in range(min(3, len(queries)))])
        knowledge_refs.extend([f"doc:{d[:40]}" for d in docs[:3]])
        knowledge_refs.extend([f"glossary:{g}" for g in glossary_terms[:4]])

        reasoning = (
            f"Context Engine assembled package from ACK/MCP: "
            f"{len(queries)} queries, {len(docs)} docs, {len(glossary_terms)} glossary, "
            f"{len(owners)} owners; kept {len(kept)} ranked items."
        )

        return ContextPackage(
            prompt=prompt,
            selected_urn=urn,
            selected_name=name,
            metadata_source=str(source),
            sql_profile=sql_profile,
            vocabulary=vocabulary,
            ranked_items=kept,
            compressed_prompt_block=compressed,
            manifest=manifest,
            ownership=ownership,
            glossary=glossary,
            documents=docs[:12],
            institutional_memory=memory[:12],
            domain=domain,
            business_definitions=business_definitions,
            recommended_joins=recommended_joins,
            pattern_library_hints=library.hints(),
            trust_breakdown=trust_breakdown,
            context_sources=list({source, "context_engine", "sql_profiler", "pattern_library"}),
            knowledge_references=knowledge_refs,
            dataset_rankings=rankings,
            reasoning_summary=reasoning,
            schema_fields=schema_fields,
            pii_fields=pii_fields,
            warnings=global_warnings,
            engineering_memory=engineering_memory,
        )

    @staticmethod
    def _ownership_bundle(owners: list[str], selected: dict[str, Any]) -> dict[str, Any]:
        # Roles are inferred lightly — DataHub may only expose flat owners
        bundle = {
            "dataset_owner": owners[0] if owners else None,
            "steward": owners[1] if len(owners) > 1 else owners[0] if owners else None,
            "engineering_team": owners[0] if owners else None,
            "business_owner": owners[-1] if owners else None,
            "platform_owner": None,
            "domain_owner": selected.get("domain"),
            "all_owners": owners,
            "summary": (
                f"Owners: {', '.join(owners)}; domain={selected.get('domain')}"
                if owners
                else f"No owners assigned; domain={selected.get('domain')}"
            ),
            "confidence": 0.9 if owners else 0.2,
        }
        return bundle


context_engine = ContextEngine()
