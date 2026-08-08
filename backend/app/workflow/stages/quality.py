"""Quality workflow inspired by DataHub Quality Skill."""

from __future__ import annotations

from app.workflow.base import BaseStage
from app.workflow.models import WorkflowState, WorkflowStep


class QualityWorkflow(BaseStage):
    id = "quality"
    label = "Evaluating quality"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        selected = state.selected_candidate or {}
        meta = selected.get("raw_meta") or {}
        signals = list(selected.get("quality_signals") or [])

        # Assertions / health from meta
        health = meta.get("health") or []
        if isinstance(health, dict):
            health = [health]
        for h in health:
            if h.get("type"):
                sig = f"{h.get('type')}: {h.get('status', 'OK')}"
                if sig not in signals:
                    signals.append(sig)

        schema_fields = (meta.get("schemaMetadata") or {}).get("fields") or []
        props = meta.get("properties") or meta.get("datasetProperties") or {}
        description = ""
        if isinstance(props, dict):
            description = props.get("description") or ""

        missing_docs = not description or len(description) < 20
        schema_health = "healthy" if len(schema_fields) >= 3 else "thin"
        broken_lineage = bool(selected.get("upstream_risks"))
        certified = bool(selected.get("is_certified"))
        deprecated = bool(selected.get("is_deprecated"))

        incidents = []
        for s in signals:
            su = s.upper()
            if any(x in su for x in ("FAIL", "ERROR", "WARN", "INCIDENT", "UNHEALTHY")):
                incidents.append(s)

        validation_status = "pass"
        if deprecated or incidents or broken_lineage:
            validation_status = "warn"
        if deprecated and not state.allow_deprecated_override:
            validation_status = "fail"

        confidence = selected.get("confidence") or (selected.get("trust_score", 50) / 100.0)
        low_confidence = confidence < 0.55 or (selected.get("trust_score") or 0) < 50

        report = {
            "assertions": signals,
            "quality_signals": signals,
            "freshness": "unknown" if not signals else "signaled",
            "incidents": incidents,
            "validation_status": validation_status,
            "certification": certified,
            "schema_health": schema_health,
            "schema_field_count": len(schema_fields),
            "missing_documentation": missing_docs,
            "broken_lineage": broken_lineage,
            "deprecated": deprecated,
            "low_confidence": low_confidence,
            "confidence": confidence,
        }
        state.quality_report = report

        warnings = []
        if low_confidence:
            warnings.append(
                "Quality/trust confidence is low — review candidates before relying on generated SQL."
            )
        if missing_docs:
            warnings.append("Selected dataset has missing or thin documentation.")
        if incidents:
            warnings.append(f"Quality incidents detected: {', '.join(incidents[:3])}")
        if broken_lineage:
            warnings.append("Upstream lineage risks present.")
        state.global_warnings.extend(warnings)

        step.complete(
            message=f"Quality status={validation_status}; confidence={confidence:.0%}.",
            outputs=report,
            warnings=warnings or None,
            reasoning_summary=(
                f"Schema {schema_health}, certified={certified}, "
                f"incidents={len(incidents)}, missing_docs={missing_docs}."
            ),
            trust_score=selected.get("trust_score"),
        )
        return state
