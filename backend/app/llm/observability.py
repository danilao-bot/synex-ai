"""AI observability metrics for every Synex run."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class ObservabilityMetrics:
    token_usage_in: int = 0
    token_usage_out: int = 0
    latency_ms: int = 0
    reasoning_duration_ms: int = 0
    generation_duration_ms: int = 0
    validation_duration_ms: int = 0
    retry_count: int = 0
    fallback_used: bool = False
    fallback_providers: list[str] = field(default_factory=list)
    validation_failures: list[str] = field(default_factory=list)
    provider_used: str = ""
    model_used: str = ""
    model_selection_reason: str = ""
    confidence: Optional[float] = None
    attempts: list[dict[str, Any]] = field(default_factory=list)
    started_at: float = field(default_factory=time.perf_counter)

    def add_tokens(self, tin: Optional[int], tout: Optional[int]) -> None:
        self.token_usage_in += int(tin or 0)
        self.token_usage_out += int(tout or 0)

    def mark_fallback(self, provider: str) -> None:
        self.fallback_used = True
        if provider and provider not in self.fallback_providers:
            self.fallback_providers.append(provider)

    def finish(self) -> None:
        self.latency_ms = int((time.perf_counter() - self.started_at) * 1000)

    def to_dict(self) -> dict[str, Any]:
        self.finish()
        return asdict(self)
