"""HTTP and SSE interfaces for the Synex Governed dbt Change Agent."""

import asyncio
import datetime
import json
import logging
from collections.abc import Callable
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Path, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.core.auth import get_current_user, require_role, create_access_token

class LoginRequest(BaseModel):
    api_key: str

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
from app.services.datahub import datahub_service
from app.services.datahub.models import MutationOp
from app.services.mcp_emitter import mcp_emitter
from app.workflow.engine import workflow_engine
from app.workflow.models import RunOutcome, WorkflowState

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
    # Accepted for backward compatibility with older clients; ignored.
    # Graph mutations only happen via POST /runs/{run_id}/writeback/approve.
    writeback_enabled: bool = False
    allow_deprecated_override: bool = False
    # Stored on synex_runs; used to reload previous SQL + structured context into the LLM.
    session_id: Optional[str] = None


class WritebackApprovalRequest(BaseModel):
    approved: bool
    approved_by: Optional[str] = "Data Engineer"


# In-memory store fallback for runs when Supabase is not configured
_RUN_MEMORY_STORE: dict[str, dict[str, Any]] = {}


@router.post("/auth/login")
async def login(payload: LoginRequest) -> dict[str, Any]:
    """Exchange Synex access key for signed JWT bearer token."""
    from app.security.audit import log_security_event
    if settings.SYNEX_API_KEY and payload.api_key != settings.SYNEX_API_KEY:
        await log_security_event(
            action="login_failure",
            user="anonymous",
            status="failed",
            details={"reason": "Invalid credentials provided"}
        )
        raise HTTPException(status_code=401, detail="Invalid API Key credentials")
    
    # Generate 8h token
    token = create_access_token(username="admin", role="admin")
    await log_security_event(
        action="login_success",
        user="admin",
        status="success"
    )
    return {"access_token": token, "token_type": "bearer", "role": "admin"}


@router.get("/history")
async def fetch_history(current_user: dict = Depends(require_role("engineer"))) -> dict[str, Any]:
    """Return past execution runs from Supabase synex_runs table."""
    history = await get_run_history()
    return {"runs": history, "count": len(history)}


@router.get("/settings")
async def fetch_settings(current_user: dict = Depends(require_role("viewer"))) -> dict[str, Any]:
    """Return active non-secret configuration parameters."""
    settings_data = await get_latest_agent_settings()
    if settings_data.get("llm_api_key"):
        raw = settings_data["llm_api_key"]
        settings_data["llm_api_key_masked"] = raw[:8] + "..." + raw[-4:] if len(raw) > 12 else "••••••••"
        del settings_data["llm_api_key"]
    if settings_data.get("datahub_pat"):
        raw = settings_data["datahub_pat"]
        settings_data["datahub_pat_masked"] = raw[:8] + "..." + raw[-4:] if len(raw) > 12 else "••••••••"
        del settings_data["datahub_pat"]
    return settings_data


@router.post("/settings")
async def update_settings(
    payload: SettingsPayload, 
    current_user: dict = Depends(require_role("admin"))
) -> dict[str, Any]:
    """Save new configuration parameters to Supabase synex_settings table."""
    data = payload.model_dump(exclude_none=True)
    success = await save_agent_settings(data)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save settings to database")
    
    from app.security.audit import log_security_event
    await log_security_event(
        action="settings_update",
        user=current_user.get("sub", "unknown"),
        status="success",
        details={"updated_keys": list(data.keys())}
    )
    return {"status": "success", "updated_keys": list(data.keys())}


async def execute_agent(
    request: AgentRunRequest,
    user_identity: str = "anonymous",
    trace_sink: Optional[Callable[[dict[str, Any]], None]] = None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute the Skills-inspired autonomous Data Engineering workflow engine."""
    db_settings = await get_latest_agent_settings()
    dh_url = db_settings.get("datahub_url") or db_settings.get("datahub_gms_url") or settings.DATAHUB_GMS_URL
    
    # SSRF Protection
    from app.security.ssrf import is_safe_url
    if not is_safe_url(dh_url):
        from app.security.audit import log_security_event
        await log_security_event(
            action="ssrf_blocked",
            user=user_identity,
            status="blocked",
            details={"url": dh_url}
        )
        raise RuntimeError("SSRF protection: Outbound DataHub GMS URL is not safe.")

    dh_pat = db_settings.get("datahub_pat") or settings.get_datahub_auth_token()
    mcp_url = settings.DATAHUB_MCP_URL or ""
    datahub_service.configure(gms_url=dh_url, token=dh_pat, mcp_url=mcp_url)

    llm_api_key = db_settings.get("llm_api_key") or settings.LLM_API_KEY
    llm_model = db_settings.get("llm_model") or settings.LLM_MODEL
    llm_provider = db_settings.get("llm_provider") or settings.LLM_PROVIDER

    previous_sql = None
    previous_validation_summary = None
    engineering_memory: dict[str, Any] = {}
    if request.session_id:
        from app.memory.engineering_memory import build_engineering_memory

        previous_run = await get_last_run_for_session(request.session_id)
        prior_mem = None
        for cached in _RUN_MEMORY_STORE.values():
            if cached.get("session_id") == request.session_id:
                prior_mem = cached.get("engineering_memory")
                if prior_mem:
                    break
        if previous_run:
            previous_sql = previous_run.get("sql")
            previous_validation_summary = (
                f"prior_status={previous_run.get('status')} target={previous_run.get('target_urn')}"
            )
            engineering_memory = build_engineering_memory(
                previous_run=previous_run,
                prior_memory=prior_mem,
            )
        elif prior_mem:
            engineering_memory = prior_mem
            previous_sql = prior_mem.get("previous_sql")

    run_payload = {
        "prompt": request.prompt,
        "status": "RUNNING",
        "trace_logs": [],
        "session_id": request.session_id,
        "writeback_status": "pending_approval",
    }
    run_id = await create_run(run_payload)
    if not run_id:
        import uuid
        run_id = str(uuid.uuid4())

    from app.llm.observability import ObservabilityMetrics

    state = WorkflowState(
        prompt=request.prompt,
        run_id=run_id,
        target_dialect=request.target_dialect,
        allow_deprecated_override=request.allow_deprecated_override,
        session_id=request.session_id,
        previous_sql=previous_sql,
        previous_validation_summary=previous_validation_summary,
        llm_api_key=llm_api_key or "",
        llm_model=llm_model or "",
        llm_provider=llm_provider or "openrouter",
        engineering_memory=engineering_memory,
        observability=ObservabilityMetrics(),
    )

    try:
        state = await workflow_engine.run(state, emit=trace_sink)
        result = workflow_engine.build_result(state)
        trace = result.get("trace_logs") or []

        selected = state.selected_candidate or {}
        db_status = "SUCCESS"
        if state.outcome == RunOutcome.NEEDS_CLARIFICATION:
            db_status = "FAILED"  # CHECK constraint: RUNNING|SUCCESS|FAILED — store detail in workflow_steps
            result["status"] = "NEEDS_CLARIFICATION"
        elif state.outcome == RunOutcome.FAILED:
            db_status = "FAILED"
            result["status"] = "FAILED"
        else:
            db_status = "SUCCESS"
            result["status"] = "SUCCESS"

        _RUN_MEMORY_STORE[run_id] = result
        if request.session_id:
            result["session_id"] = request.session_id

        # Persist known columns; full workflow lives in result + trace_logs (and optional workflow_steps JSON)
        await update_run(run_id, {
            "status": db_status,
            "target_urn": selected.get("urn"),
            "target_name": selected.get("name"),
            "pii_columns": selected.get("pii_fields") or [],
            "sql": (state.generated or {}).get("sql"),
            "dbt_yaml": (state.generated or {}).get("dbt_yaml"),
            "trace_logs": state.step_dicts() or trace,
            "workflow_steps": state.step_dicts(),
            "session_id": request.session_id,
            "writeback_status": "pending_approval" if state.proposed_writeback else None,
            "context_summary": (state.context_manifest or None),
            "sql_explanation": state.sql_explanation or None,
            "observability": result.get("observability"),
            "confidence": (state.confidence or {}).get("score") if state.confidence else None,
        })

        return result, trace

    except Exception as exc:
        logger.exception("Synex workflow engine run failed")
        err_event = {"step": len(state.steps) + 1, "type": "ERROR", "message": str(exc)}
        if trace_sink:
            trace_sink(err_event)
        await update_run(run_id, {
            "status": "FAILED",
            "trace_logs": [s.to_dict() for s in state.steps] + [err_event],
        })
        raise


@router.post("/run")
async def run_agent_json(
    request: AgentRunRequest,
    current_user: dict = Depends(require_role("engineer"))
) -> dict[str, Any]:
    """Primary Governed dbt Change Agent endpoint."""
    # 1. Prompt Injection Scanning
    from app.security.injection_defender import scan_prompt
    is_malicious, injection_reason = scan_prompt(request.prompt)
    if is_malicious:
        from app.security.audit import log_security_event
        await log_security_event(
            action="prompt_injection_blocked",
            user=current_user.get("sub", "unknown"),
            status="blocked",
            details={"prompt_preview": request.prompt[:100], "reason": injection_reason}
        )
        raise HTTPException(status_code=400, detail=f"Prompt rejected: {injection_reason}")

    # 2. Audit run start
    from app.security.audit import log_security_event
    user_sub = current_user.get("sub", "unknown")
    await log_security_event(
        action="run_agent_start",
        user=user_sub,
        status="success",
        details={"dialect": request.target_dialect, "session_id": request.session_id}
    )

    try:
        result, _ = await execute_agent(request, user_identity=user_sub)
        await log_security_event(
            action="run_agent_completed",
            user=user_sub,
            status="success",
            target_urn=result.get("target_urn"),
            details={"run_id": result.get("run_id")}
        )
        return result
    except RuntimeError as rerr:
        await log_security_event(
            action="run_agent_failed",
            user=user_sub,
            status="failed",
            details={"reason": str(rerr)}
        )
        raise HTTPException(status_code=400, detail=str(rerr))
    except Exception as exc:
        logger.exception("Agent execution exception")
        await log_security_event(
            action="run_agent_failed",
            user=user_sub,
            status="failed",
            details={"reason": str(exc)}
        )
        raise HTTPException(status_code=500, detail=f"Synex agent execution failed: {str(exc)}") from exc


@router.post("/agent/run")
async def run_agent_stream(
    request: AgentRunRequest,
    current_user: dict = Depends(require_role("engineer"))
) -> StreamingResponse:
    """SSE streaming variant — emits each workflow stage as it completes."""
    # 1. Prompt Injection Scanning
    from app.security.injection_defender import scan_prompt
    is_malicious, injection_reason = scan_prompt(request.prompt)
    if is_malicious:
        from app.security.audit import log_security_event
        await log_security_event(
            action="prompt_injection_blocked",
            user=current_user.get("sub", "unknown"),
            status="blocked",
            details={"prompt_preview": request.prompt[:100], "reason": injection_reason}
        )
        raise HTTPException(status_code=400, detail=f"Prompt rejected: {injection_reason}")

    user_sub = current_user.get("sub", "unknown")
    
    # 2. Audit run start
    from app.security.audit import log_security_event
    await log_security_event(
        action="run_agent_start",
        user=user_sub,
        status="success",
        details={"dialect": request.target_dialect, "session_id": request.session_id}
    )

    async def event_generator():
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

        def emit(event: dict[str, Any]) -> None:
            queue.put_nowait(event)

        task = asyncio.create_task(execute_agent(request, user_identity=user_sub, trace_sink=emit))
        try:
            while True:
                if task.done() and queue.empty():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.25)
                except asyncio.TimeoutError:
                    continue
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"

            result, trace = await task
            await log_security_event(
                action="run_agent_completed",
                user=user_sub,
                status="success",
                target_urn=result.get("target_urn"),
                details={"run_id": result.get("run_id")}
            )
            yield f"data: {json.dumps({'step': len(trace) + 1, 'type': 'COMPLETED', 'message': 'Synex workflow completed.', 'payload': result})}\n\n"
        except Exception as exc:
            if not task.done():
                task.cancel()
            await log_security_event(
                action="run_agent_failed",
                user=user_sub,
                status="failed",
                details={"reason": str(exc)}
            )
            yield f"data: {json.dumps({'type': 'ERROR', 'message': f'Synex workflow failed: {str(exc)}'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


@router.post("/runs/{run_id}/writeback/approve")
async def approve_writeback(
    run_id: str = Path(..., description="Unique run ID"),
    payload: WritebackApprovalRequest = ...,
    current_user: dict = Depends(require_role("engineer"))
) -> dict[str, Any]:
    """Execute approved multi-aspect DataHub mutations via Agent Context Kit / MCP tools."""
    if not payload.approved:
        raise HTTPException(
            status_code=400,
            detail="Write-back approval rejected. Field 'approved' must be explicitly true."
        )

    if not settings.DATAHUB_MCP_MUTATIONS_ENABLED:
        raise HTTPException(
            status_code=403,
            detail="DATAHUB_MCP_MUTATIONS_ENABLED is false. Enable mutations in server config to allow write-back."
        )

    run_data = _RUN_MEMORY_STORE.get(run_id)
    if not run_data:
        run_db = await get_run_by_id(run_id)
        if not run_db:
            raise HTTPException(status_code=404, detail=f"Run ID '{run_id}' not found.")
        run_data = run_db

    if run_data.get("writeback_status") == "emitted" or run_data.get("writeback_approved"):
        return {
            "status": "already_approved",
            "message": f"Write-back for run '{run_id}' was already executed previously.",
            "target_urn": (run_data.get("selected_dataset") or {}).get("urn") or run_data.get("target_urn"),
            "approved_at": run_data.get("writeback_approved_at"),
        }

    validation = run_data.get("validation") or {}
    if not validation.get("passed", True):
        blocking_errs = validation.get("blocking_errors", [])
        raise HTTPException(
            status_code=422,
            detail=f"Cannot approve write-back for run with validation blocking errors: {'; '.join(blocking_errs)}"
        )

    target_urn = (
        (run_data.get("selected_dataset") or {}).get("urn")
        or run_data.get("target_urn")
        or (run_data.get("proposed_writeback") or {}).get("target_urn")
    )
    if not target_urn:
        raise HTTPException(status_code=400, detail="Target URN missing from run data.")

    # Reconfigure DataHub service for mutation path
    db_settings = await get_latest_agent_settings()
    dh_url = db_settings.get("datahub_url") or settings.DATAHUB_GMS_URL
    
    # SSRF Protection
    from app.security.ssrf import is_safe_url
    user_sub = current_user.get("sub", "unknown")
    if not is_safe_url(dh_url):
        from app.security.audit import log_security_event
        await log_security_event(
            action="ssrf_blocked",
            user=user_sub,
            status="blocked",
            details={"url": dh_url, "context": "writeback_approval"}
        )
        raise HTTPException(status_code=400, detail="DataHub GMS URL blocked due to SSRF protection rules.")

    dh_pat = db_settings.get("datahub_pat") or settings.get_datahub_auth_token()
    datahub_service.configure(gms_url=dh_url, token=dh_pat, mcp_url=settings.DATAHUB_MCP_URL or "")
    mcp_emitter.configure(gms_url=dh_url, token=dh_pat)

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    proposed = run_data.get("proposed_writeback") or {}
    raw_ops = proposed.get("operations") or []

    # Normalize ops: support legacy string list and new MutationOp dicts
    mutation_ops: list[MutationOp] = []
    for item in raw_ops:
        if isinstance(item, str):
            if "documentation" in item.lower() or "contract" in item.lower() or "description" in item.lower():
                mutation_ops.append(
                    MutationOp(
                        op="update_description",
                        target_urn=target_urn,
                        params={
                            "description": (
                                f"### Synex Generated Contract\n\n"
                                f"- **Synex Run ID:** `{run_id}`\n"
                                f"- **Approved By:** `{payload.approved_by or 'Data Engineer'}`\n"
                                f"- **Timestamp:** `{now_iso}`\n"
                                f"- **Source URN:** `{target_urn}`\n"
                             ),
                             "operation": "append",
                        },
                        preview=item,
                    )
                )
            else:
                # Skip non-executable legacy labels
                continue
        elif isinstance(item, dict):
            # Stamp approval metadata into description ops
            params = dict(item.get("params") or {})
            if item.get("op") == "update_description":
                desc = params.get("description") or ""
                if "Approved By" not in desc:
                    desc = (
                        desc.rstrip()
                        + f"\n- **Approved By:** `{payload.approved_by or 'Data Engineer'}`\n"
                        + f"- **Timestamp:** `{now_iso}`\n"
                    )
                    params["description"] = desc
            mutation_ops.append(
                MutationOp(
                    op=item.get("op") or "update_description",
                    target_urn=item.get("target_urn") or target_urn,
                    params=params,
                    preview=item.get("preview") or "",
                )
            )

    if not mutation_ops:
        # Guarantee at least a description write for older runs
        mutation_ops.append(
            MutationOp(
                op="update_description",
                target_urn=target_urn,
                params={
                    "description": (
                        f"### Synex Generated Contract\n\n"
                        f"- **Synex Run ID:** `{run_id}`\n"
                        f"- **Approved By:** `{payload.approved_by or 'Data Engineer'}`\n"
                        f"- **Timestamp:** `{now_iso}`\n"
                    ),
                    "operation": "append",
                },
                preview="Append Synex Generated Contract",
            )
        )

    results: list[dict[str, Any]] = []
    any_success = False
    for mop in mutation_ops:
        executed = await datahub_service.execute_mutation(mop)
        results.append(executed.to_dict())
        if executed.status == "executed":
            any_success = True

    if not any_success:
        from app.security.audit import log_security_event
        await log_security_event(
            action="metadata_mutation_failed",
            user=user_sub,
            status="failed",
            target_urn=target_urn,
            details={"run_id": run_id, "mutation_details": [mop.to_dict() for mop in mutation_ops]}
        )
        raise HTTPException(
            status_code=502,
            detail=f"All DataHub mutation operations failed for '{target_urn}'. Check token and ACK availability.",
        )

    run_data["writeback_status"] = "emitted"
    run_data["writeback_approved"] = True
    run_data["writeback_approved_at"] = now_iso
    run_data["writeback_approved_by"] = payload.approved_by
    run_data["writeback_results"] = results

    await update_run(run_id, {
        "writeback_status": "emitted",
        "writeback_approved": True,
        "writeback_approved_at": now_iso,
        "writeback_approved_by": payload.approved_by,
    })

    from app.security.audit import log_security_event
    await log_security_event(
        action="metadata_mutation_approved",
        user=user_sub,
        status="success",
        target_urn=target_urn,
        details={
            "run_id": run_id,
            "approved_by": payload.approved_by,
            "mutation_details": [mop.to_dict() for mop in mutation_ops]
        }
    )

    return {
        "status": "success",
        "message": f"Executed {sum(1 for r in results if r.get('status') == 'executed')}/{len(results)} DataHub MCP mutation(s) for '{target_urn}'.",
        "run_id": run_id,
        "target_urn": target_urn,
        "approved_by": payload.approved_by,
        "timestamp": now_iso,
        "mutation_results": results,
    }


@router.get("/security/metrics")
async def get_security_metrics(current_user: dict = Depends(require_role("admin"))) -> dict[str, Any]:
    """Expose security performance and threat metrics from the audit logs table."""
    client = get_supabase_client()
    if client is None:
        return {"status": "error", "message": "Supabase audit storage not configured."}
        
    try:
        # Fetch recent security logs and aggregate in application thread
        response = await asyncio.to_thread(
            lambda: client.table("synex_audit_logs")
            .select("action,status")
            .limit(1000)
            .execute()
        )
        
        metrics = {
            "failed_authentications": 0,
            "rate_limit_triggers": 0,
            "prompt_injection_attempts": 0,
            "metadata_mutations_approved": 0,
            "metadata_mutations_failed": 0,
            "ssrf_blocks": 0,
        }
        
        for entry in response.data or []:
            action = entry.get("action")
            status = entry.get("status")
            
            if action == "login_failure":
                metrics["failed_authentications"] += 1
            elif action == "rate_limit_exceeded":
                metrics["rate_limit_triggers"] += 1
            elif action == "prompt_injection_blocked":
                metrics["prompt_injection_attempts"] += 1
            elif action == "metadata_mutation_approved":
                metrics["metadata_mutations_approved"] += 1
            elif action == "metadata_mutation_failed":
                metrics["metadata_mutations_failed"] += 1
            elif action == "ssrf_blocked":
                metrics["ssrf_blocks"] += 1
                
        return {
            "status": "success",
            "metrics": metrics,
            "total_audit_events_analyzed": len(response.data or [])
        }
    except Exception as e:
        logger.exception("Failed to query security metrics")
        return {"status": "error", "detail": str(e)}
