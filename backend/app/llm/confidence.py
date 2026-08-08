"""Confidence engine — multi-factor score with explanations."""

from __future__ import annotations

from typing import Any


def compute_confidence(
    *,
    selected: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
    context_package: Any = None,
    engineering_memory: dict[str, Any] | None = None,
    critique: dict[str, Any] | None = None,
    retry_count: int = 0,
) -> dict[str, Any]:
    selected = selected or {}
    validation = validation or {}
    engineering_memory = engineering_memory or {}
    critique = critique or {}

    factors: dict[str, float] = {}
    reasons_high: list[str] = []
    reasons_low: list[str] = []

    # Schema coverage
    schema_n = len(getattr(context_package, "schema_fields", None) or selected.get("schema_fields") or [])
    factors["schema_coverage"] = min(100.0, 30.0 + schema_n * 3.0)
    if schema_n >= 5:
        reasons_high.append(f"Schema coverage strong ({schema_n} fields).")
    else:
        reasons_low.append("Thin schema coverage.")

    # Validation
    if validation.get("passed"):
        factors["validation_success"] = 95.0
        reasons_high.append("Deterministic validation passed.")
    elif validation.get("passed") is False:
        factors["validation_success"] = 15.0
        reasons_low.append("Validation has blocking errors.")
    else:
        factors["validation_success"] = 50.0

    # Trust
    trust = float(selected.get("trust_score") or 50)
    factors["trust_score"] = trust
    if trust >= 75:
        reasons_high.append(f"Dataset trust high ({trust}/100).")
    elif trust < 50:
        reasons_low.append(f"Dataset trust low ({trust}/100).")

    # Production SQL similarity / availability
    profile = getattr(context_package, "sql_profile", None)
    qcount = getattr(profile, "query_count", 0) if profile else 0
    factors["production_sql_similarity"] = min(100.0, 20.0 + qcount * 15.0)
    if qcount >= 1:
        reasons_high.append(f"{qcount} production SQL example(s) influenced generation.")
    else:
        reasons_low.append("No production SQL examples available.")

    # Glossary
    gloss_n = len(getattr(context_package, "glossary", None) or selected.get("glossary_terms") or [])
    factors["glossary_coverage"] = min(100.0, gloss_n * 25.0)
    if gloss_n:
        reasons_high.append(f"Glossary coverage: {gloss_n} term(s).")
    else:
        reasons_low.append("No glossary terms loaded.")

    # Ownership
    owners = (getattr(context_package, "ownership", None) or {}).get("all_owners") or selected.get("owners") or []
    factors["ownership_confidence"] = 90.0 if owners else 25.0
    if owners:
        reasons_high.append("Ownership present.")
    else:
        reasons_low.append("Missing ownership.")

    # Quality
    q_sigs = len(getattr(context_package, "ranked_items", None) or [])
    factors["quality_signals"] = min(100.0, 40.0 + q_sigs * 2.0)

    # Lineage
    lineage_dim = (selected.get("trust_dimensions") or {}).get("lineage_confidence")
    factors["lineage_confidence"] = float(lineage_dim) if lineage_dim is not None else 50.0

    # Documentation
    docs_n = len(getattr(context_package, "documents", None) or [])
    factors["documentation_coverage"] = min(100.0, docs_n * 20.0)
    if docs_n:
        reasons_high.append(f"Documentation coverage: {docs_n} page(s).")
    else:
        reasons_low.append("Documentation sparse.")

    # Conversation / engineering memory
    has_mem = bool(engineering_memory.get("previous_sql") or engineering_memory.get("successful_sql"))
    factors["conversation_history"] = 80.0 if has_mem else 45.0
    if has_mem:
        reasons_high.append("Engineering memory available from prior runs.")

    # Critique penalty
    if critique.get("needs_revision"):
        factors["self_critique"] = 40.0
        reasons_low.append("Self-critique requested revisions.")
    elif critique.get("approved"):
        factors["self_critique"] = 90.0
        reasons_high.append("Self-critique approved the artifact.")
    else:
        factors["self_critique"] = 60.0

    # Retry dampener
    if retry_count > 0:
        factors["retry_penalty"] = max(40.0, 100.0 - retry_count * 15.0)
        reasons_low.append(f"Required {retry_count} validation retry(ies).")
    else:
        factors["retry_penalty"] = 100.0

    weights = {
        "schema_coverage": 0.10,
        "validation_success": 0.18,
        "trust_score": 0.12,
        "production_sql_similarity": 0.12,
        "glossary_coverage": 0.06,
        "ownership_confidence": 0.06,
        "quality_signals": 0.06,
        "lineage_confidence": 0.08,
        "documentation_coverage": 0.06,
        "conversation_history": 0.06,
        "self_critique": 0.06,
        "retry_penalty": 0.04,
    }
    overall = sum(factors[k] * w for k, w in weights.items() if k in factors)
    overall = round(max(0.0, min(100.0, overall)), 1)

    level = "high" if overall >= 75 else ("medium" if overall >= 50 else "low")
    return {
        "score": overall,
        "level": level,
        "factors": {k: round(v, 1) for k, v in factors.items()},
        "why_high": reasons_high,
        "why_low": reasons_low,
        "summary": (
            f"Confidence {overall}/100 ({level}). "
            + (" ".join(reasons_high[:2]) if reasons_high else "")
            + ((" Issues: " + " ".join(reasons_low[:2])) if reasons_low else "")
        ),
    }
