"""DataHub service package — ACK / MCP / GraphQL providers."""

from app.services.datahub.service import DataHubService, datahub_service

__all__ = ["DataHubService", "datahub_service"]
