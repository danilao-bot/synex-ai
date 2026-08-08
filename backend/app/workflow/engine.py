"""Synex Workflow Engine — orchestrates Skills-inspired Data Engineering stages."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from app.workflow.models import RunOutcome, WorkflowState
from app.workflow.stages.intent import IntentAnalyzer
from app.workflow.stages.search import SearchWorkflow
from app.workflow.stages.trust import TrustWorkflow
from app.workflow.stages.lineage import LineageWorkflow
from app.workflow.stages.quality import QualityWorkflow
from app.workflow.stages.enrichment import EnrichmentWorkflow
from app.workflow.stages.context_assembly import ContextAssemblyWorkflow
from app.workflow.stages.planning import PlanningWorkflow
from app.workflow.stages.generation import GenerationWorkflow
from app.workflow.stages.validation import ValidationWorkflow
from app.workflow.stages.self_critique import SelfCritiqueWorkflow
from app.workflow.stages.confidence import ConfidenceWorkflow
from app.workflow.stages.explanation import ExplanationWorkflow
from app.workflow.stages.approval import ApprovalWorkflow
from app.workflow.stages.writeback import WritebackWorkflow

logger = logging.getLogger(__name__)

EmitFn = Callable[[dict[str, Any]], None]


class WorkflowEngine:
    """Coordinates independent workflow modules. Not a giant function."""

    def __init__(self) -> None:
        self.stages = [
            IntentAnalyzer(),
            SearchWorkflow(),
            TrustWorkflow(),
            LineageWorkflow(),
            QualityWorkflow(),
            EnrichmentWorkflow(),
            ContextAssemblyWorkflow(),
            PlanningWorkflow(),
            GenerationWorkflow(),
            ValidationWorkflow(),
            SelfCritiqueWorkflow(),
            ConfidenceWorkflow(),
            ExplanationWorkflow(),
            ApprovalWorkflow(),
            WritebackWorkflow(),
        ]

    async def run(
        self,
        state: WorkflowState,
        emit: Optional[EmitFn] = None,
    ) -> WorkflowState:
        for index, stage in enumerate(self.stages):
            stage.bind(emit, index + 1)

            # Early exit: ambiguity — never guess
            if state.outcome == RunOutcome.NEEDS_CLARIFICATION:
                if stage.id not in ("intent",):
                    break

            await stage.run(state)

            if state.outcome == RunOutcome.NEEDS_CLARIFICATION:
                logger.info("Workflow paused for clarification on run %s", state.run_id)
                break
            if state.outcome == RunOutcome.FAILED:
                break

        if state.outcome == RunOutcome.SUCCESS and state.proposed_writeback.get("requires_approval"):
            state.outcome = RunOutcome.AWAITING_APPROVAL

        return state

    def build_result(self, state: WorkflowState) -> dict[str, Any]:
        """Assemble API response from workflow state."""
        selected = state.selected_candidate or {}
        eng = state.engineering_context
        status = state.outcome.value
        if status == RunOutcome.AWAITING_APPROVAL.value:
            status = "SUCCESS"  # API status enum compatibility; approval is separate

        result: dict[str, Any] = {
            "run_id": state.run_id,
            "status": status if status != "NEEDS_CLARIFICATION" else "NEEDS_CLARIFICATION",
            "outcome": state.outcome.value,
            "workflow_steps": state.step_dicts(),
            "intent": state.intent.to_dict() if state.intent else None,
            "clarifying_questions": state.clarifying_questions,
            "metadata_source": (
                getattr(state.enriched_ctx, "metadata_source", None)
                or state.search_source
                or "ack"
            ),
            "selected_dataset": selected,
            "candidate_datasets": state.candidate_evaluations,
            "schema_fields": (
                eng.schema_fields if eng else getattr(state.enriched_ctx, "schema_fields", []) or []
            ),
            "enriched_context": (
                state.enriched_ctx.to_dict() if state.enriched_ctx else None
            ),
            "engineering_context": eng.to_dict() if eng else None,
            "governance": {
                "pii_fields": selected.get("pii_fields") or (eng.pii_fields if eng else []),
                "deprecated": selected.get("is_deprecated", False),
                "risks": selected.get("upstream_risks") or [],
                "risk_level": state.intent.risk_level if state.intent else "medium",
            },
            "lineage_impact": state.lineage_report,
            "quality_report": state.quality_report,
            "enrichment": state.enrichment,
            "artifacts": {
                "sql": state.generated.get("sql", ""),
                "dbt_yaml": state.generated.get("dbt_yaml", ""),
                "dbt_tests": (state.generated.get("artifact_bundle") or {}).get("dbt_tests", []),
                "artifact_bundle": state.generated.get("artifact_bundle") or {},
                "documentation": state.generated.get("documentation", ""),
                "business_explanation": state.generated.get("business_explanation", ""),
                "confidence_explanation": state.generated.get("confidence_explanation", ""),
                "expected_output": state.generated.get("expected_output", ""),
                "potential_risks": state.generated.get("potential_risks", []),
                "sql_explanation": state.sql_explanation or state.generated.get("sql_explanation"),
            },
            "validation": state.validation,
            "proposed_writeback": state.proposed_writeback,
            "sql_explanation": state.sql_explanation,
            "self_critique": state.self_critique,
            "confidence": state.confidence,
            "observability": (
                state.observability.to_dict() if state.observability else None
            ),
            "context_package": (
                state.context_package.to_dict() if state.context_package else None
            ),
            "context_manifest": state.context_manifest,
            "engineering_memory": _finalize_memory(state),
            "trace_logs": [
                {
                    "step": i + 1,
                    "type": f"WORKFLOW_{s.id.upper()}",
                    "message": s.message,
                    "status": s.status.value if hasattr(s.status, "value") else s.status,
                    "duration_ms": s.duration_ms,
                    "stage": s.id,
                    "stage_label": s.label,
                }
                for i, s in enumerate(state.steps)
            ],
            "plan": state.plan,
            "session_memory_used": bool(
                state.previous_sql or (state.engineering_memory or {}).get("previous_sql")
            ),
            "warnings": state.global_warnings,
        }
        return result


def _finalize_memory(state: WorkflowState) -> dict[str, Any]:
    from app.memory.engineering_memory import build_engineering_memory

    return build_engineering_memory(
        prior_memory=state.engineering_memory,
        state_like={
            "selected_dataset": state.selected_candidate,
            "sql": (state.generated or {}).get("sql"),
            "validation": state.validation,
            "context_package": state.context_package.to_dict() if state.context_package else {},
            "lineage_impact": state.lineage_report,
            "proposed_writeback": state.proposed_writeback,
            "warnings": state.global_warnings,
            "engineering_memory": state.engineering_memory,
        },
    )


workflow_engine = WorkflowEngine()
