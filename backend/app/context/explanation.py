"""SQL Explanation Engine — evidence-backed post-generation rationale."""

from __future__ import annotations

from typing import Any, Optional

from app.context.models import ContextPackage


def build_sql_explanation(
    package: ContextPackage,
    sql: str,
    selected: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
    confidence: dict[str, Any] | None = None,
    critique: dict[str, Any] | None = None,
    alternatives: list[str] | None = None,
) -> dict[str, Any]:
    selected = selected or {}
    validation = validation or {}
    confidence = confidence or {}
    critique = critique or {}
    profile = package.sql_profile
    joins_used = []
    if profile:
        for j in profile.common_joins[:5]:
            table = j.split()[-1] if j else ""
            if table and table.lower() in (sql or "").lower():
                joins_used.append(j)

    docs_used = [d[:120] for d in package.documents[:3]]
    gloss_used = [
        g.get("name") if isinstance(g, dict) else str(g)
        for g in package.glossary[:5]
    ]
    vocab_used = [f"{v.user_term}→{v.glossary_term or v.canonical_field}" for v in package.vocabulary[:6]]

    influenced_by_sql = (profile.sample_queries[:2] if profile else [])
    lineage_note = next(
        (i.content for i in package.ranked_items if i.kind == "lineage"),
        package.reasoning_summary,
    )

    risks = list(package.warnings or [])
    risks.extend(critique.get("issues") or [])
    if not validation.get("passed", True):
        risks.extend(validation.get("blocking_errors") or [])

    alts = alternatives or []
    if profile and profile.frequently_joined_tables:
        alts.append(
            f"Alternative join set from production: {', '.join(profile.frequently_joined_tables[:4])}"
        )
    if selected.get("recommendation") != "preferred":
        alts.append("Consider a higher-trust certified dataset if available in candidate rankings.")

    explanation = {
        "why_dataset": (
            f"Chose '{package.selected_name}' "
            f"(trust {package.trust_breakdown.get('overall', selected.get('trust_score', 'n/a'))}) "
            f"via ranked DataHub candidates."
        ),
        "why_joins": (
            f"Joins guided by production patterns: {', '.join(joins_used) or 'none required / single-table model'}."
        ),
        "why_filters": (
            f"Filters inspired by production WHERE patterns: "
            f"{', '.join((profile.where_patterns[:3] if profile else []) or ['prompt-driven only'])}."
        ),
        "why_aggregation": (
            f"Aggregations from production profile: "
            f"{', '.join((profile.aggregations[:4] if profile else []) or ['none detected — row-level model'])}."
        ),
        "business_logic": (
            f"Business vocabulary and glossary applied: {', '.join(vocab_used[:4]) or 'n/a'}."
        ),
        "validation_summary": (
            "Passed deterministic governance validation."
            if validation.get("passed")
            else f"Validation issues: {'; '.join((validation.get('blocking_errors') or [])[:3])}"
        ),
        "governance_summary": (
            f"PII fields={package.pii_fields or 'none'}; "
            f"self-critique={'approved' if critique.get('approved') else 'flagged'}."
        ),
        "potential_risks": risks[:8],
        "alternative_approaches": alts[:5],
        "production_sql_influence": influenced_by_sql,
        "documentation_influence": docs_used,
        "glossary_terms_used": gloss_used,
        "business_rules_applied": [
            *package.institutional_memory[:3],
            *package.business_definitions[:3],
        ],
        "vocabulary_used": vocab_used,
        "lineage_influence": lineage_note,
        "pattern_library_used": package.pattern_library_hints[:8],
        "context_sources": package.context_sources,
        "prompt_version": package.prompt_version,
        "confidence": confidence,
        "summary": (
            f"SQL grounded in {package.manifest.production_sql_examples if package.manifest else 0} production queries, "
            f"{package.manifest.documentation_pages if package.manifest else 0} docs, "
            f"{package.manifest.glossary_definitions if package.manifest else 0} glossary terms, "
            f"trust {package.manifest.trust_score if package.manifest else 0:.0f}%, "
            f"confidence {confidence.get('score', 'n/a')}/100."
        ),
    }
    return explanation
