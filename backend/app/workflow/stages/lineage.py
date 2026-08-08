"""Lineage workflow inspired by DataHub Lineage Skill."""

from __future__ import annotations

from app.workflow.base import BaseStage
from app.workflow.models import WorkflowState, WorkflowStep


class LineageWorkflow(BaseStage):
    id = "lineage"
    label = "Checking lineage"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        selected = state.selected_candidate or {}
        up = selected.get("upstream_nodes") or []
        down = selected.get("downstream_nodes") or []

        up_names = [n.get("name") or n.get("urn", "") for n in up]
        down_names = [n.get("name") or n.get("urn", "") for n in down]

        # Column lineage proxy from schema field paths (full column lineage when ACK provides edges)
        schema_fields = ((selected.get("raw_meta") or {}).get("schemaMetadata") or {}).get("fields") or []
        column_lineage = [
            {"field": f.get("fieldPath"), "nativeDataType": f.get("nativeDataType")}
            for f in schema_fields[:40]
        ]

        # Compare lineage across top candidates
        comparisons = []
        for e in (state.candidate_evaluations or [])[:3]:
            comparisons.append({
                "name": e.get("name"),
                "upstream_count": len(e.get("upstream_nodes") or []),
                "downstream_count": len(e.get("downstream_nodes") or e.get("downstream_impact_count") or []),
                "upstream_risks": e.get("upstream_risks") or [],
                "trust_score": e.get("trust_score"),
            })

        safer_reason = (
            f"'{selected.get('name')}' preferred: fewer upstream risks "
            f"({len(selected.get('upstream_risks') or [])}) and verified "
            f"{len(down)} downstream dependents."
        )
        if len(state.candidate_evaluations or []) > 1:
            alt = state.candidate_evaluations[1]
            if (alt.get("trust_score") or 0) < (selected.get("trust_score") or 0):
                safer_reason += (
                    f" Alternative '{alt.get('name')}' scored lower "
                    f"({alt.get('trust_score')}/100) with "
                    f"{len(alt.get('upstream_risks') or [])} upstream risk(s)."
                )

        dashboards = [n for n in down_names if "dashboard" in n.lower() or "chart" in n.lower()]
        truncated = len(down) >= 20
        impact = {
            "upstream": [u.get("urn") for u in up],
            "downstream": [d.get("urn") for d in down],
            "upstream_nodes": up,
            "downstream_nodes": down,
            "upstream_names": up_names,
            "downstream_names": down_names,
            "downstream_impact_count": len(down),
            "truncated": truncated,
            "upstream_risks": selected.get("upstream_risks") or [],
            "max_hops": 2,
            "column_lineage": column_lineage,
            "transformation_chain": up_names[:8] + [selected.get("name")] + down_names[:8],
            "affected_dashboards": dashboards,
            "affected_datasets": down_names,
            "potential_downstream_risks": (
                [f"High blast radius: {len(down)} dependents"] if len(down) >= 10 else []
            )
            + (selected.get("upstream_risks") or []),
            "comparisons": comparisons,
            "safer_choice_reason": safer_reason,
        }

        state.lineage_report = impact
        warnings = []
        if truncated:
            warnings.append("Downstream lineage truncated at display limit.")
        if impact["potential_downstream_risks"]:
            warnings.extend(impact["potential_downstream_risks"][:3])
            state.global_warnings.extend(warnings)

        step.complete(
            message=f"Lineage mapped: {len(up)} upstream, {len(down)} downstream.",
            outputs={
                "upstream_count": len(up),
                "downstream_count": len(down),
                "safer_choice_reason": safer_reason,
                "column_fields": len(column_lineage),
                "comparisons": comparisons,
            },
            reasoning_summary=safer_reason,
            warnings=warnings or None,
        )
        step.logs.append("Impact analysis complete.")
        return state
