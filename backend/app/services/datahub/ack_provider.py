"""Agent Context Kit provider — official datahub_agent_context.mcp_tools."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _ack_available() -> bool:
    try:
        import datahub_agent_context  # noqa: F401
        from datahub.sdk.main_client import DataHubClient  # noqa: F401

        return True
    except Exception:
        return False


def _normalize_search_hit(raw: dict[str, Any]) -> dict[str, Any]:
    """Map ACK search hit into a GraphQL-ish entity dict for the reasoner."""
    entity = raw.get("entity") if isinstance(raw.get("entity"), dict) else raw
    if not isinstance(entity, dict):
        return {"urn": str(raw), "name": str(raw)}
    urn = entity.get("urn") or raw.get("urn") or ""
    props = entity.get("properties") if isinstance(entity.get("properties"), dict) else {}
    name = entity.get("name") or (props.get("name") if props else None)
    # Never treat env token (PROD/DEV) as the dataset name
    if not name or str(name).upper() in {"PROD", "DEV", "TEST", "QA", "STAGING"}:
        if urn and "dataset:(" in urn:
            inner = urn.split("dataset:(", 1)[-1].rstrip(")")
            parts = [p.strip() for p in inner.split(",")]
            if len(parts) >= 3:
                name = parts[-2]
            elif len(parts) >= 2:
                name = parts[1]
            else:
                name = parts[0] if parts else urn
        else:
            name = urn.split(":")[-1] if urn else "unknown"
    return {
        "urn": urn,
        "name": name or urn,
        "type": entity.get("type") or "DATASET",
        "properties": entity.get("properties") or {},
        "deprecation": entity.get("deprecation") or {},
        "ownership": entity.get("ownership") or {},
        "tags": entity.get("tags") or {},
        "glossaryTerms": entity.get("glossaryTerms") or {},
        "domain": entity.get("domain") or {},
        "schemaMetadata": entity.get("schemaMetadata") or {},
        "platform": entity.get("platform") or {},
        "subTypes": entity.get("subTypes") or {},
        "institutionalMemory": entity.get("institutionalMemory") or {},
        "health": entity.get("health") or [],
    }


def _entity_from_get_entities(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    # ACK may nest under entity or return flat
    entity = item.get("entity") if isinstance(item.get("entity"), dict) else item
    return _normalize_search_hit(entity)


class AckProvider:
    """Calls official Agent Context Kit MCP tools via DataHubContext."""

    source = "ack"

    def __init__(self, gms_url: str, token: str = ""):
        self.gms_url = gms_url.rstrip("/")
        self.token = token or ""
        self._client = None

    def available(self) -> bool:
        return _ack_available() and bool(self.gms_url)

    def _get_client(self):
        if self._client is not None:
            return self._client
        from datahub.sdk.main_client import DataHubClient

        self._client = DataHubClient(server=self.gms_url, token=self.token or None)
        return self._client

    def _run(self, fn, *args, **kwargs):
        from datahub_agent_context.context import DataHubContext

        with DataHubContext(self._get_client()):
            return fn(*args, **kwargs)

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        from datahub_agent_context.mcp_tools import search

        # Official search prefers /q structured queries
        q = query.strip()
        if not q.startswith("/q"):
            # Extract keywords for better matching
            words = re.findall(r"[A-Za-z0-9_]+", q)
            keywords = [w for w in words if len(w) > 2][:8]
            q = "/q " + "+".join(keywords) if keywords else "/q *"

        result = self._run(
            search,
            query=q,
            filter="entity_type = dataset",
            num_results=min(limit, 50),
        )
        hits: list[dict[str, Any]] = []
        if isinstance(result, dict):
            for row in result.get("searchResults") or result.get("search_results") or []:
                if isinstance(row, dict):
                    hits.append(_normalize_search_hit(row))
                else:
                    hits.append({"urn": str(row), "name": str(row)})
        if not hits:
            raise RuntimeError(f"ACK search returned 0 dataset candidates for '{query}'.")
        return hits

    def get_entity(self, urn: str) -> dict[str, Any]:
        from datahub_agent_context.mcp_tools import get_entities

        items = self._run(get_entities, urns=[urn])
        if not items:
            raise RuntimeError(f"ACK get_entities found no entity for {urn}")
        first = items[0] if isinstance(items, list) else items
        entity = _entity_from_get_entities(first if isinstance(first, dict) else {})
        if not entity.get("urn"):
            entity["urn"] = urn
        # Enrich schema via list_schema_fields when missing
        if not entity.get("schemaMetadata", {}).get("fields"):
            try:
                fields = self.list_schema_fields(urn)
                entity["schemaMetadata"] = {"fields": fields}
            except Exception as exc:
                logger.debug("list_schema_fields failed for %s: %s", urn, exc)
        return entity

    def list_schema_fields(self, urn: str) -> list[dict[str, Any]]:
        from datahub_agent_context.mcp_tools import list_schema_fields

        result = self._run(list_schema_fields, urn=urn)
        fields: list[dict[str, Any]] = []
        if isinstance(result, dict):
            rows = result.get("fields") or result.get("schemaFields") or result.get("schema_fields") or []
        else:
            rows = result if isinstance(result, list) else []
        for f in rows or []:
            if isinstance(f, dict):
                fields.append(
                    {
                        "fieldPath": f.get("fieldPath") or f.get("field_path") or f.get("name") or "",
                        "nativeDataType": f.get("nativeDataType") or f.get("type") or "VARCHAR",
                        "description": f.get("description") or "",
                        "nullable": f.get("nullable"),
                        "tags": f.get("tags") or {},
                        "glossaryTerms": f.get("glossaryTerms") or {},
                    }
                )
            else:
                fields.append({"fieldPath": str(f), "nativeDataType": "VARCHAR", "description": ""})
        return fields

    def get_lineage(self, urn: str, upstream: bool = True, max_hops: int = 2) -> list[dict[str, Any]]:
        from datahub_agent_context.mcp_tools import get_lineage

        result = self._run(
            get_lineage,
            urn=urn,
            upstream=upstream,
            max_hops=max_hops,
            max_results=30,
        )
        nodes: list[dict[str, Any]] = []
        if isinstance(result, dict):
            raw_nodes = result.get("nodes") or result.get("lineage") or result.get("entities") or []
            if isinstance(raw_nodes, dict):
                raw_nodes = raw_nodes.get("nodes") or []
            for n in raw_nodes or []:
                if not isinstance(n, dict):
                    continue
                n_urn = n.get("urn") or ""
                if n_urn == urn:
                    continue
                nodes.append(
                    {
                        "urn": n_urn,
                        "name": n.get("name") or n_urn,
                        "type": n.get("type"),
                        "deprecation": n.get("deprecation") or {},
                        "tags": n.get("tags") or {},
                    }
                )
        return nodes

    def get_dataset_queries(self, urn: str) -> list[str]:
        from datahub_agent_context.mcp_tools import get_dataset_queries

        try:
            result = self._run(get_dataset_queries, urn=urn, count=10)
        except Exception as exc:
            logger.debug("get_dataset_queries failed: %s", exc)
            return []

        queries: list[str] = []
        rows = result if isinstance(result, list) else (result.get("queries") if isinstance(result, dict) else [])
        for q in rows or []:
            if isinstance(q, str):
                queries.append(q)
            elif isinstance(q, dict):
                text = q.get("query") or q.get("statement") or q.get("sql") or ""
                if text:
                    queries.append(str(text))
        return queries

    def search_documents(self, query: str) -> list[str]:
        try:
            from datahub_agent_context.mcp_tools import search_documents

            result = self._run(search_documents, query=query)
        except Exception as exc:
            logger.debug("search_documents failed: %s", exc)
            return []
        docs: list[str] = []
        rows = result if isinstance(result, list) else (result.get("documents") or result.get("searchResults") if isinstance(result, dict) else [])
        for d in rows or []:
            if isinstance(d, str):
                docs.append(d)
            elif isinstance(d, dict):
                docs.append(d.get("title") or d.get("content") or d.get("description") or str(d)[:200])
        return docs

    def grep_documents(self, query: str) -> list[str]:
        """Grep engineering/business docs for request-relevant snippets."""
        try:
            from datahub_agent_context.mcp_tools import grep_documents

            # Prefer structured kwargs; fall back to query-only
            try:
                result = self._run(grep_documents, query=query)
            except TypeError:
                result = self._run(grep_documents, pattern=query)
        except Exception as exc:
            logger.debug("grep_documents failed: %s", exc)
            return []
        docs: list[str] = []
        rows = result if isinstance(result, list) else (
            (result.get("matches") or result.get("documents") or result.get("results"))
            if isinstance(result, dict)
            else []
        )
        for d in rows or []:
            if isinstance(d, str):
                docs.append(d)
            elif isinstance(d, dict):
                docs.append(
                    d.get("snippet")
                    or d.get("content")
                    or d.get("title")
                    or d.get("description")
                    or str(d)[:240]
                )
        return docs

    def get_assertions(self, urn: str) -> list[str]:
        try:
            from datahub_agent_context.mcp_tools import get_dataset_assertions

            result = self._run(get_dataset_assertions, urn=urn)
        except Exception as exc:
            logger.debug("get_dataset_assertions failed: %s", exc)
            return []
        signals: list[str] = []
        rows = result if isinstance(result, list) else (result.get("assertions") if isinstance(result, dict) else [])
        for a in rows or []:
            if isinstance(a, str):
                signals.append(a)
            elif isinstance(a, dict):
                signals.append(a.get("type") or a.get("name") or str(a)[:120])
        return signals

    # --- Mutations ---

    def update_description(self, urn: str, description: str, operation: str = "append") -> dict[str, Any]:
        from datahub_agent_context.mcp_tools import update_description

        return self._run(
            update_description,
            entity_urn=urn,
            operation=operation if operation in ("replace", "append", "remove") else "append",
            description=description,
        )

    def add_tags(self, urn: str, tag_urns: list[str]) -> dict[str, Any]:
        from datahub_agent_context.mcp_tools import add_tags

        return self._run(add_tags, tag_urns=tag_urns, entity_urns=[urn])

    def add_glossary_terms(self, urn: str, term_urns: list[str]) -> dict[str, Any]:
        from datahub_agent_context.mcp_tools import add_glossary_terms

        return self._run(add_glossary_terms, term_urns=term_urns, entity_urns=[urn])

    def set_domains(self, urn: str, domain_urn: str) -> dict[str, Any]:
        from datahub_agent_context.mcp_tools import set_domains

        return self._run(set_domains, domain_urn=domain_urn, entity_urns=[urn])

    def add_owners(self, urn: str, owner_urns: list[str]) -> dict[str, Any]:
        from datahub_agent_context.mcp_tools import add_owners

        return self._run(add_owners, owner_urns=owner_urns, entity_urns=[urn])

    def save_document(self, **kwargs: Any) -> dict[str, Any]:
        from datahub_agent_context.mcp_tools import save_document

        return self._run(save_document, **kwargs)
