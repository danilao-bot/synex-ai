"""Production SQL profiler — extract reusable patterns from real queries."""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

from app.context.models import SqlProfile

_JOIN_RE = re.compile(
    r"\b((?:LEFT|RIGHT|INNER|FULL|CROSS)?\s*JOIN)\s+([`\"\[]?[\w.]+[`\"\]]?)(?:\s+(?:AS\s+)?(\w+))?",
    re.I,
)
_FROM_RE = re.compile(r"\bFROM\s+([`\"\[]?[\w.]+[`\"\]]?)(?:\s+(?:AS\s+)?(\w+))?", re.I)
_WHERE_RE = re.compile(r"\bWHERE\b(.{0,240}?)(?:\bGROUP\b|\bORDER\b|\bLIMIT\b|\bHAVING\b|$)", re.I | re.S)
_GROUP_RE = re.compile(r"\bGROUP\s+BY\s+([^\n]+?)(?:\bORDER\b|\bHAVING\b|\bLIMIT\b|$)", re.I | re.S)
_AGG_RE = re.compile(r"\b(SUM|COUNT|AVG|MIN|MAX|COUNT_IF|APPROX_COUNT_DISTINCT)\s*\(", re.I)
_WIN_RE = re.compile(r"\b(ROW_NUMBER|RANK|DENSE_RANK|LAG|LEAD|SUM|AVG|COUNT)\s*\([^)]*\)\s*OVER\s*\(", re.I)
_CTE_RE = re.compile(r"\bWITH\s+(\w+)\s+AS\s*\(|,\s*(\w+)\s+AS\s*\(", re.I)
_DATE_RE = re.compile(
    r"\b(DATE_TRUNC|DATEADD|DATEDIFF|CURRENT_DATE|CURRENT_TIMESTAMP|GETDATE|TO_DATE|CAST\s*\([^)]*AS\s+DATE)",
    re.I,
)
_NULL_RE = re.compile(r"\b(COALESCE|IFNULL|NVL|NULLIF|IS\s+NULL|IS\s+NOT\s+NULL)\b", re.I)
_CALC_RE = re.compile(
    r"([A-Za-z_][\w.]*)\s*([*/+-])\s*([A-Za-z_][\w.]*)|AS\s+(gross_|net_|total_|arr_|mrr_|revenue_)\w*",
    re.I,
)
_ALIAS_RE = re.compile(r"\bAS\s+([a-zA-Z_][\w]*)", re.I)


def profile_queries(queries: Iterable[str]) -> SqlProfile:
    qs = [q.strip() for q in queries if q and str(q).strip()]
    profile = SqlProfile(query_count=len(qs), sample_queries=qs[:5])
    if not qs:
        return profile

    joined: Counter[str] = Counter()
    joins: list[str] = []
    wheres: list[str] = []
    groups: list[str] = []
    aggs: Counter[str] = Counter()
    windows: Counter[str] = Counter()
    ctes: Counter[str] = Counter()
    dates: Counter[str] = Counter()
    nulls: Counter[str] = Counter()
    calcs: list[str] = []
    aliases: Counter[str] = Counter()
    naming: list[str] = []

    for q in qs:
        for m in _JOIN_RE.finditer(q):
            jtype, table, alias = m.group(1), m.group(2), m.group(3)
            table_clean = table.strip("`\"[]")
            joined[table_clean] += 1
            joins.append(f"{jtype.strip().upper()} {table_clean}" + (f" AS {alias}" if alias else ""))
        for m in _FROM_RE.finditer(q):
            table = m.group(1).strip("`\"[]")
            joined[table] += 0  # register presence
        wm = _WHERE_RE.search(q)
        if wm:
            clause = " ".join(wm.group(1).split())[:180]
            if clause:
                wheres.append(clause)
        gm = _GROUP_RE.search(q)
        if gm:
            groups.append(" ".join(gm.group(1).split())[:120])
        for m in _AGG_RE.finditer(q):
            aggs[m.group(1).upper()] += 1
        for m in _WIN_RE.finditer(q):
            windows[m.group(1).upper()] += 1
        for m in _CTE_RE.finditer(q):
            name = m.group(1) or m.group(2)
            if name:
                ctes[name] += 1
        for m in _DATE_RE.finditer(q):
            dates[m.group(1).split("(")[0].upper()] += 1
        for m in _NULL_RE.finditer(q):
            nulls[m.group(1).upper().replace("  ", " ")] += 1
        for m in _CALC_RE.finditer(q):
            snippet = m.group(0)
            if snippet and snippet not in calcs:
                calcs.append(snippet[:120])
        for m in _ALIAS_RE.finditer(q):
            aliases[m.group(1)] += 1

        lower = q.lower()
        if "fct_" in lower or "dim_" in lower or "stg_" in lower:
            naming.append("dbt-style fct_/dim_/stg_ prefixes observed")
        if "sha2" in lower or "md5" in lower:
            naming.append("hashing transforms present in production SQL")

    profile.frequently_joined_tables = [t for t, _ in joined.most_common(10) if t]
    profile.common_joins = list(dict.fromkeys(joins))[:12]
    profile.where_patterns = list(dict.fromkeys(wheres))[:10]
    profile.group_by_patterns = list(dict.fromkeys(groups))[:8]
    profile.aggregations = [f"{k}×{v}" for k, v in aggs.most_common(8)]
    profile.window_functions = [f"{k}×{v}" for k, v in windows.most_common(8)]
    profile.ctes = [k for k, _ in ctes.most_common(10)]
    profile.date_handling = [f"{k}×{v}" for k, v in dates.most_common(6)]
    profile.null_handling = [f"{k}×{v}" for k, v in nulls.most_common(6)]
    profile.business_calculations = calcs[:8]
    profile.derived_metrics = [a for a, _ in aliases.most_common(12) if any(
        a.lower().startswith(p) for p in ("total_", "gross_", "net_", "arr_", "mrr_", "avg_", "cnt_")
    )]
    profile.alias_conventions = [f"{a}×{c}" for a, c in aliases.most_common(10)]
    profile.preferred_aliases = {a: a for a, _ in aliases.most_common(8)}
    profile.naming_conventions = list(dict.fromkeys(naming))[:6]
    return profile
