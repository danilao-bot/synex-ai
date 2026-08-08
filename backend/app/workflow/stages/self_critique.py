"""Self-critique stage before confidence / explanation."""

from __future__ import annotations

from app.core.config import settings
from app.llm.critique import critique_artifacts
from app.workflow.base import BaseStage
from app.workflow.models import WorkflowState, WorkflowStep


class SelfCritiqueWorkflow(BaseStage):
    id = "self_critique"
    label = "Self evaluation"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        eng = state.engineering_context
        selected = state.selected_candidate or {}
        sql = (state.generated or {}).get("sql") or ""
        dbt_yaml = (state.generated or {}).get("dbt_yaml") or ""
        lineage_summary = (state.lineage_report or {}).get("safer_choice_reason") or ""

        critique = critique_artifacts(
            sql=sql,
            dbt_yaml=dbt_yaml,
            prompt=state.prompt,
            schema_fields=eng.schema_fields if eng else [],
            pii_fields=eng.pii_fields if eng else selected.get("pii_fields") or [],
            validation=state.validation or {},
            lineage_summary=lineage_summary,
            api_key=state.llm_api_key,
            provider=state.llm_provider,
            model=state.llm_model,
            use_llm=bool(settings.ENABLE_LLM_CRITIQUE and state.llm_api_key),
        )
        state.self_critique = critique

        # Light revision: if critique demands and validation passed but PII concern, flag warning
        if critique.get("needs_revision"):
            state.global_warnings.extend(critique.get("issues") or [])

        step.complete(
            message=(
                "Self-critique approved."
                if critique.get("approved")
                else f"Self-critique flags: {', '.join((critique.get('issues') or ['review needed'])[:3])}"
            ),
            outputs={
                "approved": critique.get("approved"),
                "needs_revision": critique.get("needs_revision"),
                "answers": critique.get("answers"),
                "issues": critique.get("issues"),
            },
            warnings=(critique.get("issues") or [])[:4] or None,
            reasoning_summary=critique.get("notes") or "",
        )
        return state
