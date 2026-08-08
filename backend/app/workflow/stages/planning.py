"""Planning workflow — visible reasoning plan before generation."""

from __future__ import annotations

from app.workflow.base import BaseStage
from app.workflow.models import WorkflowState, WorkflowStep


class PlanningWorkflow(BaseStage):
    id = "planning"
    label = "Planning SQL"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        selected = state.selected_candidate or {}
        eng = state.engineering_context
        intent = state.intent
        pii = (eng.pii_fields if eng else selected.get("pii_fields")) or []

        plan = [
            {
                "step": 1,
                "type": "UNDERSTAND_REQUEST",
                "description": f"Interpret intent '{intent.intent if intent else 'generate'}' for prompt.",
            },
            {
                "step": 2,
                "type": "IDENTIFY_DATASETS",
                "description": f"Use canonical dataset '{selected.get('name')}' ({selected.get('urn')}).",
            },
            {
                "step": 3,
                "type": "VERIFY_GOVERNANCE",
                "description": (
                    f"Trust {selected.get('trust_score')}/100; "
                    f"certified={selected.get('is_certified')}; deprecated={selected.get('is_deprecated')}."
                ),
            },
            {
                "step": 4,
                "type": "DETERMINE_JOINS",
                "description": (
                    f"Recommended joins: {', '.join((eng.recommended_joins if eng else [])[:2]) or 'none required'}."
                ),
            },
            {
                "step": 5,
                "type": "DETERMINE_FILTERS",
                "description": "Apply domain/business filters implied by the user prompt.",
            },
            {
                "step": 6,
                "type": "DETERMINE_AGGREGATIONS",
                "description": "Aggregate only when the prompt requests metrics (sum/count/avg).",
            },
            {
                "step": 7,
                "type": "DETERMINE_DBT_MODEL",
                "description": f"Generate dialect={state.target_dialect} dbt model SQL.",
            },
            {
                "step": 8,
                "type": "DETERMINE_SCHEMA_YML",
                "description": "Emit schema.yml with tests for keys and PII-safe columns.",
            },
            {
                "step": 9,
                "type": "DETERMINE_VALIDATION_STRATEGY",
                "description": (
                    f"SQLGlot + DuckDB + schema/PII checks; mask columns: {', '.join(pii) or 'n/a'}."
                ),
            },
        ]
        state.plan = plan
        if eng:
            eng.plan = plan
            state.engineering_context = eng

        step.complete(
            message=f"Engineering plan ready ({len(plan)} steps).",
            outputs={"plan": plan},
            reasoning_summary="Visible plan constructed before any LLM generation.",
        )
        return state
