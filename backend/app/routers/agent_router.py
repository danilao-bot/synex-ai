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
from app.db import create_run, get_latest_agent_settings, update_run
from app.services.datahub_client import datahub_client
from app.services.mcp_emitter import mcp_emitter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Agent"])


class AgentRunRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8_000)
    target_dialect: str = "snowflake"
    writeback_enabled: bool = True


async def execute_agent(
    request: AgentRunRequest, trace_sink: Callable[[dict[str, Any]], None] | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run the metadata-first workflow once and return its final response plus trace."""
    trace: list[dict[str, Any]] = []
    run_id = await create_run({"prompt": request.prompt, "status": "running", "trace_logs": []})

    def add_trace(kind: str, message: str) -> None:
        event = {"step": len(trace) + 1, "type": kind, "message": message}
        trace.append(event)
        if trace_sink:
            trace_sink(event)

    try:
        db_settings = await get_latest_agent_settings()
        # DataHub connection settings are controlled in Supabase without leaking API keys in responses.
        if db_settings.get("datahub_gms_url"):
            datahub_client.configure(db_settings["datahub_gms_url"])
            mcp_emitter.configure(db_settings["datahub_gms_url"])

        add_trace("ENTITY_DISCOVERY", "Searching the DataHub metadata graph for matching datasets.")
        entities = reasoner.rank_candidates(await datahub_client.search_entities(request.prompt))
        if not entities:
            raise RuntimeError("DataHub returned no dataset candidates.")
        target_urn = entities[0]["urn"]

        add_trace("GOVERNANCE_AUDIT", f"Fetching schema, tags, deprecation, and lineage for {target_urn}.")
        aspects = await datahub_client.get_dataset_aspects(target_urn)
        governance = reasoner.evaluate_governance(aspects)
        if governance["deprecated"]:
            add_trace("WARNING", "Selected dataset is deprecated; generated output should be reviewed before use.")

        add_trace("LINEAGE_TRAVERSAL", f"Detected PII columns: {', '.join(governance['pii_columns']) or 'none'}.")
        generated = generator.generate_code_and_contract(
            table_name=aspects.get("name") or target_urn,
            pii_columns=governance["pii_columns"],
            dialect=request.target_dialect,
        )

        validation = validator.validate_sql(generated["sql"], request.target_dialect)
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
