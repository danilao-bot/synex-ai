"""Explanation workflow — evidence-backed rationale after generation."""

from __future__ import annotations

from app.context.explanation import build_sql_explanation
from app.workflow.base import BaseStage
from app.workflow.models import WorkflowState, WorkflowStep


class ExplanationWorkflow(BaseStage):
    id = "explanation"
    label = "Explaining decisions"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        package = state.context_package
        if not package:
            step.complete(message="No context package — explanation skipped.", outputs={})
            return state

        explanation = build_sql_explanation(
            package,
            sql=(state.generated or {}).get("sql") or "",
            selected=state.selected_candidate,
            validation=state.validation,
            confidence=state.confidence,
            critique=state.self_critique,
        )
        state.sql_explanation = explanation
        if state.generated is not None:
            state.generated["sql_explanation"] = explanation
            state.generated["business_explanation"] = explanation.get("summary") or state.generated.get(
                "business_explanation"
            )

        step.complete(
            message=explanation.get("summary") or "Explanation ready.",
            outputs={
                "why_dataset": explanation.get("why_dataset"),
                "why_joins": explanation.get("why_joins"),
                "validation_summary": explanation.get("validation_summary"),
                "governance_summary": explanation.get("governance_summary"),
                "potential_risks": explanation.get("potential_risks"),
                "alternative_approaches": explanation.get("alternative_approaches"),
            },
            reasoning_summary=explanation.get("summary") or "",
            trust_score=(state.selected_candidate or {}).get("trust_score"),
        )
        return state
