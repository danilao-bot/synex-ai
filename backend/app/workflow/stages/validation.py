"""Validation with automatic retry using validator feedback."""

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


class ValidationWorkflow(BaseStage):
    id = "validation"
    label = "Running validation"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        metrics = state.observability or ObservabilityMetrics()
        state.observability = metrics
        max_retries = max(0, int(settings.LLM_MAX_RETRIES))
        attempt = 0

        while True:
            t0 = time.perf_counter()
            report = self._validate(state)
            metrics.validation_duration_ms += int((time.perf_counter() - t0) * 1000)
            state.validation = report

            if report["passed"] or attempt >= max_retries:
                break

            # Retry with validator feedback
            attempt += 1
            metrics.retry_count = attempt
            feedback = "\n".join(report.get("blocking_errors") or [])
            step.logs.append(f"Validation failed — retry {attempt}/{max_retries}: {feedback[:200]}")
            if self._emit:
                self._emit({
                    "step": self._step_index,
                    "type": "RETRY",
                    "stage": "validation",
                    "status": "running",
                    "message": f"Retry {attempt}/{max_retries} using validator feedback.",
                    "retry_count": attempt,
                    "errors": report.get("blocking_errors") or [],
                })

            metrics.validation_failures.extend(report.get("blocking_errors") or [])
            eng = state.engineering_context
            selected = state.selected_candidate or {}

            def on_attempt(meta: dict[str, Any]) -> None:
                metrics.attempts.append(meta)
                if meta.get("index", 0) > 0:
                    metrics.mark_fallback(meta.get("provider") or "")

            regenerated = generator.generate_code_and_contract(
                table_name=eng.selected_name if eng else selected.get("name") or "model",
                pii_columns=(eng.pii_fields if eng else selected.get("pii_fields") or []),
                dialect=state.target_dialect,
                prompt=state.prompt,
                schema_fields=eng.schema_fields if eng else [],
                previous_sql=state.previous_sql,
                enriched_context_block=eng.to_prompt_block() if eng else None,
                llm_api_key=state.llm_api_key,
                llm_model=state.llm_model,
                llm_provider=state.llm_provider,
                intent=state.intent,
                retry_feedback=feedback,
                on_attempt=on_attempt,
                memory_section=memory_to_prompt_section(state.engineering_memory or {}),
                task_hint="complex",
            )
            meta = regenerated.get("llm_meta") or {}
            metrics.add_tokens(meta.get("tokens_in"), meta.get("tokens_out"))
            metrics.provider_used = meta.get("provider") or metrics.provider_used
            metrics.model_used = meta.get("model") or metrics.model_used
            if meta.get("fallback_used"):
                metrics.fallback_used = True

            # Preserve prior docs fields
            prior = state.generated or {}
            regenerated["documentation"] = prior.get("documentation") or regenerated.get("documentation")
            regenerated["business_explanation"] = prior.get("business_explanation")
            regenerated["potential_risks"] = prior.get("potential_risks") or []
            state.generated = regenerated

            if self._emit:
                self._emit({
                    "step": self._step_index,
                    "type": "SQL_TOKEN",
                    "stage": "validation",
                    "status": "running",
                    "message": (regenerated.get("sql") or "")[:400],
                    "partial": True,
                    "retry": attempt,
                })

        msg = (
            "Validation passed."
            if state.validation.get("passed")
            else f"Validation failed after {attempt} retry(ies) "
            f"({len(state.validation.get('blocking_errors') or [])} blocking)."
        )
        step.complete(
            message=msg,
            outputs={
                "passed": state.validation.get("passed"),
                "blocking_errors": state.validation.get("blocking_errors"),
                "warnings": state.validation.get("warnings"),
                "retry_count": attempt,
                "extended": state.validation.get("extended"),
            },
            warnings=(state.validation.get("warnings") or [])[:5] or None,
            reasoning_summary=msg,
        )
        return state

    def _validate(self, state: WorkflowState) -> dict[str, Any]:
        selected = state.selected_candidate or {}
        eng = state.engineering_context
        sql = (state.generated or {}).get("sql") or ""
        dbt_yaml = (state.generated or {}).get("dbt_yaml") or ""
        schema_fields = eng.schema_fields if eng else []
        pii_fields = eng.pii_fields if eng else selected.get("pii_fields") or []

        report = validator.validate_governance(
            sql=sql,
            dbt_yaml=dbt_yaml,
            schema_fields=schema_fields,
            pii_fields=pii_fields,
            is_deprecated=bool(selected.get("is_deprecated")),
            allow_deprecated_override=state.allow_deprecated_override,
            dialect=state.target_dialect,
        )
        extra_warnings = list(report.get("warnings") or [])
        extra_blocking = list(report.get("blocking_errors") or [])

        name = (eng.selected_name if eng else selected.get("name") or "").lower()
        if name and not any(name.startswith(p) for p in ("fct_", "dim_", "stg_", "int_", "mart_")):
            extra_warnings.append(
                f"Source name '{name}' does not follow common dbt naming prefixes (fct_/dim_/stg_)."
            )
        if state.lineage_report.get("broken_lineage") or selected.get("upstream_risks"):
            extra_warnings.append("Lineage consistency: upstream risks may affect generated model reliability.")
        q = state.quality_report or {}
        if q.get("validation_status") == "fail":
            extra_blocking.append("Quality workflow marked selected dataset as fail.")
        elif q.get("low_confidence"):
            extra_warnings.append("Quality confidence was low at selection time.")

        report = {
            **report,
            "warnings": extra_warnings,
            "blocking_errors": extra_blocking,
            "extended": {
                "naming_conventions": "checked",
                "lineage_consistency": "checked",
                "quality_compatibility": q.get("validation_status"),
                "business_rules": state.intent.risk_level if state.intent else "medium",
                "governance": True,
            },
        }
        report["passed"] = len(report["blocking_errors"]) == 0
        return report
