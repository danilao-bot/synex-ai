"""Supabase access for Synex's persisted settings and execution history."""

import asyncio
import logging
from functools import lru_cache
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_supabase_client():
    """Return a service-role Supabase client, or None when local configuration is absent."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase is not configured; execution history will not be persisted.")
        return None
    try:
        from supabase import create_client

        return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    except Exception:
        logger.exception("Unable to initialize Supabase client")
        return None


async def get_latest_agent_settings() -> dict[str, Any]:
    """Fetch the newest non-secret agent settings row. Failures must not stop a run."""
    client = get_supabase_client()
    if client is None:
        return {}
    try:
        response = await asyncio.to_thread(
            lambda: client.table("synex_settings").select(
                "datahub_url,datahub_pat,llm_provider,llm_model,llm_api_key,updated_at"
            ).order("updated_at", desc=True).limit(1).execute()
        )
        return response.data[0] if response.data else {}
    except Exception:
        logger.exception("Could not read synex_settings")
        return {}


async def create_run(payload: dict[str, Any]) -> str | None:
    client = get_supabase_client()
    if client is None:
        return None
    try:
        response = await asyncio.to_thread(lambda: client.table("synex_runs").insert(payload).execute())
        return response.data[0].get("id") if response.data else None
    except Exception:
        logger.exception("Could not create synex_runs record")
        return None


async def update_run(run_id: str | None, payload: dict[str, Any]) -> None:
    if not run_id:
        return
    client = get_supabase_client()
    if client is None:
        return
    try:
        await asyncio.to_thread(lambda: client.table("synex_runs").update(payload).eq("id", run_id).execute())
    except Exception:
        logger.exception("Could not update synex_runs record %s", run_id)


async def get_run_history(limit: int = 20) -> list[dict[str, Any]]:
    """Fetch recent execution history from synex_runs."""
    client = get_supabase_client()
    if client is None:
        return []
    try:
        response = await asyncio.to_thread(
            lambda: client.table("synex_runs")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return response.data if response.data else []
    except Exception:
        logger.exception("Could not read synex_runs history")
        return []


async def get_last_run_for_session(session_id: str) -> dict[str, Any] | None:
    """Fetch the most recent run for a specific session."""
    client = get_supabase_client()
    if client is None or not session_id:
        return None
    try:
        response = await asyncio.to_thread(
            lambda: client.table("synex_runs")
            .select("*")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None
    except Exception:
        logger.exception("Could not read last run for session %s", session_id)
        return None


async def save_agent_settings(payload: dict[str, Any]) -> bool:
    """Save or update configuration row in synex_settings."""
    client = get_supabase_client()
    if client is None:
        logger.warning("Supabase is not configured; agent settings will not be persisted.")
        return True
    try:
        await asyncio.to_thread(lambda: client.table("synex_settings").insert(payload).execute())
        return True
    except Exception:
        logger.exception("Could not save synex_settings")
        return False

