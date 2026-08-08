"""Optional remote DataHub MCP Server HTTP transport.

Uses the Model Context Protocol client against DATAHUB_MCP_URL when configured
(Cloud: https://<tenant>.acryl.io/integrations/ai/mcp or self-hosted http://gms:8080/mcp).
Falls through if the mcp package or endpoint is unavailable.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class McpHttpProvider:
    """Thin MCP HTTP client. Best-effort; ACK is preferred for in-process tools."""

    source = "mcp_http"

    def __init__(self, mcp_url: str, token: str = ""):
        self.mcp_url = (mcp_url or "").rstrip("/")
        self.token = token or ""

    def available(self) -> bool:
        if not self.mcp_url:
            return False
        try:
            import mcp  # noqa: F401

            return True
        except Exception:
            return False

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Invoke a remote MCP tool. Raises on failure so DataHubService can fall back."""
        # Prefer streamable HTTP if available; otherwise raise to trigger fallback.
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client
        except Exception as exc:
            raise RuntimeError(f"MCP HTTP client unavailable: {exc}") from exc

        import anyio

        async def _invoke() -> Any:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            async with streamablehttp_client(self.mcp_url, headers=headers) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(name, arguments)
                    return result

        return anyio.run(_invoke)
