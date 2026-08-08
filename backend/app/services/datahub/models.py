"""Normalized DataHub DTOs used across ACK / MCP HTTP / GraphQL providers."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal, Optional


ProviderSource = Literal["ack", "mcp_http", "graphql"]


@dataclass
class MutationOp:
    """A single proposed or executed metadata mutation."""

    op: str  # update_description | add_tags | add_glossary_terms | set_domains | add_owners | save_document
    target_urn: str
    params: dict[str, Any] = field(default_factory=dict)
    preview: str = ""
    status: str = "proposed"  # proposed | executed | failed | skipped
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EnrichedContext:
    """Rich MCP context package passed to the LLM generator."""

    urn: str
    name: str
    description: str = ""
    platform: str = ""
    owners: list[str] = field(default_factory=list)
    domain: Optional[str] = None
    glossary_terms: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    quality_signals: list[str] = field(default_factory=list)
    schema_fields: list[dict[str, Any]] = field(default_factory=list)
    pii_fields: list[str] = field(default_factory=list)
    upstream: list[dict[str, Any]] = field(default_factory=list)
    downstream: list[dict[str, Any]] = field(default_factory=list)
    sample_queries: list[str] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)
    institutional_memory: list[str] = field(default_factory=list)
    assertions: list[str] = field(default_factory=list)
    is_deprecated: bool = False
    is_certified: bool = False
    metadata_source: ProviderSource = "graphql"
    previous_sql: Optional[str] = None
    previous_validation_summary: Optional[str] = None

    def to_prompt_block(self) -> str:
        lines = [
            f"DATASET: {self.name}",
            f"URN: {self.urn}",
            f"PLATFORM: {self.platform or 'unknown'}",
            f"METADATA_SOURCE: {self.metadata_source}",
            f"DESCRIPTION: {self.description or '(none)'}",
            f"OWNERS: {', '.join(self.owners) or '(none)'}",
            f"DOMAIN: {self.domain or '(none)'}",
            f"GLOSSARY: {', '.join(self.glossary_terms) or '(none)'}",
            f"TAGS: {', '.join(self.tags) or '(none)'}",
            f"QUALITY: {', '.join(self.quality_signals) or '(none)'}",
            f"CERTIFIED: {self.is_certified}  DEPRECATED: {self.is_deprecated}",
            f"PII_FIELDS: {', '.join(self.pii_fields) or '(none)'}",
            f"UPSTREAM ({len(self.upstream)}): {', '.join(n.get('name') or n.get('urn','') for n in self.upstream[:8])}",
            f"DOWNSTREAM ({len(self.downstream)}): {', '.join(n.get('name') or n.get('urn','') for n in self.downstream[:8])}",
        ]
        if self.sample_queries:
            lines.append("SAMPLE_SQL:")
            for q in self.sample_queries[:3]:
                lines.append(f"  ---\n  {q[:800]}")
        if self.documents:
            lines.append("DOCUMENTS:")
            for d in self.documents[:5]:
                lines.append(f"  - {d[:300]}")
        if self.institutional_memory:
            lines.append("INSTITUTIONAL_MEMORY:")
            for m in self.institutional_memory[:5]:
                lines.append(f"  - {m[:300]}")
        if self.assertions:
            lines.append(f"ASSERTIONS: {'; '.join(self.assertions[:8])}")
        if self.previous_sql:
            lines.append("PREVIOUS_SESSION_SQL (refine / extend this when the user asks a follow-up):")
            lines.append(self.previous_sql[:4000])
        if self.previous_validation_summary:
            lines.append(f"PREVIOUS_VALIDATION: {self.previous_validation_summary}")
        if self.schema_fields:
            lines.append("SCHEMA_FIELDS:")
            for f in self.schema_fields:
                path = f.get("fieldPath", "")
                dtype = f.get("nativeDataType", "VARCHAR")
                desc = f.get("description") or ""
                lines.append(f"  - {path} ({dtype}): {desc}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
