import logging
import asyncio
from app.core.config import settings

logger = logging.getLogger(__name__)

class MCPEmitter:
    """Emits Metadata Change Proposals (MCPs) to write-back to DataHub GMS."""

    def __init__(self) -> None:
        self.gms_url = settings.DATAHUB_GMS_URL

    def configure(self, gms_url: str) -> None:
        if gms_url:
            self.gms_url = gms_url.rstrip("/")

    async def emit_documentation_update(self, urn: str, description: str) -> bool:
        """Emit an aspect update for dataset documentation."""
        logger.info(f"Emitting Metadata Change Proposal (MCP) for URN {urn}: update description.")
        def emit() -> None:
            from datahub.emitter.mcp import MetadataChangeProposalWrapper
            from datahub.emitter.rest_emitter import DatahubRestEmitter
            from datahub.metadata.schema_classes import DatasetPropertiesClass
            emitter = DatahubRestEmitter(gms_server=self.gms_url, token=settings.DATAHUB_PAT or None)
            emitter.emit(MetadataChangeProposalWrapper(entityUrn=urn, aspect=DatasetPropertiesClass(description=description)))
        try:
            await asyncio.to_thread(emit)
            return True
        except Exception as exc:
            logger.warning("DataHub documentation MCP was not emitted: %s", exc)
            return False

    async def emit_governance_tag(self, urn: str, tag_name: str) -> bool:
        """Emit an aspect update attaching a tag to a dataset or column."""
        logger.info(f"Emitting MCP to attach tag '{tag_name}' to URN {urn}")
        def emit() -> None:
            from datahub.emitter.mcp import MetadataChangeProposalWrapper
            from datahub.emitter.rest_emitter import DatahubRestEmitter
            from datahub.metadata.schema_classes import GlobalTagsClass, TagAssociationClass
            emitter = DatahubRestEmitter(gms_server=self.gms_url, token=settings.DATAHUB_PAT or None)
            tag_urn = tag_name if tag_name.startswith("urn:li:tag:") else f"urn:li:tag:{tag_name}"
            emitter.emit(MetadataChangeProposalWrapper(entityUrn=urn, aspect=GlobalTagsClass(tags=[TagAssociationClass(tag=tag_urn)])))
        try:
            await asyncio.to_thread(emit)
            return True
        except Exception as exc:
            logger.warning("DataHub tag MCP was not emitted: %s", exc)
            return False

mcp_emitter = MCPEmitter()
