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
                "datahub_gms_url,snowflake_account,openai_api_key,updated_at"
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
