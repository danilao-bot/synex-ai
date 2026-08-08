"""Phase-3 Engineering Context DTOs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class RankedContextItem:
    kind: str  # production_sql | document | glossary | ownership | memory | lineage | quality | schema | domain
    content: str
    score: float = 0.0
    source: str = "ack"
    meta: dict[str, Any] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SqlProfile:
    """Reusable production SQL profile extracted from get_dataset_queries."""

    query_count: int = 0
    sample_queries: list[str] = field(default_factory=list)
    common_joins: list[str] = field(default_factory=list)
    frequently_joined_tables: list[str] = field(default_factory=list)
    where_patterns: list[str] = field(default_factory=list)
    group_by_patterns: list[str] = field(default_factory=list)
    aggregations: list[str] = field(default_factory=list)
    window_functions: list[str] = field(default_factory=list)
    naming_conventions: list[str] = field(default_factory=list)
    business_calculations: list[str] = field(default_factory=list)
    ctes: list[str] = field(default_factory=list)
    alias_conventions: list[str] = field(default_factory=list)
    date_handling: list[str] = field(default_factory=list)
    null_handling: list[str] = field(default_factory=list)
    derived_metrics: list[str] = field(default_factory=list)
    preferred_aliases: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_prompt_section(self, max_chars: int = 3500) -> str:
        lines = [
            "=== PRODUCTION SQL PROFILE (prefer these patterns) ===",
            f"queries_analyzed: {self.query_count}",
        ]
        if self.frequently_joined_tables:
            lines.append(f"FREQUENTLY_JOINED: {', '.join(self.frequently_joined_tables[:8])}")
        if self.common_joins:
            lines.append("COMMON_JOINS:")
            for j in self.common_joins[:6]:
                lines.append(f"  - {j}")
        if self.where_patterns:
            lines.append("WHERE_PATTERNS:")
            for w in self.where_patterns[:6]:
                lines.append(f"  - {w}")
        if self.group_by_patterns:
            lines.append(f"GROUP_BY: {'; '.join(self.group_by_patterns[:6])}")
        if self.aggregations:
            lines.append(f"AGGREGATIONS: {', '.join(self.aggregations[:8])}")
        if self.window_functions:
            lines.append(f"WINDOWS: {', '.join(self.window_functions[:6])}")
        if self.ctes:
            lines.append(f"CTES: {', '.join(self.ctes[:8])}")
        if self.date_handling:
            lines.append(f"DATE_LOGIC: {'; '.join(self.date_handling[:6])}")
        if self.null_handling:
            lines.append(f"NULL_HANDLING: {'; '.join(self.null_handling[:4])}")
        if self.business_calculations:
            lines.append("BUSINESS_CALCS:")
            for b in self.business_calculations[:5]:
                lines.append(f"  - {b}")
        if self.derived_metrics:
            lines.append(f"DERIVED_METRICS: {', '.join(self.derived_metrics[:6])}")
        if self.naming_conventions:
            lines.append(f"NAMING: {'; '.join(self.naming_conventions[:5])}")
        if self.alias_conventions:
            lines.append(f"ALIASES: {'; '.join(self.alias_conventions[:6])}")
        if self.sample_queries:
            lines.append("SAMPLE_PRODUCTION_SQL:")
            for q in self.sample_queries[:2]:
                lines.append(f"  ---\n  {q[:900]}")
        text = "\n".join(lines)
        return text[:max_chars]


@dataclass
class VocabularyMapping:
    user_term: str
    synonyms: list[str] = field(default_factory=list)
    glossary_term: Optional[str] = None
    canonical_field: Optional[str] = None
    canonical_dataset: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContextManifest:
    """Reasoning transparency checklist shown before generation."""

    candidate_datasets: int = 0
    production_sql_examples: int = 0
    glossary_definitions: int = 0
    ownership_records: int = 0
    documentation_pages: int = 0
    institutional_memory_entries: int = 0
    lineage_nodes: int = 0
    quality_signals: int = 0
    vocabulary_mappings: int = 0
    trust_score: float = 0.0
    context_items_kept: int = 0
    context_items_dropped: int = 0
    items: list[str] = field(default_factory=list)

    def to_checklist(self) -> list[str]:
        rows = [
            f"{self.candidate_datasets} candidate datasets discovered",
            f"{self.production_sql_examples} production SQL examples retrieved",
            f"{self.glossary_definitions} glossary definitions loaded",
            f"{self.ownership_records} ownership records found",
            f"{self.documentation_pages} documentation pages matched",
            f"{self.institutional_memory_entries} institutional memory entries loaded",
            f"{self.lineage_nodes} lineage nodes analyzed",
            f"{self.quality_signals} quality signals collected",
            f"{self.vocabulary_mappings} business vocabulary mappings resolved",
            f"Trust score: {self.trust_score:.0f}%",
            f"Context compression kept {self.context_items_kept} / dropped {self.context_items_dropped}",
        ]
        return rows

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["checklist"] = self.to_checklist()
        return d


@dataclass
class ContextPackage:
    """Authoritative package produced by the Context Engine for the Generator."""

    prompt: str
    selected_urn: str = ""
    selected_name: str = ""
    metadata_source: str = "ack"
    sql_profile: Optional[SqlProfile] = None
    vocabulary: list[VocabularyMapping] = field(default_factory=list)
    ranked_items: list[RankedContextItem] = field(default_factory=list)
    compressed_prompt_block: str = ""
    manifest: Optional[ContextManifest] = None
    ownership: dict[str, Any] = field(default_factory=dict)
    glossary: list[dict[str, Any]] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)
    institutional_memory: list[str] = field(default_factory=list)
    domain: Optional[str] = None
    business_definitions: list[str] = field(default_factory=list)
    recommended_joins: list[str] = field(default_factory=list)
    pattern_library_hints: list[str] = field(default_factory=list)
    trust_breakdown: dict[str, Any] = field(default_factory=dict)
    context_sources: list[str] = field(default_factory=list)
    knowledge_references: list[str] = field(default_factory=list)
    prompt_version: str = "synex-context-v3"
    dataset_rankings: list[dict[str, Any]] = field(default_factory=list)
    reasoning_summary: str = ""
    schema_fields: list[dict[str, Any]] = field(default_factory=list)
    pii_fields: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    engineering_memory: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt": self.prompt,
            "selected_urn": self.selected_urn,
            "selected_name": self.selected_name,
            "metadata_source": self.metadata_source,
            "sql_profile": self.sql_profile.to_dict() if self.sql_profile else None,
            "vocabulary": [v.to_dict() for v in self.vocabulary],
            "ranked_items": [r.to_dict() for r in self.ranked_items[:40]],
            "compressed_prompt_block": self.compressed_prompt_block,
            "manifest": self.manifest.to_dict() if self.manifest else None,
            "ownership": self.ownership,
            "glossary": self.glossary,
            "documents": self.documents,
            "institutional_memory": self.institutional_memory,
            "domain": self.domain,
            "business_definitions": self.business_definitions,
            "recommended_joins": self.recommended_joins,
            "pattern_library_hints": self.pattern_library_hints,
            "trust_breakdown": self.trust_breakdown,
            "context_sources": self.context_sources,
            "knowledge_references": self.knowledge_references,
            "prompt_version": self.prompt_version,
            "dataset_rankings": self.dataset_rankings,
            "reasoning_summary": self.reasoning_summary,
            "schema_fields": self.schema_fields,
            "pii_fields": self.pii_fields,
            "warnings": self.warnings,
            "engineering_memory": self.engineering_memory,
        }
