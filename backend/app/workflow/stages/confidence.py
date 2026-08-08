"""Confidence analysis stage."""

from __future__ import annotations

from app.llm.confidence import compute_confidence
from app.llm.observability import ObservabilityMetrics
from app.workflow.base import BaseStage
from app.workflow.models import WorkflowState, WorkflowStep


class ConfidenceWorkflow(BaseStage):
    id = "confidence"
    label = "Confidence analysis"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        metrics = state.observability or ObservabilityMetrics()
        state.observability = metrics

        confidence = compute_confidence(
            selected=state.selected_candidate,
            validation=state.validation,
            context_package=state.context_package,
            engineering_memory=state.engineering_memory,
            critique=state.self_critique,
            retry_count=metrics.retry_count,
        )
        state.confidence = confidence
        metrics.confidence = confidence.get("score")

        if state.generated is not None:
            state.generated["confidence_explanation"] = confidence.get("summary")
            state.generated["confidence"] = confidence

        if self._emit:
            self._emit({
                "step": self._step_index,
                "type": "CONFIDENCE",
                "stage": "confidence",
                "status": "completed",
                "message": confidence.get("summary"),
                "confidence": confidence.get("score"),
                "level": confidence.get("level"),
            })

        step.complete(
            message=confidence.get("summary") or f"Confidence {confidence.get('score')}/100",
            outputs=confidence,
            reasoning_summary=confidence.get("summary") or "",
            trust_score=(state.selected_candidate or {}).get("trust_score"),
        )
        return state
