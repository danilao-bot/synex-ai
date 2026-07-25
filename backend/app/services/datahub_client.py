import logging
from typing import Dict, Any, List
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


class DataHubClient:
    """Client for interacting with DataHub GMS via GraphQL and REST APIs."""

    def __init__(self):
        self.gms_url = settings.DATAHUB_GMS_URL.rstrip('/')
        self.headers = {"Content-Type": "application/json"}
        if settings.DATAHUB_PAT:
            self.headers["Authorization"] = f"Bearer {settings.DATAHUB_PAT}"

    def configure(self, gms_url: str) -> None:
        """Apply the current Supabase-managed GMS endpoint for this process."""
        if gms_url:
            self.gms_url = gms_url.rstrip("/")

    async def search_entities(self, query: str, entity_types: List[str] = None) -> List[Dict[str, Any]]:
        """Search DataHub catalog for datasets matching keywords.
        
        Raises RuntimeError if DataHub GMS is unreachable — no silent fallback.
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
                  properties { description }
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
                "count": 10
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.gms_url}/api/graphql",
                    json={"query": graphql_query, "variables": variables},
                    headers=self.headers
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("errors"):
                        raise RuntimeError(f"DataHub GraphQL error: {data['errors']}")
                    results = data.get("data", {}).get("search", {}).get("searchResults", [])
                    entities = [r.get("entity") for r in results if r.get("entity")]
                    if entities:
                        return entities
                    raise RuntimeError(
                        f"DataHub returned 0 results for query '{query}'. "
                        "Ensure your DataHub instance has ingested datasets."
                    )
                else:
                    raise RuntimeError(
                        f"DataHub GMS responded with HTTP {response.status_code}. "
                        f"Check that {self.gms_url} is reachable."
                    )
        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot reach DataHub GMS at {self.gms_url}. "
                "Verify the DataHub URL is correct and the server is running."
            )
        except httpx.TimeoutException:
            raise RuntimeError(
                f"DataHub GMS at {self.gms_url} timed out after 10 seconds."
            )

    async def get_dataset_aspects(self, urn: str) -> Dict[str, Any]:
        """Fetch schema, governance tags, deprecation, and lineage aspects for a URN.
        
        Raises RuntimeError if DataHub GMS is unreachable — no silent fallback.
        """
        graphql_query = """
        query getDataset($urn: String!) {
          dataset(urn: $urn) {
            urn
            name
            properties { description }
            deprecation { deprecated note }
            tags { tags { tag { urn name } } }
            schemaMetadata {
              fields {
                fieldPath
                nativeDataType
                description
                tags { tags { tag { urn name } } }
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
                    headers=self.headers
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get("errors"):
                        raise RuntimeError(f"DataHub GraphQL error: {data['errors']}")
                    dataset = data.get("data", {}).get("dataset")
                    if dataset:
                        return dataset
                    raise RuntimeError(
                        f"DataHub returned no dataset for URN '{urn}'. "
                        "Ensure this dataset has been ingested."
                    )
                else:
                    raise RuntimeError(
                        f"DataHub GMS responded with HTTP {response.status_code} "
                        f"when fetching aspects for {urn}."
                    )
        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot reach DataHub GMS at {self.gms_url}. "
                "Verify the DataHub URL is correct and the server is running."
            )
        except httpx.TimeoutException:
            raise RuntimeError(
                f"DataHub GMS at {self.gms_url} timed out while fetching aspects for {urn}."
            )

    async def health_check(self) -> Dict[str, Any]:
        """Probe DataHub GMS health endpoint. Returns reachability status."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.gms_url}/health")
                return {
                    "reachable": response.status_code == 200,
                    "status_code": response.status_code,
                    "gms_url": self.gms_url,
                }
        except Exception as e:
            return {
                "reachable": False,
                "error": str(e),
                "gms_url": self.gms_url,
            }


datahub_client = DataHubClient()
