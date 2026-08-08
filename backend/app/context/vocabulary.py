"""Business vocabulary resolver — map user language to canonical DataHub entities."""

from __future__ import annotations

import re
from typing import Any, Optional

from app.context.models import VocabularyMapping

# Seed synonym graph (extended by glossary / schema at runtime)
_SEED: dict[str, list[str]] = {
    "revenue": ["gross_revenue", "net_revenue", "arr", "mrr", "sales", "income", "grossrevenue"],
    "customer": ["client", "account", "subscriber", "user", "buyer", "crm_customer"],
    "order": ["transaction", "purchase", "sale", "invoice"],
    "product": ["sku", "item", "offering"],
    "employee": ["staff", "worker", "person", "hr"],
    "date": ["day", "ds", "event_date", "created_at", "order_date"],
}


def resolve_vocabulary(
    prompt: str,
    glossary_terms: list[str] | None = None,
    schema_fields: list[dict[str, Any]] | None = None,
    dataset_name: Optional[str] = None,
    domain: Optional[str] = None,
) -> list[VocabularyMapping]:
    glossary_terms = glossary_terms or []
    schema_fields = schema_fields or []
    field_paths = [f.get("fieldPath", "") for f in schema_fields if f.get("fieldPath")]
    words = set(re.findall(r"[a-zA-Z][a-zA-Z0-9_]+", (prompt or "").lower()))

    mappings: list[VocabularyMapping] = []
    seen: set[str] = set()

    for seed, synonyms in _SEED.items():
        if seed not in words and not any(s in " ".join(words) or s in words for s in synonyms):
            # also match if any synonym token appears
            if not any(any(tok.startswith(s) or s in tok for tok in words) for s in [seed, *synonyms]):
                continue
        if seed in seen:
            continue
        seen.add(seed)

        gloss = _best_glossary(seed, synonyms, glossary_terms)
        field = _best_field(seed, synonyms, field_paths)
        conf = 0.4
        if gloss:
            conf += 0.25
        if field:
            conf += 0.25
        if dataset_name and any(s in dataset_name.lower() for s in [seed, *synonyms]):
            conf += 0.1

        mappings.append(
            VocabularyMapping(
                user_term=seed,
                synonyms=synonyms[:6],
                glossary_term=gloss,
                canonical_field=field,
                canonical_dataset=dataset_name if dataset_name and seed in (dataset_name or "").lower() else dataset_name,
                confidence=min(0.99, conf),
            )
        )

    # Glossary-driven extras from prompt tokens
    for term in glossary_terms:
        tlow = (term or "").lower()
        token = re.sub(r"[^a-z0-9_]+", "_", tlow).strip("_")
        if not token or token in seen:
            continue
        if any(w in tlow or tlow in w for w in words if len(w) > 3):
            seen.add(token)
            mappings.append(
                VocabularyMapping(
                    user_term=token,
                    synonyms=[],
                    glossary_term=term,
                    canonical_field=_best_field(token, [], field_paths),
                    canonical_dataset=dataset_name,
                    confidence=0.7,
                )
            )

    if domain:
        mappings.append(
            VocabularyMapping(
                user_term="domain",
                synonyms=[domain],
                glossary_term=None,
                canonical_field=None,
                canonical_dataset=dataset_name,
                confidence=0.8,
            )
        )

    return mappings


def vocabulary_prompt_block(mappings: list[VocabularyMapping]) -> str:
    if not mappings:
        return "=== BUSINESS VOCABULARY ===\n(none resolved)"
    lines = ["=== BUSINESS VOCABULARY (use canonical terms) ==="]
    for m in mappings[:12]:
        lines.append(
            f"  {m.user_term} → glossary={m.glossary_term or '-'} "
            f"field={m.canonical_field or '-'} "
            f"dataset={m.canonical_dataset or '-'} "
            f"(conf={m.confidence:.0%})"
        )
        if m.synonyms:
            lines.append(f"    synonyms: {', '.join(m.synonyms[:5])}")
    return "\n".join(lines)


def _best_glossary(seed: str, synonyms: list[str], terms: list[str]) -> Optional[str]:
    candidates = [seed, *synonyms]
    for term in terms:
        t = (term or "").lower()
        for c in candidates:
            if c in t or t.replace(" ", "_") == c:
                return term
    return None


def _best_field(seed: str, synonyms: list[str], fields: list[str]) -> Optional[str]:
    candidates = [seed, *synonyms]
    for f in fields:
        flow = f.lower()
        for c in candidates:
            if c in flow:
                return f
    return None
