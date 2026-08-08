"""Build multi-aspect metadata write-back proposals (approval required)."""

from __future__ import annotations

from typing import Any, Optional

from app.services.datahub.models import EnrichedContext, MutationOp


def build_writeback_proposal(
    run_id: str,
    ctx: EnrichedContext,
    sql: str,
    dbt_yaml: str,
    validation_passed: bool,
) -> dict[str, Any]:
    """Create a structured multi-op proposal. Never executes mutations."""
    ops: list[MutationOp] = []

    contract = (
        f"### Synex Generated Contract\n\n"
        f"- **Synex Run ID:** `{run_id}`\n"
        f"- **Source URN:** `{ctx.urn}`\n"
        f"- **Metadata Source:** `{ctx.metadata_source}`\n"
        f"- **Governance Validation:** {'Passed' if validation_passed else 'Failed'}\n"
        f"- **PII Decision:** SHA2 hashing on {', '.join(ctx.pii_fields) or 'n/a'}\n"
        f"- **Model preview (SQL excerpt):**\n```sql\n{sql[:600]}\n```\n"
    )
    ops.append(
        MutationOp(
            op="update_description",
            target_urn=ctx.urn,
            params={"description": contract, "operation": "append"},
            preview="Append Synex Generated Contract block to dataset description",
        )
    )

    # Propose governance tags when PII was handled
    if ctx.pii_fields:
        ops.append(
            MutationOp(
                op="add_tags",
                target_urn=ctx.urn,
                params={"tag_urns": ["urn:li:tag:synex_pii_masked"]},
                preview="Add tag synex_pii_masked (PII columns hashed in generated model)",
            )
        )

    ops.append(
        MutationOp(
            op="add_tags",
            target_urn=ctx.urn,
            params={"tag_urns": ["urn:li:tag:synex_generated"]},
            preview="Add tag synex_generated",
        )
    )

    return {
        "requires_approval": True,
        "target_urn": ctx.urn,
        "operations": [op.to_dict() for op in ops],
        "operation_labels": [op.preview or op.op for op in ops],
        "summary": (
            f"Proposed {len(ops)} DataHub metadata mutation(s) for '{ctx.urn}' "
            f"via Agent Context Kit / MCP tools. Requires POST /api/v1/runs/{run_id}/writeback/approve."
        ),
        "dbt_yaml_preview": dbt_yaml[:500] if dbt_yaml else "",
    }
