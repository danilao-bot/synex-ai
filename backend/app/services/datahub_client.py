"""Thin facade over DataHubContextAdapter.

TODO(Phase MCP / ACK integration): either expand this as the public service boundary
or delete once all callers use datahub_context directly. Currently unused by the router
(router imports datahub_context). Kept as a stable import surface for tests/docs.
"""

import logging
from typing import Dict, Any, List, Optional
from app.services.datahub_context import datahub_context

logger = logging.getLogger(__name__)


class DataHubClient:
    """Wrapper using DataHubContextAdapter for catalog queries and metadata retrieval."""

    def configure(self, gms_url: Optional[str] = None, token: Optional[str] = None) -> None:
        datahub_context.configure(gms_url=gms_url, token=token)

    async def search_entities(self, query: str, entity_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        return await datahub_context.search_candidates(query, entity_types)

    async def get_dataset_aspects(self, urn: str) -> Dict[str, Any]:
        return await datahub_context.get_entity_metadata(urn)

    async def health_check(self) -> Dict[str, Any]:
        try:
            await datahub_context.search_candidates("test", limit=1)
            return {"reachable": True, "gms_url": datahub_context.gms_url}
        except Exception as exc:
            return {"reachable": False, "error": str(exc), "gms_url": datahub_context.gms_url}


datahub_client = DataHubClient()
