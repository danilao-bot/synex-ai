"""SQL Pattern Library — reusable production patterns consulted before generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.context.models import SqlProfile


@dataclass
class PatternLibrary:
    """In-memory / session pattern store derived from production SQL + prior runs."""

    join_patterns: list[str] = field(default_factory=list)
    revenue_calculations: list[str] = field(default_factory=list)
    currency_conversion: list[str] = field(default_factory=list)
    time_filters: list[str] = field(default_factory=list)
    window_functions: list[str] = field(default_factory=list)
    deduplication: list[str] = field(default_factory=list)
    scd_patterns: list[str] = field(default_factory=list)
    preferred_aliases: list[str] = field(default_factory=list)
    business_metrics: list[str] = field(default_factory=list)

    def ingest_profile(self, profile: SqlProfile) -> None:
        self.join_patterns = _merge(self.join_patterns, profile.common_joins)
        self.window_functions = _merge(self.window_functions, [w.split("×")[0] for w in profile.window_functions])
        self.time_filters = _merge(
            self.time_filters,
            [w for w in profile.where_patterns if any(k in w.lower() for k in ("date", "time", "day", "month", "year"))],
        )
        self.business_metrics = _merge(self.business_metrics, profile.derived_metrics)
        self.revenue_calculations = _merge(
            self.revenue_calculations,
            [c for c in profile.business_calculations if any(k in c.lower() for k in ("revenue", "amount", "price", "arr", "mrr"))],
        )
        self.currency_conversion = _merge(
            self.currency_conversion,
            [c for c in profile.business_calculations if "currency" in c.lower() or "fx" in c.lower() or "exchange" in c.lower()],
        )
        self.preferred_aliases = _merge(self.preferred_aliases, list(profile.preferred_aliases.keys()))
        # Heuristic SCD / dedupe from CTE names and windows
        for cte in profile.ctes:
            low = cte.lower()
            if any(k in low for k in ("scd", "history", "snapshot", "version")):
                self.scd_patterns = _merge(self.scd_patterns, [f"CTE `{cte}` suggests SCD/history pattern"])
            if any(k in low for k in ("dedup", "unique", "distinct_")):
                self.deduplication = _merge(self.deduplication, [f"CTE `{cte}` suggests deduplication"])
        if any("ROW_NUMBER" in w.upper() for w in profile.window_functions):
            self.deduplication = _merge(self.deduplication, ["ROW_NUMBER() OVER (...) used for dedupe in production"])

    def ingest_memory(self, memory: dict[str, Any] | None) -> None:
        if not memory:
            return
        patterns = memory.get("sql_patterns") or memory.get("pattern_library") or {}
        if isinstance(patterns, dict):
            for key in (
                "join_patterns",
                "revenue_calculations",
                "currency_conversion",
                "time_filters",
                "window_functions",
                "deduplication",
                "scd_patterns",
                "preferred_aliases",
                "business_metrics",
            ):
                setattr(self, key, _merge(getattr(self, key), patterns.get(key) or []))

    def hints(self) -> list[str]:
        hints: list[str] = []
        for label, values in (
            ("JOIN", self.join_patterns[:4]),
            ("REVENUE_CALC", self.revenue_calculations[:3]),
            ("TIME_FILTER", self.time_filters[:3]),
            ("WINDOW", self.window_functions[:3]),
            ("DEDUPE", self.deduplication[:2]),
            ("SCD", self.scd_patterns[:2]),
            ("METRIC", self.business_metrics[:4]),
            ("ALIAS", self.preferred_aliases[:4]),
        ):
            for v in values:
                hints.append(f"{label}: {v}")
        return hints

    def to_dict(self) -> dict[str, Any]:
        return {
            "join_patterns": self.join_patterns,
            "revenue_calculations": self.revenue_calculations,
            "currency_conversion": self.currency_conversion,
            "time_filters": self.time_filters,
            "window_functions": self.window_functions,
            "deduplication": self.deduplication,
            "scd_patterns": self.scd_patterns,
            "preferred_aliases": self.preferred_aliases,
            "business_metrics": self.business_metrics,
        }

    def to_prompt_section(self) -> str:
        hints = self.hints()
        if not hints:
            return "=== SQL PATTERN LIBRARY ===\n(no production patterns available yet)"
        lines = ["=== SQL PATTERN LIBRARY (reuse before inventing) ==="]
        lines.extend(f"  - {h}" for h in hints[:20])
        return "\n".join(lines)


def _merge(existing: list[str], new: list[str], limit: int = 24) -> list[str]:
    out = list(existing)
    for item in new:
        if item and item not in out:
            out.append(item)
    return out[:limit]
