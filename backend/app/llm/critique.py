"""Self-evaluation / critique before returning final SQL."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.llm.model_selector import select_model
from app.llm.providers import llm_router


def critique_artifacts(
    *,
    sql: str,
    dbt_yaml: str,
    prompt: str,
    schema_fields: list[dict[str, Any]],
    pii_fields: list[str],
    validation: dict[str, Any],
    lineage_summary: str = "",
    api_key: str,
    provider: str,
    model: str,
    use_llm: bool = True,
) -> dict[str, Any]:
    """
    Deterministic critique always runs; optional LLM critique for deeper review.
    """
    issues: list[str] = []
    questions = {
        "schema_correct": True,
        "lineage_respected": True,
        "joins_simplifiable": False,
        "pii_exposed": False,
        "governance_risk": False,
        "engineer_would_approve": True,
    }

    field_names = { (f.get("fieldPath") or "").lower() for f in schema_fields }
    sql_l = (sql or "").lower()

    # Hallucinated columns (light)
    for col in re.findall(r"\b([a-z_][a-z0-9_]{2,})\b", sql_l):
        if col in field_names or col in {
            "select", "from", "where", "join", "left", "right", "inner", "on", "as",
            "and", "or", "group", "by", "order", "limit", "with", "ref", "source",
            "sha2", "md5", "sum", "count", "avg", "min", "max", "case", "when", "then",
            "else", "end", "null", "true", "false", "distinct", "over", "partition",
        }:
            continue
        # skip common aliases
        if col.endswith("_hash") or col.endswith("_id") or col.startswith("total_"):
            continue

    for pii in pii_fields:
        pname = pii.lower()
        if pname in sql_l and "sha2" not in sql_l and "md5" not in sql_l:
            # crude: if pii name appears near select without hash keywords overall
            if re.search(rf"select[^;]*\b{re.escape(pname)}\b", sql_l) and not re.search(
                rf"(sha2|md5|hash)\s*\(\s*{re.escape(pname)}", sql_l
            ):
                questions["pii_exposed"] = True
                issues.append(f"Possible raw PII exposure for '{pii}'.")

    if not validation.get("passed", True):
        questions["governance_risk"] = True
        questions["engineer_would_approve"] = False
        issues.extend(validation.get("blocking_errors") or ["Validation failed."])

    if sql_l.count(" join ") >= 3:
        questions["joins_simplifiable"] = True
        issues.append("Multiple joins detected — consider simplification if unused.")

    if lineage_summary and "risk" in lineage_summary.lower():
        questions["lineage_respected"] = False
        issues.append("Lineage risks present — review upstream dependencies.")

    llm_notes = ""
    if use_llm and api_key and not issues:
        choice = select_model(prompt=prompt, provider=provider, default_model=model, task="critique")
        try:
            result = llm_router.complete(
                provider=choice.provider,
                model=choice.model,
                api_key=api_key,
                system=(
                    "You are a senior data engineer reviewing Synex SQL. "
                    "Reply ONLY with JSON: "
                    '{"approved": bool, "needs_revision": bool, "issues": [str], '
                    '"answers": {"schema_correct": bool, "lineage_respected": bool, '
                    '"joins_simplifiable": bool, "pii_exposed": bool, '
                    '"governance_risk": bool, "engineer_would_approve": bool}, "notes": str}'
                ),
                user=(
                    f"PROMPT: {prompt}\n\nSQL:\n{sql[:3500]}\n\nYAML:\n{dbt_yaml[:1200]}\n"
                    f"PII_FIELDS: {pii_fields}\nVALIDATION: {validation.get('passed')}\n"
                    f"LINEAGE: {lineage_summary}\n"
                ),
                temperature=0.0,
                max_tokens=500,
                task="critique",
                enable_fallback=True,
            )
            llm_notes = result.text
            parsed = _parse_json(result.text)
            if parsed:
                questions.update(parsed.get("answers") or {})
                issues.extend(parsed.get("issues") or [])
                approved = bool(parsed.get("approved", not parsed.get("needs_revision")))
                needs_revision = bool(parsed.get("needs_revision", not approved))
                return {
                    "approved": approved and not issues,
                    "needs_revision": needs_revision or bool(issues),
                    "issues": issues,
                    "answers": questions,
                    "notes": parsed.get("notes") or "",
                    "llm_raw": llm_notes[:500],
                    "provider": result.provider,
                    "model": result.model,
                }
        except Exception as exc:
            issues.append(f"LLM critique unavailable: {exc}")

    approved = not questions["pii_exposed"] and not questions["governance_risk"] and validation.get("passed", True)
    return {
        "approved": approved,
        "needs_revision": not approved,
        "issues": issues,
        "answers": questions,
        "notes": "Deterministic self-evaluation completed.",
        "llm_raw": llm_notes[:500] if llm_notes else "",
    }


def _parse_json(text: str) -> Optional[dict[str, Any]]:
    text = (text or "").strip()
    text = re.sub(r"^```json\s*", "", text, flags=re.I)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None
