"""Intelligent model selection by task complexity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.core.config import settings


@dataclass
class ModelChoice:
    provider: str
    model: str
    task: str
    reason: str


def select_model(
    *,
    prompt: str,
    intent: Any = None,
    provider: Optional[str] = None,
    default_model: Optional[str] = None,
    task: str = "generation",
) -> ModelChoice:
    """
    Simple SQL → fast model
    Complex dbt / high risk → large reasoning model
    Validation / critique → fast verifier
    """
    provider = (provider or settings.LLM_PROVIDER or "openrouter").lower()
    default_model = default_model or settings.LLM_MODEL

    if task in ("validation", "critique", "verify"):
        return ModelChoice(
            provider=provider,
            model=_fast(provider),
            task="critique",
            reason="Self-evaluation / verifier uses a fast model.",
        )

    complexity = _complexity(prompt, intent)
    if complexity >= 7:
        return ModelChoice(
            provider=provider,
            model=_large(provider, default_model),
            task="complex",
            reason="Complex dbt / multi-join / high-risk request → large reasoning model.",
        )
    if complexity <= 3:
        return ModelChoice(
            provider=provider,
            model=_fast(provider),
            task="simple",
            reason="Simple SQL request → fast model.",
        )
    return ModelChoice(
        provider=provider,
        model=default_model,
        task="generation",
        reason="Standard generation using configured model.",
    )


def _complexity(prompt: str, intent: Any) -> int:
    score = 4
    lower = (prompt or "").lower()
    for kw, pts in (
        ("join", 1),
        ("dbt", 1),
        ("incremental", 2),
        ("scd", 2),
        ("window", 1),
        ("pii", 1),
        ("lineage", 1),
        ("multi", 1),
        ("aggregate", 1),
        ("mart", 1),
    ):
        if kw in lower:
            score += pts
    if intent:
        if getattr(intent, "risk_level", "") == "high":
            score += 2
        if getattr(intent, "desired_artifact", "") == "dbt_sql_and_schema_yml":
            score += 1
        if len(getattr(intent, "required_metadata", []) or []) >= 5:
            score += 1
    if len(prompt or "") > 400:
        score += 1
    return min(10, score)


def _fast(provider: str) -> str:
    return {
        "openrouter": settings.LLM_FAST_MODEL or "openai/gpt-4o-mini",
        "openai": "gpt-4o-mini",
        "anthropic": "claude-3-5-haiku-latest",
        "groq": "llama-3.1-8b-instant",
        "gemini": "gemini-2.0-flash",
    }.get(provider, settings.LLM_FAST_MODEL or "openai/gpt-4o-mini")


def _large(provider: str, default_model: str) -> str:
    return {
        "openrouter": settings.LLM_REASONING_MODEL or default_model or "openai/gpt-4o",
        "openai": "gpt-4o",
        "anthropic": "claude-sonnet-4-20250514",
        "groq": "llama-3.3-70b-versatile",
        "gemini": "gemini-2.0-flash",
    }.get(provider, default_model)
