"""DataHubService — ACK first, optional MCP HTTP, GraphQL fallback."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Optional

from app.services.datahub.ack_provider import AckProvider
from app.services.datahub.graphql_provider import GraphQLProvider
from app.services.datahub.mcp_http_provider import McpHttpProvider
from app.services.datahub.models import EnrichedContext, MutationOp, ProviderSource

logger = logging.getLogger(__name__)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def dataset_name_from_urn(urn: str) -> str:
    """Extract dataset name from DataHub URN — never return env token like PROD."""
    if not urn:
        return ""
    m = re.search(r"urn:li:dataset:\((.+)\)\s*$", urn)
    if not m:
        return urn.split(":")[-1]
    parts = [p.strip() for p in m.group(1).split(",")]
    if len(parts) >= 3:
        return parts[-2]  # platform, name, env
    if len(parts) == 2:
        return parts[1]
    return parts[0] if parts else urn


def _safe_entity_name(entity: dict[str, Any], urn: str = "") -> str:
    name = entity.get("name")
    if isinstance(name, str) and name and name.upper() not in {"PROD", "DEV", "TEST", "QA", "STAGING"}:
        return name
    props = _as_dict(entity.get("properties"))
    pname = props.get("name")
    if isinstance(pname, str) and pname and pname.upper() not in {"PROD", "DEV", "TEST", "QA", "STAGING"}:
        return pname
    derived = dataset_name_from_urn(urn or entity.get("urn") or "")
    return derived or name or urn or "unknown_dataset"

class DataHubService:
    """Unified DataHub access with fail-down providers."""

    def __init__(
        self,
        gms_url: str,
        token: str = "",
        mcp_url: str = "",
    ):
        self.gms_url = (gms_url or "").rstrip("/")
        self.token = token or ""
        self.mcp_url = (mcp_url or "").rstrip("/")
        self.ack = AckProvider(self.gms_url, self.token)
        self.mcp_http = McpHttpProvider(self.mcp_url, self.token) if self.mcp_url else None
        self.graphql = GraphQLProvider(self.gms_url, self.token)
        self.last_source: ProviderSource = "graphql"

    def configure(self, gms_url: Optional[str] = None, token: Optional[str] = None, mcp_url: Optional[str] = None) -> None:
        if gms_url:
            self.gms_url = gms_url.rstrip("/")
            self.ack = AckProvider(self.gms_url, self.token if token is None else token)
            self.graphql = GraphQLProvider(self.gms_url, self.token if token is None else token)
        if token is not None:
            self.token = token
            self.ack.token = token
            self.ack._client = None
            self.graphql = GraphQLProvider(self.gms_url, token)
            if self.mcp_http:
                self.mcp_http.token = token
        if mcp_url is not None:
            self.mcp_url = mcp_url.rstrip("/")
            self.mcp_http = McpHttpProvider(self.mcp_url, self.token) if self.mcp_url else None

    async def search(self, query: str, limit: int = 5) -> tuple[list[dict[str, Any]], ProviderSource]:
        # 1) ACK
        if self.ack.available():
            try:
                hits = await asyncio.to_thread(self.ack.search, query, limit)
                self.last_source = "ack"
                return hits, "ack"
            except Exception as exc:
                logger.warning("ACK search failed, falling back: %s", exc)

        # 2) MCP HTTP (best-effort search tool)
        if self.mcp_http and self.mcp_http.available():
            try:
                raw = await asyncio.to_thread(
                    self.mcp_http.call_tool,
                    "search",
                    {"query": query, "num_results": limit},
                )
                hits = self._normalize_mcp_search(raw)
                if hits:
                    self.last_source = "mcp_http"
                    return hits, "mcp_http"
            except Exception as exc:
                logger.warning("MCP HTTP search failed, falling back: %s", exc)

        # 3) GraphQL
        hits = await self.graphql.search_async(query, limit=limit)
        self.last_source = "graphql"
        return hits, "graphql"

    async def get_entity(self, urn: str) -> tuple[dict[str, Any], ProviderSource]:
        if self.ack.available():
            try:
                entity = await asyncio.to_thread(self.ack.get_entity, urn)
                self.last_source = "ack"
                return entity, "ack"
            except Exception as exc:
                logger.warning("ACK get_entity failed: %s", exc)
        entity = await self.graphql.get_entity_async(urn)
        self.last_source = "graphql"
        return entity, "graphql"

    async def get_lineage(self, urn: str, upstream: bool = True, max_hops: int = 2) -> list[dict[str, Any]]:
        if self.ack.available():
            try:
                return await asyncio.to_thread(self.ack.get_lineage, urn, upstream, max_hops)
            except Exception as exc:
                logger.warning("ACK lineage failed: %s", exc)
        return await self.graphql.get_lineage_async(urn, upstream=upstream)

    async def list_schema_fields(self, urn: str) -> list[dict[str, Any]]:
        if self.ack.available():
            try:
                return await asyncio.to_thread(self.ack.list_schema_fields, urn)
            except Exception as exc:
                logger.warning("ACK list_schema_fields failed: %s", exc)
        return await self.graphql.list_schema_fields_async(urn)

    async def get_dataset_queries(self, urn: str) -> list[str]:
        if self.ack.available():
            try:
                return await asyncio.to_thread(self.ack.get_dataset_queries, urn)
            except Exception as exc:
                logger.debug("ACK queries failed: %s", exc)
        ctx = await self.graphql.get_sql_query_context_async(urn)
        mem = ((ctx or {}).get("institutionalMemory") or {}) if isinstance(ctx, dict) else {}
        if not isinstance(mem, dict):
            mem = {}
        elements = mem.get("elements") or []
        if not isinstance(elements, list):
            return []
        return [e.get("description") or e.get("url") or "" for e in elements if isinstance(e, dict)]

    async def search_documents(self, query: str) -> list[str]:
        if self.ack.available():
            try:
                return await asyncio.to_thread(self.ack.search_documents, query)
            except Exception as exc:
                logger.debug("ACK documents failed: %s", exc)
        return []

    async def grep_documents(self, query: str) -> list[str]:
        if self.ack.available():
            try:
                return await asyncio.to_thread(self.ack.grep_documents, query)
            except Exception as exc:
                logger.debug("ACK grep_documents failed: %s", exc)
        return []

    async def get_assertions(self, urn: str) -> list[str]:
        if self.ack.available():
            try:
                return await asyncio.to_thread(self.ack.get_assertions, urn)
            except Exception as exc:
                logger.debug("ACK assertions failed: %s", exc)
        return []

    async def enrich_dataset(
        self,
        urn: str,
        prompt: str = "",
        previous_sql: Optional[str] = None,
        previous_validation_summary: Optional[str] = None,
    ) -> EnrichedContext:
        entity, source = await self.get_entity(urn)
        entity = _as_dict(entity)
        schema_meta = _as_dict(entity.get("schemaMetadata"))
        schema_fields = _as_list(schema_meta.get("fields"))
        if not schema_fields:
            try:
                schema_fields = await self.list_schema_fields(urn)
            except Exception as exc:
                logger.debug("list_schema_fields during enrich failed: %s", exc)
                schema_fields = []
            entity["schemaMetadata"] = {"fields": schema_fields}

        up, down = await asyncio.gather(
            self.get_lineage(urn, upstream=True, max_hops=2),
            self.get_lineage(urn, upstream=False, max_hops=2),
        )
        queries, docs, assertions = await asyncio.gather(
            self.get_dataset_queries(urn),
            self.search_documents(prompt or _safe_entity_name(entity, urn) or urn),
            self.get_assertions(urn),
        )

        # Extract display fields (compatible with GraphQL + ACK shapes)
        ownership = _as_dict(entity.get("ownership"))
        owners_raw = _as_list(ownership.get("owners"))
        owners = []
        for o in owners_raw:
            if isinstance(o, dict):
                owner = o.get("owner")
                if isinstance(owner, dict):
                    owners.append(
                        _as_dict(owner.get("properties")).get("displayName")
                        or owner.get("urn")
                        or ""
                    )
                elif isinstance(owner, str):
                    owners.append(owner)
            elif isinstance(o, str):
                owners.append(o)

        tags_blob = _as_dict(entity.get("tags"))
        tags_raw = _as_list(tags_blob.get("tags"))
        tags = []
        for t in tags_raw:
            if isinstance(t, dict) and isinstance(t.get("tag"), dict):
                tags.append(t["tag"].get("name") or t["tag"].get("urn") or "")
            elif isinstance(t, str):
                tags.append(t)

        gloss_blob = _as_dict(entity.get("glossaryTerms"))
        terms_raw = _as_list(gloss_blob.get("terms"))
        glossary = []
        for t in terms_raw:
            if isinstance(t, dict) and isinstance(t.get("term"), dict):
                glossary.append(
                    _as_dict(t["term"].get("properties")).get("name")
                    or t["term"].get("urn")
                    or ""
                )

        domain_wrap = _as_dict(entity.get("domain"))
        domain_info = _as_dict(domain_wrap.get("domain"))
        domain = _as_dict(domain_info.get("properties")).get("name") or domain_info.get("urn")

        deprecation = _as_dict(entity.get("deprecation"))
        is_deprecated = bool(deprecation.get("deprecated", False))
        is_certified = any("CERTIFIED" in (t or "").upper() or "VERIFIED" in (t or "").upper() for t in tags)

        props = _as_dict(entity.get("properties"))
        description = props.get("description") or ""
        platform = ""
        plat = _as_dict(entity.get("platform"))
        platform = plat.get("name") or _as_dict(plat.get("properties")).get("displayName") or ""

        pii_pattern = re.compile(
            r"(email|e_mail|phone|mobile|ssn|social_security|credit_?card|passport|dob|date_?of_?birth|address)",
            re.I,
        )
        pii_fields: list[str] = []
        for f in schema_fields:
            if not isinstance(f, dict):
                continue
            f_path = f.get("fieldPath", "") or ""
            f_tags_blob = _as_dict(f.get("tags"))
            f_tags = [
                _as_dict(t.get("tag")).get("name", "").upper()
                for t in _as_list(f_tags_blob.get("tags"))
                if isinstance(t, dict) and t.get("tag")
            ]
            if any("PII" in t or "SENSITIVE" in t for t in f_tags) or pii_pattern.search(f_path):
                pii_fields.append(f_path)

        mem_blob = _as_dict(entity.get("institutionalMemory"))
        mem_elems = _as_list(mem_blob.get("elements"))
        institutional = [
            e.get("description") or e.get("url") or ""
            for e in mem_elems
            if isinstance(e, dict)
        ]

        health = entity.get("health") or []
        quality = []
        if isinstance(health, list):
            for h in health:
                if isinstance(h, dict) and h.get("type"):
                    quality.append(f"{h.get('type')}: {h.get('status', 'OK')}")
        quality.extend(assertions or [])

        return EnrichedContext(
            urn=urn,
            name=_safe_entity_name(entity, urn),
            description=description or "",
            platform=platform or "",
            owners=[o for o in owners if o],
            domain=domain,
            glossary_terms=[g for g in glossary if g],
            tags=[t for t in tags if t],
            quality_signals=quality,
            schema_fields=[f for f in schema_fields if isinstance(f, dict)],
            pii_fields=sorted(set(pii_fields)),
            upstream=up or [],
            downstream=down or [],
            sample_queries=queries or [],
            documents=docs or [],
            institutional_memory=institutional,
            assertions=assertions or [],
            is_deprecated=is_deprecated,
            is_certified=is_certified,
            metadata_source=source,
            previous_sql=previous_sql,
            previous_validation_summary=previous_validation_summary,
        )

    async def execute_mutation(self, op: MutationOp) -> MutationOp:
        """Execute one approved mutation via ACK, with GraphQL description fallback."""
        try:
            if op.op == "update_description":
                text = op.params.get("description") or ""
                if self.ack.available():
                    try:
                        await asyncio.to_thread(
                            self.ack.update_description,
                            op.target_urn,
                            text,
                            op.params.get("operation", "append"),
                        )
                        op.status = "executed"
                        return op
                    except Exception as exc:
                        logger.warning("ACK update_description failed, trying GraphQL MCP wrapper: %s", exc)
                ok = await self.graphql.emit_description_async(op.target_urn, text)
                op.status = "executed" if ok else "failed"
                if not ok:
                    op.error = "Description emit failed"
                return op

            if not self.ack.available():
                op.status = "failed"
                op.error = "ACK mutations unavailable"
                return op

            if op.op == "add_tags":
                await asyncio.to_thread(self.ack.add_tags, op.target_urn, op.params.get("tag_urns") or [])
            elif op.op == "add_glossary_terms":
                await asyncio.to_thread(
                    self.ack.add_glossary_terms, op.target_urn, op.params.get("term_urns") or []
                )
            elif op.op == "set_domains":
                domain = op.params.get("domain_urn") or (op.params.get("domain_urns") or [None])[0]
                if not domain:
                    raise RuntimeError("domain_urn required")
                await asyncio.to_thread(self.ack.set_domains, op.target_urn, domain)
            elif op.op == "add_owners":
                await asyncio.to_thread(self.ack.add_owners, op.target_urn, op.params.get("owner_urns") or [])
            elif op.op == "save_document":
                await asyncio.to_thread(self.ack.save_document, **(op.params or {}))
            else:
                op.status = "skipped"
                op.error = f"Unknown op {op.op}"
                return op
            op.status = "executed"
            return op
        except Exception as exc:
            op.status = "failed"
            op.error = str(exc)
            return op

    @staticmethod
    def _normalize_mcp_search(raw: Any) -> list[dict[str, Any]]:
        hits: list[dict[str, Any]] = []
        content = raw
        if hasattr(raw, "content"):
            content = raw.content
        if isinstance(content, list):
            for item in content:
                text = getattr(item, "text", None) or (item.get("text") if isinstance(item, dict) else None)
                if text:
                    hits.append({"urn": text, "name": text})
        elif isinstance(content, dict):
            for row in content.get("searchResults") or []:
                ent = row.get("entity") if isinstance(row, dict) else None
                if isinstance(ent, dict):
                    hits.append({"urn": ent.get("urn"), "name": ent.get("name") or ent.get("urn")})
        return [h for h in hits if h.get("urn")]


# Process-wide service instance (reconfigured per request)
datahub_service = DataHubService(gms_url="http://localhost:8080")
