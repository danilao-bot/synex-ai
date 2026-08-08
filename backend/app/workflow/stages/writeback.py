"""Write-back workflow stage — records proposal readiness; execution is approve-gated."""

from __future__ import annotations

from datetime import datetime, timezone

from app.workflow.base import BaseStage
from app.workflow.models import StepStatus, WorkflowState, WorkflowStep


class WritebackWorkflow(BaseStage):
    id = "writeback"
    label = "Awaiting write-back"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        """Does not emit mutations. Captures audit scaffold for later approval execution."""
        proposed = state.proposed_writeback or {}
        ops = proposed.get("operations") or []
        audit_log = []
        for o in ops:
            if isinstance(o, dict):
                audit_log.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "operator": "pending",
                    "run_id": state.run_id,
                    "affected_entity": o.get("target_urn") or proposed.get("target_urn"),
                    "mutation_type": o.get("op"),
                    "result": "pending_approval",
                    "preview": o.get("preview"),
                })

        state.proposed_writeback = {
            **proposed,
            "audit_log": audit_log,
            "writeback_stage": "proposal_ready",
        }

        step.status = StepStatus.WAITING
        step.complete(
            message="Write-back staged. Human approval required before DataHub mutations.",
            outputs={
                "pending_mutations": len(ops),
                "audit_log_entries": len(audit_log),
                "supported_ops": [
                    "update_description",
                    "add_tags",
                    "add_glossary_terms",
                    "set_domains",
                    "add_owners",
                    "save_document",
                ],
            },
            reasoning_summary="Governed write-back: Proposal → Preview → Approve → Execute → Audit.",
        )
        step.status = StepStatus.WAITING
        return state
