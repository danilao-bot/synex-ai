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
        """Search DataHub catalog for datasets matching keywords."""
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
                        raise RuntimeError(data["errors"])
                    results = data.get("data", {}).get("search", {}).get("searchResults", [])
                    entities = [r.get("entity") for r in results if r.get("entity")]
                    if entities:
                        return entities
        except Exception as e:
            logger.warning(f"DataHub GraphQL query fallback triggered: {e}")
            
        # Mock fallback for offline hackathon testing
        return [
            {
                "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.prod.orders,PROD)",
                "type": "DATASET",
                "name": "analytics.prod.orders",
                "properties": {"description": "Canonical production orders table"}
            },
            {
                "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.prod.customers,PROD)",
                "type": "DATASET",
                "name": "analytics.prod.customers",
                "properties": {"description": "Canonical customer master data"}
            }
        ]

    async def get_dataset_aspects(self, urn: str) -> Dict[str, Any]:
        """Fetch schema, governance tags, deprecation, and lineage aspects for a URN."""
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
                        raise RuntimeError(data["errors"])
                    dataset = data.get("data", {}).get("dataset")
                    if dataset:
                        return dataset
        except Exception as e:
            logger.warning(f"Failed to fetch dataset aspects for {urn}: {e}")

        # Return mock aspects for robust offline development
        return {
            "urn": urn,
            "name": urn.split(",")[-2] if "," in urn else "analytics.prod.orders",
            "properties": {"description": "Production orders table"},
            "deprecation": {"deprecated": False, "note": None},
            "tags": {"tags": [{"tag": {"name": "Tier-1"}}]},
            "schemaMetadata": {
                "fields": [
                    {"fieldPath": "order_id", "nativeDataType": "VARCHAR", "description": "Primary key", "tags": {"tags": []}},
                    {"fieldPath": "customer_id", "nativeDataType": "VARCHAR", "description": "Foreign key to customer", "tags": {"tags": []}},
                    {"fieldPath": "email", "nativeDataType": "VARCHAR", "description": "Customer email", "tags": {"tags": [{"tag": {"name": "PII"}}]}},
                    {"fieldPath": "amount", "nativeDataType": "NUMBER", "description": "Order dollar total", "tags": {"tags": []}},
                    {"fieldPath": "order_date", "nativeDataType": "TIMESTAMP", "description": "Order placement timestamp", "tags": {"tags": []}}
                ]
            },
            "upstreamLineage": {"upstreamNodes": []}
        }

datahub_client = DataHubClient()
