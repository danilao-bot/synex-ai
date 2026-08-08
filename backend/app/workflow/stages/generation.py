"""Generation + validation retry loop with provider fallback and streaming hooks."""

from __future__ import annotations

import time
from typing import Any

from app.agent.generator import generator
from app.agent.validator import validator
from app.core.config import settings
from app.llm.observability import ObservabilityMetrics
from app.memory.engineering_memory import memory_to_prompt_section
from app.workflow.base import BaseStage
from app.workflow.models import WorkflowState, WorkflowStep


class GenerationWorkflow(BaseStage):
    id = "generation"
    label = "Generating artifacts"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        eng = state.engineering_context
        selected = state.selected_candidate or {}
        if not eng:
            raise RuntimeError("Engineering context missing — cannot generate.")

        metrics = state.observability or ObservabilityMetrics()
        state.observability = metrics

        def on_attempt(meta: dict[str, Any]) -> None:
            metrics.attempts.append(meta)
            if meta.get("status") == "ok" and meta.get("index", 0) > 0:
                metrics.mark_fallback(meta.get("provider") or "")
            if self._emit:
                self._emit({
                    "step": self._step_index,
                    "type": "LLM_ATTEMPT",
                    "stage": "generation",
                    "stage_label": "LLM provider attempt",
                    "status": meta.get("status"),
                    "message": f"{meta.get('provider')}/{meta.get('model')}: {meta.get('status')}",
                    "provider": meta.get("provider"),
                    "model": meta.get("model"),
                    "fallback": meta.get("index", 0) > 0,
                })

        memory_section = memory_to_prompt_section(state.engineering_memory or {})
        step.logs.append("LLM receives Context Engine package + engineering memory only.")
        if eng.context_manifest:
            for line in (eng.context_manifest.get("checklist") or [])[:6]:
                step.logs.append(f"context: {line}")

        # Stream planning/reasoning cue before tokens
        if self._emit:
            self._emit({
                "step": self._step_index,
                "type": "REASONING",
                "stage": "generation",
                "status": "running",
                "message": "Planning SQL from engineering context…",
            })

        t0 = time.perf_counter()
        generated = generator.generate_code_and_contract(
            table_name=eng.selected_name or selected.get("name") or "model",
            pii_columns=eng.pii_fields,
            dialect=state.target_dialect,
            prompt=state.prompt,
            schema_fields=eng.schema_fields,
            previous_sql=state.previous_sql,
            enriched_context_block=eng.to_prompt_block(),
            llm_api_key=state.llm_api_key,
            llm_model=state.llm_model,
            llm_provider=state.llm_provider,
            intent=state.intent,
            on_attempt=on_attempt,
            memory_section=memory_section,
        )
        metrics.generation_duration_ms += int((time.perf_counter() - t0) * 1000)
        meta = generated.get("llm_meta") or {}
        metrics.provider_used = meta.get("provider") or metrics.provider_used
        metrics.model_used = meta.get("model") or metrics.model_used
        metrics.model_selection_reason = meta.get("model_selection_reason") or ""
        metrics.add_tokens(meta.get("tokens_in"), meta.get("tokens_out"))
        if meta.get("fallback_used"):
            metrics.fallback_used = True

        # Stream SQL preview chunks (token-ish progress for UI)
        sql = generated.get("sql") or ""
        if self._emit and sql:
            chunk_size = max(80, len(sql) // 4)
            for i in range(0, len(sql), chunk_size):
                self._emit({
                    "step": self._step_index,
                    "type": "SQL_TOKEN",
                    "stage": "generation",
                    "status": "running",
                    "message": sql[i : i + chunk_size],
                    "partial": True,
                })

        trust = selected.get("trust_score") or 0
        generated["documentation"] = (
            f"# Synex Generated Model\n\nSource: `{eng.selected_name}`\nTrust: {trust}/100\n"
            f"Provider: {meta.get('provider')} / {meta.get('model')}\n"
        )
        generated["business_explanation"] = eng.reasoning_summary or ""
        generated["confidence_explanation"] = meta.get("model_selection_reason") or ""
        generated["expected_output"] = f"dbt model SQL ({state.target_dialect}) + schema.yml"
        generated["potential_risks"] = list(state.global_warnings)
        state.generated = generated

        step.complete(
            message=f"Generated via {meta.get('provider')}/{meta.get('model')} ({meta.get('task')}).",
            outputs={
                "sql_chars": len(sql),
                "provider": meta.get("provider"),
                "model": meta.get("model"),
                "fallback_used": meta.get("fallback_used"),
                "model_selection_reason": meta.get("model_selection_reason"),
            },
            reasoning_summary=meta.get("model_selection_reason") or "",
            trust_score=trust,
        )
        return state
