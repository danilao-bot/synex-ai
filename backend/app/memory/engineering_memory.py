"""Structured engineering memory — reusable across sessions (not raw chat)."""

from __future__ import annotations

from typing import Any, Optional


def build_engineering_memory(
    *,
    state_like: dict[str, Any] | None = None,
    previous_run: dict[str, Any] | None = None,
    prior_memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge prior memory + last run into structured engineering memory."""
    mem: dict[str, Any] = {
        "previous_sql": None,
        "previous_validation": None,
        "previous_datasets": [],
        "previous_metadata": {},
        "previous_glossary": [],
        "previous_lineage": {},
        "previous_dbt_models": [],
        "previous_writeback_proposals": [],
        "preferred_joins": [],
        "preferred_datasets": [],
        "frequently_used_dimensions": [],
        "business_metrics": [],
        "previous_corrections": [],
        "validation_failures": [],
        "successful_sql": [],
        "rejected_sql": [],
        "trust_history": [],
        "sql_patterns": {},
        "vocabulary": [],
        "warnings": [],
        "pattern_library": {},
        "approvals": [],
    }

    if prior_memory:
        for k, v in prior_memory.items():
            if v is not None:
                mem[k] = v

    if previous_run:
        mem["previous_sql"] = previous_run.get("sql") or mem.get("previous_sql")
        mem["previous_validation"] = {
            "status": previous_run.get("status"),
            "target_urn": previous_run.get("target_urn"),
            "target_name": previous_run.get("target_name"),
        }
        if previous_run.get("target_urn"):
            mem["previous_datasets"] = _uniq(
                mem.get("previous_datasets") or [],
                [{"urn": previous_run.get("target_urn"), "name": previous_run.get("target_name")}],
            )
            mem["preferred_datasets"] = _uniq_str(
                mem.get("preferred_datasets") or [],
                [previous_run.get("target_name") or previous_run.get("target_urn")],
            )
        if previous_run.get("dbt_yaml"):
            mem["previous_dbt_models"] = _uniq_str(
                mem.get("previous_dbt_models") or [],
                [previous_run.get("dbt_yaml")[:800]],
            )
        # Pull structured fields if persisted
        ctx = previous_run.get("context_summary") or {}
        if isinstance(ctx, dict) and ctx:
            mem["previous_metadata"] = {**(mem.get("previous_metadata") or {}), **ctx}
        expl = previous_run.get("sql_explanation")
        if expl:
            mem["previous_corrections"] = _uniq_str(
                mem.get("previous_corrections") or [],
                [str((expl or {}).get("summary") or expl)[:400]],
            )
        trace = previous_run.get("trace_logs") or previous_run.get("workflow_steps") or []
        for step in trace:
            if not isinstance(step, dict):
                continue
            if (step.get("status") == "failed" or "fail" in str(step.get("message") or "").lower()) and step.get("errors"):
                mem["validation_failures"] = _uniq_str(
                    mem.get("validation_failures") or [],
                    list(step.get("errors") or [])[:5],
                )

    if state_like:
        selected = state_like.get("selected_dataset") or {}
        eng_mem = state_like.get("engineering_memory") or {}
        for k, v in eng_mem.items():
            if v is not None:
                mem[k] = v
        if state_like.get("sql"):
            passed = (state_like.get("validation") or {}).get("passed")
            if passed:
                mem["successful_sql"] = _uniq_str(mem.get("successful_sql") or [], [state_like["sql"][:2000]])
            elif passed is False:
                mem["rejected_sql"] = _uniq_str(mem.get("rejected_sql") or [], [state_like["sql"][:2000]])
                errs = (state_like.get("validation") or {}).get("blocking_errors") or []
                mem["validation_failures"] = _uniq_str(mem.get("validation_failures") or [], errs[:8])
        if selected.get("urn"):
            mem["previous_datasets"] = _uniq(
                mem.get("previous_datasets") or [],
                [{"urn": selected.get("urn"), "name": selected.get("name")}],
            )
            mem["trust_history"] = (mem.get("trust_history") or [])[-19:] + [
                {"urn": selected.get("urn"), "trust": selected.get("trust_score")}
            ]
        pkg = state_like.get("context_package") or {}
        if pkg.get("glossary"):
            mem["previous_glossary"] = [
                g.get("name") if isinstance(g, dict) else str(g) for g in pkg["glossary"]
            ][:20]
        if pkg.get("recommended_joins"):
            mem["preferred_joins"] = _uniq_str(mem.get("preferred_joins") or [], pkg["recommended_joins"][:12])
        if pkg.get("sql_profile"):
            mem["sql_patterns"] = pkg["sql_profile"]
            dims = (pkg["sql_profile"].get("group_by_patterns") or [])[:8]
            mem["frequently_used_dimensions"] = _uniq_str(mem.get("frequently_used_dimensions") or [], dims)
            mem["business_metrics"] = _uniq_str(
                mem.get("business_metrics") or [],
                pkg["sql_profile"].get("derived_metrics") or [],
            )
        if state_like.get("lineage_impact"):
            mem["previous_lineage"] = {
                "upstream": (state_like["lineage_impact"].get("upstream") or [])[:10],
                "downstream_count": state_like["lineage_impact"].get("downstream_impact_count"),
            }
        if state_like.get("proposed_writeback"):
            mem["previous_writeback_proposals"] = [state_like["proposed_writeback"]]
        if state_like.get("warnings"):
            mem["warnings"] = state_like["warnings"][:12]

    mem["previous_sql"] = mem.get("previous_sql")
    return mem


def memory_to_prompt_section(mem: dict[str, Any]) -> str:
    lines = ["=== ENGINEERING MEMORY (structured — not raw chat) ==="]
    if mem.get("previous_sql"):
        lines.append("PREVIOUS_SQL:")
        lines.append(str(mem["previous_sql"])[:2500])
    if mem.get("previous_validation"):
        lines.append(f"PREVIOUS_VALIDATION: {mem['previous_validation']}")
    if mem.get("preferred_datasets"):
        lines.append(f"PREFERRED_DATASETS: {', '.join(mem['preferred_datasets'][:6])}")
    if mem.get("preferred_joins"):
        lines.append("PREFERRED_JOINS:")
        for j in mem["preferred_joins"][:6]:
            lines.append(f"  - {j}")
    if mem.get("frequently_used_dimensions"):
        lines.append(f"DIMENSIONS: {', '.join(str(d)[:80] for d in mem['frequently_used_dimensions'][:6])}")
    if mem.get("business_metrics"):
        lines.append(f"METRICS: {', '.join(mem['business_metrics'][:6])}")
    if mem.get("validation_failures"):
        lines.append("PRIOR_VALIDATION_FAILURES (avoid repeating):")
        for e in mem["validation_failures"][:6]:
            lines.append(f"  - {e}")
    if mem.get("rejected_sql"):
        lines.append("REJECTED_SQL_EXCERPT (do not repeat mistakes):")
        lines.append(str(mem["rejected_sql"][-1])[:800])
    if mem.get("successful_sql"):
        lines.append("SUCCESSFUL_SQL_EXCERPT (prefer similar patterns):")
        lines.append(str(mem["successful_sql"][-1])[:800])
    if mem.get("previous_glossary"):
        lines.append(f"PRIOR_GLOSSARY: {', '.join(mem['previous_glossary'][:8])}")
    if mem.get("trust_history"):
        lines.append(f"TRUST_HISTORY: {mem['trust_history'][-5:]}")
    return "\n".join(lines)


def _uniq(existing: list, new_items: list, limit: int = 20) -> list:
    out = list(existing)
    for item in new_items:
        if item and item not in out:
            out.append(item)
    return out[:limit]


def _uniq_str(existing: list, new_items: list, limit: int = 24) -> list:
    out = [x for x in existing if x]
    for item in new_items:
        if item and item not in out:
            out.append(item)
    return out[:limit]
