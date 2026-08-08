"""Base stage interface for Synex workflow modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional

from app.workflow.models import WorkflowState, WorkflowStep


EmitFn = Callable[[dict[str, Any]], None]


class BaseStage(ABC):
    """Independent workflow stage with structured start/complete/fail lifecycle."""

    id: str = "stage"
    label: str = "Stage"

    def __init__(self) -> None:
        self._emit: Optional[EmitFn] = None
        self._step_index: int = 0

    def bind(self, emit: Optional[EmitFn], step_index: int) -> None:
        self._emit = emit
        self._step_index = step_index

    def _emit_step(self, step: WorkflowStep) -> None:
        if self._emit:
            self._emit(step.to_sse_event(self._step_index))

    async def run(self, state: WorkflowState) -> WorkflowState:
        step = WorkflowStep(id=self.id, name=self.id, label=self.label)
        state.steps.append(step)
        step.start(f"{self.label} started")
        self._emit_step(step)
        try:
            state = await self.execute(state, step)
            if step.status.value == "running":
                step.complete(message=f"{self.label} completed")
            self._emit_step(step)
            return state
        except Exception as exc:
            step.fail(str(exc))
            self._emit_step(step)
            raise

    @abstractmethod
    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        ...
