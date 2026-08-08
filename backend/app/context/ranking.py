"""Context ranking — score every retrieved knowledge item."""

from __future__ import annotations

import re

from app.context.models import RankedContextItem


def score_item(
    kind: str,
    content: str,
    prompt: str,
    *,
    trust_score: float = 50.0,
    is_certified: bool = False,
    is_deprecated: bool = False,
    ownership_confidence: float = 0.5,
    quality_score: float = 50.0,
    glossary_coverage: float = 0.0,
    lineage_confidence: float = 50.0,
    popularity: float = 50.0,
    source: str = "ack",
) -> RankedContextItem:
    text = (content or "").strip()
    prompt_l = (prompt or "").lower()
    words = set(re.findall(r"[a-z0-9_]{3,}", prompt_l))
    content_l = text.lower()
    overlap = sum(1 for w in words if w in content_l)
    relevance = min(100.0, 20.0 + overlap * 12.0)

    freshness = 70.0 if source == "ack" else 55.0
    doc_quality = min(100.0, 30.0 + len(text) / 20.0) if kind in ("document", "memory") else 60.0
    usage = popularity

    base = (
        0.22 * relevance
        + 0.12 * freshness
        + 0.15 * trust_score
        + 0.10 * doc_quality
        + 0.08 * usage
        + 0.10 * ownership_confidence * 100
        + 0.08 * quality_score
        + 0.08 * glossary_coverage
        + 0.07 * lineage_confidence
    )

    reasons = [f"business_relevance={relevance:.0f}"]
    if is_certified:
        base += 8
        reasons.append("certified asset boost")
    if is_deprecated:
        base -= 25
        reasons.append("deprecated penalty")
    if kind == "production_sql":
        base += 12
        reasons.append("production SQL high weight")
    if kind == "glossary":
        base += 6
        reasons.append("glossary terminology")
    if not text:
        base = 0

    score = max(0.0, min(100.0, base))
    return RankedContextItem(
        kind=kind,
        content=text[:4000],
        score=round(score, 1),
        source=source,
        meta={
            "trust": trust_score,
            "quality": quality_score,
            "lineage_confidence": lineage_confidence,
            "ownership_confidence": ownership_confidence,
        },
        reasons=reasons,
    )


def rank_and_filter(
    items: list[RankedContextItem], min_score: float = 35.0, limit: int = 40
) -> tuple[list[RankedContextItem], list[RankedContextItem]]:
    ordered = sorted(items, key=lambda x: x.score, reverse=True)
    kept = [i for i in ordered if i.score >= min_score][:limit]
    dropped = [i for i in ordered if i not in kept]
    return kept, dropped
