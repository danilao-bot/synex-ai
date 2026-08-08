"""GraphQL fallback provider — wraps existing DataHubContextAdapter."""

from __future__ import annotations

import logging
from typing import Any

from app.services.datahub_context import DataHubContextAdapter

logger = logging.getLogger(__name__)


class GraphQLProvider:
    """Legacy GraphQL/OpenAPI adapter used when ACK/MCP is unavailable."""

    source = "graphql"

    def __init__(self, gms_url: str, token: str = ""):
        self.adapter = DataHubContextAdapter(gms_url=gms_url, token=token)

    def available(self) -> bool:
        return bool(self.adapter.gms_url)

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        # sync bridge — caller runs via asyncio.to_thread
        import asyncio

        return asyncio.get_event_loop().run_until_complete(
            self.adapter.search_candidates(query, limit=limit)
        )

    async def search_async(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        return await self.adapter.search_candidates(query, limit=limit)

    async def get_entity_async(self, urn: str) -> dict[str, Any]:
        return await self.adapter.get_entity_metadata(urn)

    async def get_lineage_async(self, urn: str, upstream: bool = True) -> list[dict[str, Any]]:
        if upstream:
            return await self.adapter.get_upstream_lineage(urn)
        return await self.adapter.get_downstream_lineage(urn)

    async def list_schema_fields_async(self, urn: str) -> list[dict[str, Any]]:
        return await self.adapter.list_schema_fields(urn)

    async def get_sql_query_context_async(self, urn: str) -> dict[str, Any]:
        return await self.adapter.get_sql_query_context(urn)

    async def emit_description_async(self, urn: str, text: str) -> bool:
        return await self.adapter.emit_governed_proposal(urn, text)
