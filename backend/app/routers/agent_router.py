"""HTTP and SSE interfaces for the Synex agent."""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agent.generator import generator
from app.agent.planner import planner
from app.agent.reasoner import reasoner
from app.agent.validator import validator
from app.db import create_run, get_latest_agent_settings, get_run_history, save_agent_settings, update_run, get_last_run_for_session
from app.services.datahub_client import datahub_client
from app.services.mcp_emitter import mcp_emitter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Agent"])


class SettingsPayload(BaseModel):
    datahub_url: str | None = None
    datahub_pat: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None


@router.get("/history")
async def fetch_history() -> dict[str, Any]:
    """Return past execution runs from Supabase synex_runs table."""
    history = await get_run_history()
    return {"runs": history, "count": len(history)}


@router.get("/settings")
async def fetch_settings() -> dict[str, Any]:
    """Return active non-secret configuration parameters."""
    settings_data = await get_latest_agent_settings()
    # Mask LLM API key before returning — never expose raw key to frontend
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



class AgentRunRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8_000)
    target_dialect: str = "snowflake"
    writeback_enabled: bool = True
    session_id: str | None = None


async def execute_agent(
    request: AgentRunRequest, trace_sink: Callable[[dict[str, Any]], None] | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run the metadata-first workflow once and return its final response plus trace."""
    trace: list[dict[str, Any]] = []
    run_id = await create_run({
        "prompt": request.prompt, 
        "status": "running", 
        "trace_logs": [],
        "session_id": request.session_id
    })

    def add_trace(kind: str, message: str) -> None:
        event = {"step": len(trace) + 1, "type": kind, "message": message}
        trace.append(event)
        if trace_sink:
            trace_sink(event)

    try:
        db_settings = await get_latest_agent_settings()
        # Apply DataHub URL from Supabase settings if available
        datahub_url = db_settings.get("datahub_url") or db_settings.get("datahub_gms_url")
        if datahub_url:
            datahub_client.configure(datahub_url)
            mcp_emitter.configure(datahub_url)

        # Extract LLM credentials from Supabase settings (fallback to env vars via generator)
        llm_api_key = db_settings.get("llm_api_key") or None
        llm_model = db_settings.get("llm_model") or None

        # Pull previous session memory if available
        previous_sql = None
        if request.session_id:
            previous_run = await get_last_run_for_session(request.session_id)
            if previous_run and previous_run.get("generated_sql"):
                previous_sql = previous_run.get("generated_sql")
                add_trace("MEMORY_LOAD", "Loaded conversational context from previous session turn.")

        add_trace("ENTITY_DISCOVERY", "Querying DataHub metadata graph for matching datasets.")
        entities = reasoner.rank_candidates(await datahub_client.search_entities(request.prompt))
        if not entities:
            raise RuntimeError("DataHub returned no dataset candidates.")
        target_urn = entities[0]["urn"]

        add_trace("GOVERNANCE_AUDIT", f"Fetching schema, PII tags, deprecation, and lineage for {target_urn}.")
        aspects = await datahub_client.get_dataset_aspects(target_urn)
        governance = reasoner.evaluate_governance(aspects)
        if governance["deprecated"]:
            add_trace("WARNING", "Selected dataset is marked deprecated in DataHub; review output before use.")

        schema_fields = aspects.get("schemaMetadata", {}).get("fields", [])
        add_trace("LINEAGE_TRAVERSAL", f"Schema loaded: {len(schema_fields)} fields. PII columns: {', '.join(governance['pii_columns']) or 'none detected'}.")

        add_trace("CODE_SYNTHESIS", f"Calling LLM (model: {llm_model or 'env default'}) with real DataHub metadata context.")
        generated = generator.generate_code_and_contract(
            table_name=aspects.get("name") or target_urn,
            pii_columns=governance["pii_columns"],
            dialect=request.target_dialect,
            previous_sql=previous_sql,
            prompt=request.prompt,
            schema_fields=schema_fields,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
        )

        validation = validator.validate_sql(generated["sql"], request.target_dialect, schema_fields=schema_fields)
        validation_message = "SQL AST and DuckDB sandbox validation passed." if validation["ast_valid"] and validation["sandbox_success"] else "SQL validation completed with issues; inspect validation details."
        add_trace("VALIDATION", validation_message)

        writeback_status = "skipped"
        if request.writeback_enabled:
            emitted = await mcp_emitter.emit_documentation_update(
                target_urn, "Generated dbt model contract validated by Synex."
            )
            writeback_status = "emitted" if emitted else "unavailable"
            add_trace("WRITEBACK", f"DataHub documentation MCP {writeback_status}.")

        result = {
            "run_id": run_id,
            "status": "completed",
            "target_urn": target_urn,
            "target_name": aspects.get("name", target_urn),
            "dataset_description": (aspects.get("properties") or {}).get("description") or "",
            "schema_fields": schema_fields,
            "pii_columns": governance["pii_columns"],
            "sql": generated["sql"],
            "dbt_yaml": generated["dbt_yaml"],
            "validation": validation,
            "writeback_status": writeback_status,
            "trace_logs": trace,
            "plan": planner.plan_steps(request.prompt),
        }
        await update_run(run_id, {
            "status": "completed", "target_urn": result["target_urn"], "target_name": result["target_name"],
            "pii_columns": result["pii_columns"], "sql": result["sql"], "dbt_yaml": result["dbt_yaml"], "trace_logs": trace,
            "session_id": request.session_id
        })
        return result, trace
    except Exception as exc:
        logger.exception("Synex agent run failed")
        add_trace("ERROR", str(exc))
        await update_run(run_id, {"status": "failed", "trace_logs": trace})
        raise


@router.post("/run")
async def run_agent_json(request: AgentRunRequest) -> dict[str, Any]:
    """Frontend-compatible request/response endpoint."""
    try:
        result, _ = await execute_agent(request)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Synex agent execution failed") from exc


@router.post("/agent/run")
async def run_agent_stream(request: AgentRunRequest) -> StreamingResponse:
    """SSE variant for clients that render execution trace events as they arrive."""
    async def event_generator():
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
        task = asyncio.create_task(execute_agent(request, queue.put_nowait))
        try:
            while not task.done() or not queue.empty():
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
            result, trace = await task
            yield f"data: {json.dumps({'step': len(trace) + 1, 'type': 'COMPLETED', 'message': 'Synex agent task completed.', 'payload': result})}\n\n"
        except Exception:
            if not task.done():
                task.cancel()
            yield f"data: {json.dumps({'type': 'ERROR', 'message': 'Synex agent execution failed.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
