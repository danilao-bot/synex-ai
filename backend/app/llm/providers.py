"""LLM provider abstraction with automatic failover."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    latency_ms: int = 0
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    fallback_used: bool = False
    attempts: list[dict[str, Any]] = field(default_factory=list)


class ProviderError(Exception):
    def __init__(self, message: str, *, retryable: bool = True, kind: str = "provider"):
        super().__init__(message)
        self.retryable = retryable
        self.kind = kind  # timeout | rate_limit | unavailable | generation


class LLMProviderRouter:
    """
    Multi-provider router: OpenAI / Anthropic / Gemini / Groq / OpenRouter.
    Falls through configurable order on timeout, rate limit, or failure.
    """

    def __init__(self) -> None:
        self._compat_bases = {
            "openrouter": settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1",
            "openai": "https://api.openai.com/v1",
            "groq": "https://api.groq.com/openai/v1",
            "together": "https://api.together.xyz/v1",
            "mistral": "https://api.mistral.ai/v1",
            "deepseek": "https://api.deepseek.com/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta/openai/",
        }

    def fallback_chain(
        self,
        primary_provider: str,
        primary_model: str,
        api_key: str,
        task: str = "generation",
    ) -> list[dict[str, str]]:
        """Build ordered provider/model attempts."""
        order = [
            p.strip()
            for p in (settings.LLM_FALLBACK_ORDER or "openrouter,openai,anthropic,groq,gemini").split(",")
            if p.strip()
        ]
        # Ensure primary first
        primary = (primary_provider or "openrouter").lower()
        chain: list[dict[str, str]] = [{"provider": primary, "model": primary_model, "api_key": api_key}]
        for p in order:
            pl = p.lower()
            if pl == primary:
                continue
            key = self._key_for(pl, api_key)
            if not key:
                continue
            chain.append({"provider": pl, "model": self._default_model(pl, task), "api_key": key})
        return chain

    def _key_for(self, provider: str, primary_key: str) -> str:
        # Prefer dedicated keys when set; else reuse primary for openrouter-compatible
        mapping = {
            "openai": settings.OPENAI_API_KEY or (primary_key if provider == "openai" else ""),
            "anthropic": settings.ANTHROPIC_API_KEY or "",
            "groq": settings.GROQ_API_KEY or "",
            "gemini": settings.GEMINI_API_KEY or "",
            "openrouter": settings.LLM_API_KEY or primary_key,
        }
        if provider in mapping and mapping[provider]:
            return mapping[provider]
        # OpenRouter can proxy many models with the primary key
        if provider == "openrouter":
            return primary_key
        # Allow primary key for openai-compat when same key works
        if provider in ("openai", "groq") and primary_key and settings.LLM_PROVIDER == provider:
            return primary_key
        return mapping.get(provider) or ""

    def _default_model(self, provider: str, task: str) -> str:
        if task == "validation" or task == "critique":
            defaults = {
                "openrouter": "openai/gpt-4o-mini",
                "openai": "gpt-4o-mini",
                "anthropic": "claude-3-5-haiku-latest",
                "groq": "llama-3.1-8b-instant",
                "gemini": "gemini-2.0-flash",
            }
        elif task == "complex":
            defaults = {
                "openrouter": "openai/gpt-4o",
                "openai": "gpt-4o",
                "anthropic": "claude-sonnet-4-20250514",
                "groq": "llama-3.3-70b-versatile",
                "gemini": "gemini-2.0-flash",
            }
        else:
            defaults = {
                "openrouter": settings.LLM_MODEL or "openai/gpt-4o",
                "openai": "gpt-4o-mini",
                "anthropic": "claude-3-5-haiku-latest",
                "groq": "llama-3.1-8b-instant",
                "gemini": "gemini-2.0-flash",
            }
        return defaults.get(provider, settings.LLM_MODEL)

    def complete(
        self,
        *,
        provider: str,
        model: str,
        api_key: str,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        task: str = "generation",
        enable_fallback: bool = True,
        on_attempt: Optional[Callable[[dict[str, Any]], None]] = None,
    ) -> LLMResult:
        chain = self.fallback_chain(provider, model, api_key, task=task) if enable_fallback else [
            {"provider": provider, "model": model, "api_key": api_key}
        ]
        attempts: list[dict[str, Any]] = []
        last_err: Exception | None = None

        for idx, attempt in enumerate(chain):
            p, m, k = attempt["provider"], attempt["model"], attempt["api_key"]
            if not k:
                continue
            started = time.perf_counter()
            meta = {"provider": p, "model": m, "index": idx}
            if on_attempt:
                on_attempt({**meta, "status": "starting"})
            try:
                text, tok_in, tok_out = self._call(p, k, m, system, user, temperature, max_tokens)
                latency = int((time.perf_counter() - started) * 1000)
                meta.update({"status": "ok", "latency_ms": latency})
                attempts.append(meta)
                if on_attempt:
                    on_attempt(meta)
                return LLMResult(
                    text=text,
                    provider=p,
                    model=m,
                    latency_ms=latency,
                    tokens_in=tok_in,
                    tokens_out=tok_out,
                    fallback_used=idx > 0,
                    attempts=attempts,
                )
            except Exception as exc:
                latency = int((time.perf_counter() - started) * 1000)
                kind = self._classify(exc)
                meta.update({"status": "failed", "error": str(exc)[:300], "kind": kind, "latency_ms": latency})
                attempts.append(meta)
                if on_attempt:
                    on_attempt(meta)
                last_err = exc
                logger.warning("LLM provider %s/%s failed (%s): %s", p, m, kind, exc)
                continue

        raise ProviderError(
            f"All LLM providers failed. Last error: {last_err}",
            retryable=False,
            kind="unavailable",
        )

    def _classify(self, exc: Exception) -> str:
        msg = str(exc).lower()
        if "rate" in msg or "429" in msg:
            return "rate_limit"
        if "timeout" in msg or "timed out" in msg:
            return "timeout"
        if "401" in msg or "403" in msg or "auth" in msg:
            return "unavailable"
        return "generation"

    def _call(
        self,
        provider: str,
        api_key: str,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, Optional[int], Optional[int]]:
        p = provider.lower()
        if p == "anthropic":
            return self._anthropic(api_key, model, system, user, max_tokens)
        # OpenAI-compatible (openai, openrouter, groq, gemini openai bridge, etc.)
        base = self._compat_bases.get(p, settings.OPENROUTER_BASE_URL)
        return self._openai_compat(api_key, base, model, system, user, temperature, max_tokens)

    def _openai_compat(
        self,
        api_key: str,
        base_url: str,
        model: str,
        system: str,
        user: str,
        temperature: float,
        max_tokens: int,
    ) -> tuple[str, Optional[int], Optional[int]]:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=base_url, timeout=settings.LLM_TIMEOUT_SECONDS)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = (response.choices[0].message.content or "").strip()
        usage = getattr(response, "usage", None)
        tok_in = getattr(usage, "prompt_tokens", None) if usage else None
        tok_out = getattr(usage, "completion_tokens", None) if usage else None
        return text, tok_in, tok_out

    def _anthropic(
        self,
        api_key: str,
        model: str,
        system: str,
        user: str,
        max_tokens: int,
    ) -> tuple[str, Optional[int], Optional[int]]:
        try:
            import anthropic
        except ImportError as exc:
            raise ProviderError("anthropic package not installed", retryable=False) from exc
        client = anthropic.Anthropic(api_key=api_key, timeout=settings.LLM_TIMEOUT_SECONDS)
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = message.content[0].text.strip()
        usage = getattr(message, "usage", None)
        tok_in = getattr(usage, "input_tokens", None) if usage else None
        tok_out = getattr(usage, "output_tokens", None) if usage else None
        return text, tok_in, tok_out


llm_router = LLMProviderRouter()
