import logging
from typing import Optional
from app.services.datahub_context import datahub_context

logger = logging.getLogger(__name__)


class MCPEmitter:
    """Emits Metadata Change Proposals (MCPs) to write-back to DataHub GMS."""

    def configure(self, gms_url: Optional[str] = None, token: Optional[str] = None) -> None:
        datahub_context.configure(gms_url=gms_url, token=token)

    async def emit_documentation_update(self, urn: str, description: str) -> bool:
        """Emit an aspect update for dataset documentation using the context adapter."""
        return await datahub_context.emit_governed_proposal(urn, description)


mcp_emitter = MCPEmitter()
