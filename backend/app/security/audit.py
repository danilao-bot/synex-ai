"""Audit logging utilities to securely record sensitive events and mutations."""

import datetime
import logging
from typing import Any, Optional
from app.db import get_supabase_client

logger = logging.getLogger("synex.audit")


def mask_secret_data(data: dict) -> dict:
    """Recursively mask fields in a dictionary that look like API keys or tokens."""
    masked = {}
    secret_keys = ("api_key", "pat", "token", "password", "service_role")
    for k, v in data.items():
        if isinstance(v, dict):
            masked[k] = mask_secret_data(v)
        elif isinstance(v, list):
            masked[k] = [mask_secret_data(item) if isinstance(item, dict) else item for item in v]
        elif any(sk in k.lower() for sk in secret_keys) and isinstance(v, str):
            if len(v) > 8:
                masked[k] = v[:8] + "..." + v[-4:]
            else:
                masked[k] = "••••••••"
        else:
            masked[k] = v
    return masked


async def log_security_event(
    action: str,
    user: str,
    status: str = "success",
    target_urn: Optional[str] = None,
    details: Optional[dict] = None
) -> None:
    """Record a security or administrative action to the audit logs.
    
    Logs to the system console, local files, and persists to the Supabase `synex_audit_logs` table if present.
    """
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    safe_details = mask_secret_data(details or {})
    
    # 1. Console log (sanitized)
    logger.info(
        "[AUDIT] %s | User: %s | Action: %s | Status: %s | Target: %s | Details: %s",
        now, user, action, status, target_urn or "N/A", safe_details
    )
    
    # 2. Persist to Supabase if configured
    client = get_supabase_client()
    if client is not None:
        try:
            payload = {
                "created_at": now,
                "user_identity": user,
                "action": action,
                "status": status,
                "target_urn": target_urn,
                "details": safe_details
            }
            # We run this in a background thread or async to prevent blocking HTTP handler
            import asyncio
            await asyncio.to_thread(
                lambda: client.table("synex_audit_logs").insert(payload).execute()
            )
        except Exception as exc:
            # Audit log errors should not crash the core application flow, but they must be reported
            logger.error("Failed to persist audit log entry to Supabase: %s", exc)
