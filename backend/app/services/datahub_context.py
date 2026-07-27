"""DataHub MCP and Agent Context Adapter for Synex backend.

Integrates with DataHub MCP Server / GMS APIs to provide rich metadata context:
search, entity metadata, schema fields, upstream/downstream lineage, query context,
and approved Metadata Change Proposal (MCP) write-backs.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class DataHubContextAdapter:
    """Modular adapter providing DataHub MCP Server and Agent Context Kit operations."""

    def __init__(self, gms_url: Optional[str] = None, mcp_url: Optional[str] = None, token: Optional[str] = None):
        self.gms_url = (gms_url or settings.DATAHUB_GMS_URL).rstrip("/")
        self.mcp_url = (mcp_url or settings.DATAHUB_MCP_URL or settings.DATAHUB_GMS_URL).rstrip("/")
        self.token = token or settings.get_datahub_auth_token()

    def configure(self, gms_url: Optional[str] = None, mcp_url: Optional[str] = None, token: Optional[str] = None) -> None:
        """Dynamically reconfigure GMS / MCP endpoints and authorization token."""
        if gms_url:
            self.gms_url = gms_url.rstrip("/")
        if mcp_url:
            self.mcp_url = mcp_url.rstrip("/")
        if token is not None:
            self.token = token

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        auth_token = self.token or settings.get_datahub_auth_token()
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        return headers

    async def search_candidates(self, query: str, entity_types: Optional[List[str]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Search DataHub catalog for matching datasets using GraphQL / MCP endpoint.
        
        Raises RuntimeError on connection failure or missing setup — no fabricated fallbacks.
        """
        if not entity_types:
            entity_types = ["DATASET"]

        graphql_query = """
        query searchCatalog($input: SearchInput!) {
          search(input: $input) {
            searchResults {
              entity {
                urn
                type
                ... on Dataset {
                  name
                  properties { description customProperties { key value } }
                  deprecation { deprecated note }
                  subTypes { typeNames }
                  domain { domain { urn properties { name } } }
                  institutionalMemory { elements { url description } }
                  ownership { owners { owner { urn properties { displayName email } } type } }
                  tags { tags { tag { urn name properties { description } } } }
                  glossaryTerms { terms { term { urn properties { name description } } } }
                }
              }
            }
          }
        }
        """
        variables = {
            "input": {
                "type": entity_types[0],
                "query": query,
                "start": 0,
                "count": limit
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.gms_url}/api/graphql",
                    json={"query": graphql_query, "variables": variables},
                    headers=self._get_headers()
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("errors"):
                        raise RuntimeError(f"DataHub search GraphQL error: {data['errors']}")
                    results = data.get("data", {}).get("search", {}).get("searchResults", [])
                    entities = [r.get("entity") for r in results if r.get("entity")]
                    if entities:
                        return entities
                    raise RuntimeError(
                        f"DataHub returned 0 dataset candidates for search query '{query}'. "
                        "Ingest datasets into DataHub catalog before executing Synex."
                    )
                else:
                    raise RuntimeError(
                        f"DataHub GMS returned HTTP {response.status_code} at {self.gms_url}. "
                        "Verify endpoint reachability and token credentials."
                    )
        except httpx.ConnectError:
            raise RuntimeError(
                f"Unable to connect to DataHub GMS at '{self.gms_url}'. "
                "Ensure DataHub server is running and accessible."
            )
        except httpx.TimeoutException:
            raise RuntimeError(f"DataHub GMS timed out after 10s at '{self.gms_url}'.")

    async def get_entity_metadata(self, urn: str) -> Dict[str, Any]:
        """Fetch comprehensive metadata aspects for a given URN."""
        graphql_query = """
        query getDatasetDetails($urn: String!) {
          dataset(urn: $urn) {
            urn
            name
            properties { description customProperties { key value } }
            deprecation { deprecated note actor timestamp }
            domain { domain { urn properties { name } } }
            ownership { owners { owner { urn properties { displayName email } } type } }
            tags { tags { tag { urn name } } }
            glossaryTerms { terms { term { urn properties { name description } } } }
            health { status message type }
            schemaMetadata {
              fields {
                fieldPath
                nativeDataType
                description
                nullable
                tags { tags { tag { urn name } } }
                glossaryTerms { terms { term { urn properties { name } } } }
              }
            }
            upstreamLineage {
              upstreamNodes { urn type }
            }
          }
        }
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.gms_url}/api/graphql",
                    json={"query": graphql_query, "variables": {"urn": urn}},
                    headers=self._get_headers()
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("errors"):
                        raise RuntimeError(f"DataHub entity metadata error for {urn}: {data['errors']}")
                    dataset = data.get("data", {}).get("dataset")
                    if dataset:
                        return dataset
                    raise RuntimeError(f"Dataset URN '{urn}' not found in DataHub catalog.")
                else:
                    raise RuntimeError(f"DataHub GMS returned HTTP {response.status_code} for URN {urn}.")
        except httpx.ConnectError:
            raise RuntimeError(f"Cannot reach DataHub GMS at '{self.gms_url}'.")
        except httpx.TimeoutException:
            raise RuntimeError(f"Timeout fetching DataHub entity metadata for '{urn}'.")

    async def list_schema_fields(self, urn: str) -> List[Dict[str, Any]]:
        """List schema fields and data types for a dataset URN."""
        aspects = await self.get_entity_metadata(urn)
        return aspects.get("schemaMetadata", {}).get("fields", [])

    async def get_upstream_lineage(self, urn: str) -> List[Dict[str, Any]]:
        """Traverse 2-hop upstream lineage nodes for governance risk analysis."""
        graphql_query = """
        query getUpstreamLineage($urn: String!) {
          dataset(urn: $urn) {
            lineage(input: { direction: UPSTREAM, depth: 2 }) {
              nodes {
                urn
                type
                ... on Dataset {
                  name
                  deprecation { deprecated note }
                  tags { tags { tag { urn name } } }
                }
              }
            }
          }
        }
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.gms_url}/api/graphql",
                    json={"query": graphql_query, "variables": {"urn": urn}},
                    headers=self._get_headers()
                )
                if response.status_code == 200:
                    data = response.json()
                    nodes = data.get("data", {}).get("dataset", {}).get("lineage", {}).get("nodes", [])
                    return [n for n in nodes if n.get("urn") != urn]
                return []
        except Exception as exc:
            logger.warning("Upstream lineage retrieval issue for %s: %s", urn, exc)
            return []

    async def get_downstream_lineage(self, urn: str) -> List[Dict[str, Any]]:
        """Traverse 2-hop downstream lineage to calculate blast radius impact."""
        graphql_query = """
        query getDownstreamLineage($urn: String!) {
          dataset(urn: $urn) {
            lineage(input: { direction: DOWNSTREAM, depth: 2 }) {
              nodes {
                urn
                type
                ... on Dataset {
                  name
                  deprecation { deprecated }
                  tags { tags { tag { urn name } } }
                }
              }
            }
          }
        }
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.gms_url}/api/graphql",
                    json={"query": graphql_query, "variables": {"urn": urn}},
                    headers=self._get_headers()
                )
                if response.status_code == 200:
                    data = response.json()
                    nodes = data.get("data", {}).get("dataset", {}).get("lineage", {}).get("nodes", [])
                    return [n for n in nodes if n.get("urn") != urn]
                return []
        except Exception as exc:
            logger.warning("Downstream lineage retrieval issue for %s: %s", urn, exc)
            return []

    async def get_sql_query_context(self, urn: str) -> Dict[str, Any]:
        """Fetch historical SQL queries and assertions associated with dataset URN."""
        graphql_query = """
        query getQueryContext($urn: String!) {
          dataset(urn: $urn) {
            institutionalMemory { elements { url description } }
            schemaMetadata { primaryKeys }
          }
        }
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self.gms_url}/api/graphql",
                    json={"query": graphql_query, "variables": {"urn": urn}},
                    headers=self._get_headers()
                )
                if response.status_code == 200:
                    return response.json().get("data", {}).get("dataset", {})
                return {}
        except Exception:
            return {}

    async def emit_governed_proposal(self, urn: str, appended_contract_text: str) -> bool:
        """Emit approved Metadata Change Proposal (MCP) to DataHub GMS.
        
        Appends the Synex contract section without overwriting pre-existing descriptions.
        """
        auth_token = self.token or settings.get_datahub_auth_token()
        logger.info("Emitting approved Metadata Change Proposal (MCP) for URN %s", urn)

        def sync_emit() -> bool:
            try:
                from datahub.emitter.mcp import MetadataChangeProposalWrapper
                from datahub.emitter.rest_emitter import DatahubRestEmitter
                from datahub.metadata.schema_classes import DatasetPropertiesClass

                # Fetch existing description first to append safely
                existing_aspect = self._fetch_raw_aspect(urn, "datasetProperties")
                existing_description = (existing_aspect or {}).get("description") or ""

                if "### Synex Generated Contract" in existing_description:
                    # Strip previous contract section before appending updated contract
                    base_description = existing_description.split("### Synex Generated Contract")[0].strip()
                else:
                    base_description = existing_description.strip()

                combined_description = (
                    f"{base_description}\n\n{appended_contract_text}".strip()
                    if base_description else appended_contract_text.strip()
                )

                emitter = DatahubRestEmitter(gms_server=self.gms_url, token=auth_token or None)
                mcp = MetadataChangeProposalWrapper(
                    entityUrn=urn,
                    aspect=DatasetPropertiesClass(description=combined_description)
                )
                emitter.emit(mcp)
                return True
            except Exception as exc:
                logger.error("Failed to emit DataHub MCP for URN %s: %s", urn, exc)
                return False

        return await asyncio.to_thread(sync_emit)

    def _fetch_raw_aspect(self, urn: str, aspect_name: str) -> Dict[str, Any]:
        """Synchronously fetch aspect via REST endpoint."""
        try:
            auth_token = self.token or settings.get_datahub_auth_token()
            headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
            res = httpx.get(
                f"{self.gms_url}/openapi/v1/entities/{urn}/aspects/{aspect_name}",
                headers=headers,
                timeout=5.0
            )
            if res.status_code == 200:
                return res.json().get("aspect", {})
            return {}
        except Exception:
            return {}


datahub_context = DataHubContextAdapter()
