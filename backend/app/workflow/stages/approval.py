"""Approval workflow — proposal → preview → await human approval."""

from __future__ import annotations

from app.services.datahub.mutations import build_writeback_proposal
from app.workflow.base import BaseStage
from app.workflow.models import RunOutcome, StepStatus, WorkflowState, WorkflowStep


class ApprovalWorkflow(BaseStage):
    id = "approval"
    label = "Preparing metadata proposal"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        enriched = state.enriched_ctx
        if not enriched:
            raise RuntimeError("Missing enriched context for approval proposal.")

        proposed = build_writeback_proposal(
            run_id=state.run_id,
            ctx=enriched,
            sql=state.generated.get("sql") or "",
            dbt_yaml=state.generated.get("dbt_yaml") or "",
            validation_passed=bool((state.validation or {}).get("passed")),
        )

        # Merge enrichment-only proposals that are not yet in ops
        enrichment_props = (state.enrichment or {}).get("metadata_proposals") or []
        existing_ops = {o.get("op") for o in proposed.get("operations") or [] if isinstance(o, dict)}
        for p in enrichment_props:
            if p.get("op") == "update_description" and "update_description" in existing_ops:
                continue
            # Tag proposals already covered by build_writeback_proposal
            if p.get("op") == "add_tags":
                continue

        proposed["approval_state"] = "awaiting_human"
        proposed["preview"] = {
            "operations": [
                (o.get("preview") if isinstance(o, dict) else str(o))
                for o in (proposed.get("operations") or [])
            ],
            "target_urn": proposed.get("target_urn"),
            "requires_approval": True,
        }
        proposed["audit"] = {
            "run_id": state.run_id,
            "mutation_gate": "human_approval_required",
            "auto_execute": False,
        }
        state.proposed_writeback = proposed
        state.outcome = RunOutcome.AWAITING_APPROVAL

        step.status = StepStatus.WAITING
        step.complete(
            message=f"Proposed {len(proposed.get('operations') or [])} mutation(s). Awaiting human approval.",
            outputs=proposed["preview"],
            reasoning_summary="No metadata mutations execute until POST writeback/approve.",
        )
        # Mark as waiting for UI
        step.status = StepStatus.WAITING
        return state
