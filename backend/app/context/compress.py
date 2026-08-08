"""Context compression — fit organizational knowledge into the LLM window."""

from __future__ import annotations

from typing import Any, Optional

from app.context.models import ContextPackage, RankedContextItem, SqlProfile
from app.context.pattern_library import PatternLibrary
from app.context.vocabulary import vocabulary_prompt_block


def compress_package(
    *,
    prompt: str,
    selected_name: str,
    selected_urn: str,
    schema_fields: list[dict[str, Any]],
    pii_fields: list[str],
    sql_profile: Optional[SqlProfile],
    pattern_library: PatternLibrary,
    vocabulary_block: str,
    kept_items: list[RankedContextItem],
    ownership: dict[str, Any],
    domain: Optional[str],
    trust_breakdown: dict[str, Any],
    warnings: list[str],
    lineage_summary: str,
    quality_summary: str,
    validation_rules: list[str],
    engineering_memory: dict[str, Any],
    max_chars: int = 12000,
) -> str:
    """Build the sole LLM context block — no independent DataHub search by the model."""
    sections: list[str] = [
        "=== SYNEX ENGINEERING CONTEXT v3 (authoritative — do not invent beyond this) ===",
        f"USER_REQUEST: {prompt}",
        f"DATASET: {selected_name}",
        f"URN: {selected_urn}",
        f"DOMAIN: {domain or '(none)'}",
        f"OWNERS: {ownership.get('summary') or '(none)'}",
        f"TRUST: {trust_breakdown}",
        f"PII_FIELDS: {', '.join(pii_fields) or '(none)'}",
        f"LINEAGE: {lineage_summary}",
        f"QUALITY: {quality_summary}",
    ]
    if warnings:
        sections.append("WARNINGS:")
        sections.extend(f"  - {w}" for w in warnings[:10])

    sections.append(vocabulary_block)

    if sql_profile:
        sections.append(sql_profile.to_prompt_section(max_chars=3200))
    sections.append(pattern_library.to_prompt_section())

    # High-score knowledge by kind
    by_kind: dict[str, list[RankedContextItem]] = {}
    for item in kept_items:
        by_kind.setdefault(item.kind, []).append(item)

    for kind, label, n in (
        ("glossary", "GLOSSARY", 6),
        ("document", "DOCUMENTATION", 5),
        ("memory", "INSTITUTIONAL_MEMORY", 5),
        ("ownership", "OWNERSHIP_NOTES", 4),
        ("quality", "QUALITY_SIGNALS", 4),
        ("lineage", "LINEAGE_NOTES", 4),
        ("production_sql", "EXTRA_PRODUCTION_SQL", 2),
    ):
        rows = by_kind.get(kind) or []
        if not rows:
            continue
        sections.append(f"=== {label} ===")
        for r in rows[:n]:
            sections.append(f"  [{r.score}] {r.content[:500]}")

    if validation_rules:
        sections.append("VALIDATION_RULES:")
        sections.extend(f"  - {r}" for r in validation_rules[:8])

    if engineering_memory:
        sections.append("ENGINEERING_MEMORY (prior session):")
        if engineering_memory.get("previous_sql"):
            sections.append(engineering_memory["previous_sql"][:2500])
        if engineering_memory.get("chosen_dataset"):
            sections.append(f"  prior_dataset: {engineering_memory['chosen_dataset']}")
        if engineering_memory.get("warnings"):
            sections.append(f"  prior_warnings: {engineering_memory['warnings'][:5]}")

    # Schema last but capped
    sections.append("SCHEMA_FIELDS:")
    for f in schema_fields[:80]:
        path = f.get("fieldPath", "")
        dtype = f.get("nativeDataType", "VARCHAR")
        desc = (f.get("description") or "")[:80]
        sections.append(f"  - {path} ({dtype}): {desc}")

    sections.append("=== END ENGINEERING CONTEXT ===")
    text = "\n".join(sections)
    if len(text) <= max_chars:
        return text
    # Hard truncate with marker — prefer keeping profile + schema head
    return text[: max_chars - 80] + "\n...[context compressed for token budget]...\n=== END ==="
