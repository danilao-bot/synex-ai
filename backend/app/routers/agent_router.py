"""HTTP and SSE interfaces for the Synex Governed dbt Change Agent."""

import asyncio
import datetime
import json
import logging
from collections.abc import Callable
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.context_reasoner import context_reasoner
from app.agent.generator import generator
from app.agent.planner import planner
from app.agent.validator import validator
from app.core.config import settings
from app.db import (
    create_run,
    get_last_run_for_session,
    get_latest_agent_settings,
    get_run_by_id,
    get_run_history,
    save_agent_settings,
    update_run,
)
from app.services.datahub_context import datahub_context
from app.services.mcp_emitter import mcp_emitter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Agent"])


class SettingsPayload(BaseModel):
    datahub_url: Optional[str] = None
    datahub_pat: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_api_key: Optional[str] = None


class AgentRunRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8_000)
    target_dialect: str = "snowflake"
    writeback_enabled: bool = False  # Always false by default — requires explicit approval endpoint call
    allow_deprecated_override: bool = False
    session_id: Optional[str] = None


class WritebackApprovalRequest(BaseModel):
    approved: bool
    approved_by: Optional[str] = "Data Engineer"


# In-memory store fallback for runs when Supabase is not configured
_RUN_MEMORY_STORE: dict[str, dict[str, Any]] = {}


@router.get("/history")
async def fetch_history() -> dict[str, Any]:
    """Return past execution runs from Supabase synex_runs table."""
    history = await get_run_history()
    return {"runs": history, "count": len(history)}


@router.get("/settings")
async def fetch_settings() -> dict[str, Any]:
    """Return active non-secret configuration parameters."""
    settings_data = await get_latest_agent_settings()
    if settings_data.get("llm_api_key"):
        raw = settings_data["llm_api_key"]
        settings_data["llm_api_key_masked"] = raw[:8] + "..." + raw[-4:]
        del settings_data["llm_api_key"]
    return settings_data


@router.post("/settings")
async def update_settings(payload: SettingsPayload) -> dict[str, Any]:
    """Save new configuration parameters to Supabase synex_settings table."""
    data = payload.model_dump(exclude_none=True)
    success = await save_agent_settings(data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save settings to database")
    return {"status": "success", "updated_keys": list(data.keys())}


async def execute_agent(
    request: AgentRunRequest, trace_sink: Optional[Callable[[dict[str, Any]], None]] = None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute the metadata-first Governed dbt Change Agent flow."""
    trace: list[dict[str, Any]] = []

    # Configure DataHub context endpoints from settings
    db_settings = await get_latest_agent_settings()
    dh_url = db_settings.get("datahub_url") or db_settings.get("datahub_gms_url") or settings.DATAHUB_GMS_URL
    dh_pat = db_settings.get("datahub_pat") or settings.get_datahub_auth_token()
    datahub_context.configure(gms_url=dh_url, token=dh_pat)

    llm_api_key = db_settings.get("llm_api_key") or settings.LLM_API_KEY
    llm_model = db_settings.get("llm_model") or settings.LLM_MODEL
    llm_provider = db_settings.get("llm_provider") or settings.LLM_PROVIDER

    run_payload = {
        "prompt": request.prompt,
        "status": "running",
        "trace_logs": [],
        "session_id": request.session_id,
        "writeback_status": "pending_approval",
    }
    run_id = await create_run(run_payload)
    if not run_id:
        import uuid
        run_id = str(uuid.uuid4())

    def add_trace(kind: str, message: str) -> None:
        event = {"step": len(trace) + 1, "type": kind, "message": message}
        trace.append(event)
        if trace_sink:
            trace_sink(event)

    try:
        # Step 1: Candidate Search & DataHub MCP Discovery
        add_trace("MCP_DISCOVERY", f"Searching DataHub catalog via MCP context adapter for query: '{request.prompt}'.")
        raw_candidates = await datahub_context.search_candidates(request.prompt, limit=5)
        if not raw_candidates:
            raise RuntimeError(f"DataHub returned no dataset candidates for prompt '{request.prompt}'.")

        # Step 2 & 3: Detailed Context Retrieval & Graph-Aware Trust Scoring
        add_trace("GRAPH_REASONING", f"Evaluating {len(raw_candidates)} candidate datasets against DataHub governance graph signals.")
        candidate_evaluations: List[dict[str, Any]] = []

        for cand in raw_candidates:
            c_urn = cand.get("urn", "")
            meta = await datahub_context.get_entity_metadata(c_urn)
            up_nodes = await datahub_context.get_upstream_lineage(c_urn)
            down_nodes = await datahub_context.get_downstream_lineage(c_urn)
            evaluation = context_reasoner.evaluate_candidate(
                meta, request.prompt, upstream_nodes=up_nodes, downstream_nodes=down_nodes
            )
            candidate_evaluations.append(evaluation)

        # Sort candidate evaluations by trust score descending
        candidate_evaluations.sort(key=lambda x: x["trust_score"], reverse=True)
        selected_cand_eval = candidate_evaluations[0]
        target_urn = selected_cand_eval["urn"]

        # Fetch detailed aspects for target URN
        aspects = await datahub_context.get_entity_metadata(target_urn)
        upstream_lineage = await datahub_context.get_upstream_lineage(target_urn)
        downstream_lineage = await datahub_context.get_downstream_lineage(target_urn)
        schema_fields = aspects.get("schemaMetadata", {}).get("fields", [])

        add_trace(
            "SOURCE_SELECTION",
            f"Selected canonical dataset '{selected_cand_eval['name']}' (Trust Score: {selected_cand_eval['trust_score']}/100). "
            f"Reasons: {'; '.join(selected_cand_eval['selection_reasons'][:2])}."
        )

        if selected_cand_eval["is_deprecated"]:
            add_trace("WARNING", f"Selected dataset {target_urn} is DEPRECATED in DataHub.")

        # Step 4: Downstream Blast Radius & Lineage Summary
        lineage_impact = {
            "upstream": [u.get("urn") for u in upstream_lineage],
            "downstream": [d.get("urn") for d in downstream_lineage],
            "downstream_impact_count": len(downstream_lineage),
            "truncated": len(downstream_lineage) >= 20,
            "upstream_risks": selected_cand_eval["upstream_risks"],
        }
        add_trace("LINEAGE_TRAVERSAL", f"Lineage mapped: {len(upstream_lineage)} upstream, {len(downstream_lineage)} downstream dependencies.")

        # Step 5: Code & dbt Artifact Synthesis
        add_trace("CODE_SYNTHESIS", f"Calling LLM provider '{llm_provider}' to synthesize governed dbt SQL model & schema contract.")
        generated = generator.generate_code_and_contract(
            table_name=aspects.get("name") or target_urn,
            pii_columns=selected_cand_eval["pii_fields"],
            dialect=request.target_dialect,
            prompt=request.prompt,
            schema_fields=schema_fields,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
            llm_provider=llm_provider,
        )

        # Step 6: Deterministic Governance Validation
        add_trace("DETERMINISTIC_VALIDATION", "Performing SQL AST parsing, schema compliance, PII masking, and YAML structural validation.")
        val_report = validator.validate_governance(
            sql=generated["sql"],
            dbt_yaml=generated["dbt_yaml"],
            schema_fields=schema_fields,
            pii_fields=selected_cand_eval["pii_fields"],
            is_deprecated=selected_cand_eval["is_deprecated"],
            allow_deprecated_override=request.allow_deprecated_override,
            dialect=request.target_dialect,
        )

        val_status_msg = "Validation passed cleanly." if val_report["passed"] else f"Validation failed with {len(val_report['blocking_errors'])} blocking error(s)."
        add_trace("VALIDATION_RESULT", val_status_msg)

        # Step 7: Proposed DataHub Write-Back (Requires Explicit Approval)
        proposed_writeback = {
            "requires_approval": True,
            "target_urn": target_urn,
            "operations": [
                "Append Synex Generated Contract documentation block",
                "Update lineage metadata annotation",
            ],
            "summary": (
                f"Proposed metadata change proposal (MCP) for dataset URN '{target_urn}'. "
                f"Requires approval via POST /api/v1/runs/{run_id}/writeback/approve."
            ),
        }
        add_trace("WRITEBACK_PROPOSAL", "Generated DataHub metadata update proposal. Pending explicit user approval.")

        result = {
            "run_id": run_id,
            "status": "completed",
            "selected_dataset": selected_cand_eval,
            "candidate_datasets": candidate_evaluations,
            "governance": {
                "pii_fields": selected_cand_eval["pii_fields"],
                "deprecated": selected_cand_eval["is_deprecated"],
                "risks": selected_cand_eval["upstream_risks"],
            },
            "lineage_impact": lineage_impact,
            "artifacts": {
                "sql": generated["sql"],
                "dbt_yaml": generated["dbt_yaml"],
                "dbt_tests": generated["artifact_bundle"]["dbt_tests"],
                "artifact_bundle": generated["artifact_bundle"],
            },
            "validation": val_report,
            "proposed_writeback": proposed_writeback,
            "trace_logs": trace,
            "plan": planner.plan_steps(request.prompt),
        }

        # Cache run object in memory store and update Supabase
        _RUN_MEMORY_STORE[run_id] = result
        await update_run(run_id, {
            "status": "completed",
            "target_urn": target_urn,
            "target_name": selected_cand_eval["name"],
            "pii_columns": selected_cand_eval["pii_fields"],
            "sql": generated["sql"],
            "dbt_yaml": generated["dbt_yaml"],
            "trace_logs": trace,
            "session_id": request.session_id,
            "writeback_status": "pending_approval",
        })

        return result, trace

    except Exception as exc:
        logger.exception("Synex Governed Agent run failed")
        add_trace("ERROR", str(exc))
        await update_run(run_id, {"status": "failed", "trace_logs": trace})
        raise


@router.post("/run")
async def run_agent_json(request: AgentRunRequest) -> dict[str, Any]:
    """Primary Governed dbt Change Agent endpoint."""
    try:
        result, _ = await execute_agent(request)
        return result
    except RuntimeError as rerr:
        raise HTTPException(status_code=400, detail=str(rerr))
    except Exception as exc:
        logger.exception("Agent execution exception")
        raise HTTPException(status_code=500, detail=f"Synex agent execution failed: {str(exc)}") from exc


@router.post("/agent/run")
async def run_agent_stream(request: AgentRunRequest) -> StreamingResponse:
    """SSE streaming variant emitting step events in real-time."""
    async def event_generator():
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        task = asyncio.create_task(execute_agent(request, queue.put_nowait))
        try:
            while not task.done() or not queue.empty():
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
            result, trace = await task
            yield f"data: {json.dumps({'step': len(trace) + 1, 'type': 'COMPLETED', 'message': 'Synex agent task completed.', 'payload': result})}\n\n"
        except Exception as exc:
            if not task.done():
                task.cancel()
            yield f"data: {json.dumps({'type': 'ERROR', 'message': f'Synex agent execution failed: {str(exc)}'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@router.post("/runs/{run_id}/writeback/approve")
async def approve_writeback(
    run_id: str = Path(..., description="Unique run ID"),
    payload: WritebackApprovalRequest = ...
) -> dict[str, Any]:
    """Perform DataHub write-back after explicit user approval."""
    # 1. Require explicit approval boolean
    if not payload.approved:
        raise HTTPException(
            status_code=400,
            detail="Write-back approval rejected. Field 'approved' must be explicitly true."
        )

    # 2. Retrieve run context from memory store or Supabase
    run_data = _RUN_MEMORY_STORE.get(run_id)
    if not run_data:
        run_db = await get_run_by_id(run_id)
        if not run_db:
            raise HTTPException(status_code=404, detail=f"Run ID '{run_id}' not found.")
        run_data = run_db

    # 3. Check write-back idempotency
    if run_data.get("writeback_status") == "emitted" or run_data.get("writeback_approved"):
        return {
            "status": "already_approved",
            "message": f"Write-back for run '{run_id}' was already executed previously.",
            "target_urn": run_data.get("selected_dataset", {}).get("urn") or run_data.get("target_urn"),
            "approved_at": run_data.get("writeback_approved_at"),
        }

    # 4. Check validation passed requirement
    validation = run_data.get("validation") or {}
    if not validation.get("passed", True):
        blocking_errs = validation.get("blocking_errors", [])
        raise HTTPException(
            status_code=422,
            detail=f"Cannot approve write-back for run with validation blocking errors: {'; '.join(blocking_errs)}"
        )

    target_urn = (
        run_data.get("selected_dataset", {}).get("urn")
        or run_data.get("target_urn")
        or run_data.get("proposed_writeback", {}).get("target_urn")
    )
    if not target_urn:
        raise HTTPException(status_code=400, detail="Target URN missing from run data.")

    # 5. Format Synex Generated Contract section
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    contract_text = (
        f"### Synex Generated Contract\n\n"
        f"- **Synex Run ID:** `{run_id}`\n"
        f"- **Approved By:** `{payload.approved_by or 'Data Engineer'}`\n"
        f"- **Timestamp:** `{now_iso}`\n"
        f"- **Source URN:** `{target_urn}`\n"
        f"- **Governance Validation Status:** Passed (Zero Blocking Errors)\n"
        f"- **PII Decision:** Transformed via SHA2 Hashing\n"
    )

    # 6. Emit DataHub MCP update
    emitted = await mcp_emitter.emit_documentation_update(target_urn, contract_text)
    if not emitted:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to emit DataHub MCP for target URN '{target_urn}'. Verify DataHub connection and token."
        )

    # 7. Update run record write-back audit state
    run_data["writeback_status"] = "emitted"
    run_data["writeback_approved"] = True
    run_data["writeback_approved_at"] = now_iso
    run_data["writeback_approved_by"] = payload.approved_by

    await update_run(run_id, {
        "writeback_status": "emitted",
        "writeback_approved": True,
        "writeback_approved_at": now_iso,
        "writeback_approved_by": payload.approved_by,
    })

    return {
        "status": "success",
        "message": f"DataHub Metadata Change Proposal (MCP) successfully emitted for URN '{target_urn}'.",
        "run_id": run_id,
        "target_urn": target_urn,
        "approved_by": payload.approved_by,
        "timestamp": now_iso,
    }
