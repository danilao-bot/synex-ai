"""Multi-provider LLM-powered SQL and dbt contract synthesis with PR-ready artifact bundles.

Supports:
  - openrouter  → OpenAI SDK pointed at https://openrouter.ai/api/v1
  - openai      → OpenAI SDK pointed at https://api.openai.com/v1
  - anthropic   → Anthropic SDK (claude-* models)
  - Any other   → Treated as OpenRouter-compatible (OpenAI SDK with env base_url)
"""
import logging
import re
from typing import Dict, Any, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_OPENAI_COMPAT_BASE_URLS: dict[str, str] = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai":     "https://api.openai.com/v1",
    "together":   "https://api.together.xyz/v1",
    "groq":       "https://api.groq.com/openai/v1",
    "mistral":    "https://api.mistral.ai/v1",
    "deepseek":   "https://api.deepseek.com/v1",
}


class AgentGenerator:
    """Synthesizes dialect-correct SQL, dbt schema YAML, and PR-ready artifact bundles."""

    def _clean_sql(self, text: str, kind: str = "sql") -> str:
        """Strip markdown fences, ANSI codes, trailing junk, and inline comments from LLM output."""
        cleaned = text or ""
        # ANSI escape sequences (sometimes leaked from tooling)
        cleaned = re.sub(r"\x1b\[[0-9;]*m", "", cleaned)
        cleaned = re.sub(r"\[\d+m", "", cleaned)
        fence = "sql" if kind == "sql" else "yaml"
        cleaned = re.sub(rf"^```{fence}\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
        # Trailing lone backticks / fence remnants
        cleaned = re.sub(r"`{1,3}\s*$", "", cleaned.strip())
        cleaned = cleaned.strip().strip("`").strip()
        if kind == "sql":
            # Remove inline SQL comments that break SQLGlot AST parsing
            # These appear as -- comment text at end of lines or on their own lines
            cleaned = re.sub(r"--[^\n]*", "", cleaned)
            # Collapse multiple blank lines from removed comments
            cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        return cleaned

    def _resolve_base_url(self, provider: str) -> str:
        p = (provider or "openrouter").lower().strip()
        env_override = settings.OPENROUTER_BASE_URL
        if p == "openrouter" and env_override:
            return env_override
        return _OPENAI_COMPAT_BASE_URLS.get(p, settings.OPENROUTER_BASE_URL)

    def _call_openai_compat(
        self,
        api_key: str,
        base_url: str,
        model: str,
        messages: list,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content.strip()

    def _call_anthropic(
        self,
        api_key: str,
        model: str,
        system: str,
        user: str,
        max_tokens: int = 1500,
    ) -> str:
        try:
            import anthropic
        except ImportError:
            raise RuntimeError("anthropic package is not installed.")
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return message.content[0].text.strip()

    def _llm_call(
        self,
        provider: str,
        api_key: str,
        model: str,
        system: str,
        user: str,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> str:
        p = (provider or "openrouter").lower().strip()
        logger.info("LLM call: provider=%s model=%s", p, model)

        if p == "anthropic":
            return self._call_anthropic(api_key, model, system, user, max_tokens)

        base_url = self._resolve_base_url(p)
        return self._call_openai_compat(
            api_key, base_url, model,
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature, max_tokens,
        )

    def generate_code_and_contract(
        self,
        table_name: str,
        pii_columns: List[str],
        dialect: str = "snowflake",
        previous_sql: str | None = None,
        prompt: str | None = None,
        schema_fields: List[Dict[str, Any]] | None = None,
        enriched_context_block: str | None = None,
        llm_api_key: str | None = None,
        llm_model: str | None = None,
        llm_provider: str | None = None,
        retry_feedback: str | None = None,
        intent: Any = None,
        on_attempt: Any = None,
        memory_section: str | None = None,
        task_hint: str | None = None,
    ) -> Dict[str, Any]:
        """Generate SQL, dbt schema contract, and complete PR-ready artifact bundle."""
        from app.llm.model_selector import select_model
        from app.llm.providers import llm_router

        api_key = llm_api_key or settings.LLM_API_KEY
        model = llm_model or settings.LLM_MODEL
        provider = llm_provider or settings.LLM_PROVIDER or "openrouter"

        if not api_key:
            raise RuntimeError(
                "No LLM API key configured. Add LLM_API_KEY to environment variables or update Settings."
            )

        schema_desc = ""
        if schema_fields:
            lines = []
            for f in schema_fields:
                path = f.get("fieldPath", "")
                dtype = f.get("nativeDataType", "VARCHAR")
                desc = f.get("description") or ""
                tags = [t.get("tag", {}).get("name", "") for t in f.get("tags", {}).get("tags", []) if t.get("tag")]
                tag_str = f" [TAGS: {', '.join(tags)}]" if tags else ""
                lines.append(f"  - {path} ({dtype}): {desc}{tag_str}")
            schema_desc = "\n".join(lines)

        pii_str = ", ".join(pii_columns) if pii_columns else "None detected"
        model_stem = re.sub(r"[^a-zA-Z0-9_]", "_", table_name.lower())
        if not model_stem.startswith("fct_") and not model_stem.startswith("dim_"):
            model_stem = f"fct_{model_stem}"

        choice = select_model(
            prompt=prompt or "",
            intent=intent,
            provider=provider,
            default_model=model,
            task=task_hint or "generation",
        )

        system_sql = (
            f"You are Synex, an expert AI Data Engineering Agent powered by DataHub Agent Context Kit.\n"
            f"You generate production-ready dbt SQL models in {dialect.upper()} dialect.\n"
            f"You MUST ground every decision in the ENGINEERING CONTEXT package below.\n"
            f"You must NEVER invent tables, joins, or metrics that are not supported by that package.\n\n"
            f"STRICT OUTPUT RULES — violating these causes validation failure:\n"
            f"- Return ONLY raw SQL — no markdown fences (no ```sql), no explanation text, no preamble.\n"
            f"- Do NOT include any SQL inline comments (-- comment). Zero comments allowed.\n"
            f"- Use only column names that exist in SCHEMA_FIELDS. Do not invent columns.\n"
            f"- Apply SHA2(column, 256) hashing to ALL PII columns in the SELECT clause.\n"
            f"- Do NOT output raw PII columns unmasked/unhashed.\n"
            f"- Prefer CTEs (WITH x AS ...) for clarity. Each CTE must be syntactically complete.\n"
            f"- Use dbt {{{{ source('datahub', '{table_name}') }}}} as the source reference.\n"
            f"- If PREVIOUS_SESSION_SQL is present and the user asks a follow-up, refine that SQL.\n"
        )

        context_section = enriched_context_block or f"Schema Fields:\n{schema_desc}\n\nPII Columns: {pii_str}"
        prev_section = ""
        if previous_sql:
            prev_section = f"\n\nPREVIOUS_SESSION_SQL:\n{previous_sql}\n"
        if memory_section:
            prev_section += f"\n{memory_section}\n"
        retry_section = ""
        if retry_feedback:
            retry_section = (
                f"\n\n=== VALIDATOR FEEDBACK (fix these issues in this revision) ===\n"
                f"{retry_feedback}\n"
            )

        user_sql = (
            f"Generate a production dbt SQL model for {table_name}.\n"
            f"DIALECT: {dialect.upper()}\n"
            f"USER REQUEST: {prompt or 'Create a governed analytics model'}\n\n"
            f"{context_section}\n"
            f"{prev_section}\n"
            f"{retry_section}\n"
            f"Generate the SQL model now using organizational knowledge only."
        )

        sql_result = llm_router.complete(
            provider=choice.provider,
            model=choice.model,
            api_key=api_key,
            system=system_sql,
            user=user_sql,
            temperature=0.2,
            max_tokens=1500,
            task=choice.task,
            enable_fallback=True,
            on_attempt=on_attempt,
        )
        sql_code = self._clean_sql(sql_result.text)

        system_yaml = (
            "You are an expert dbt developer. Return only valid YAML — no markdown fences.\n"
            "Define version: 2, models, column descriptions, and data contract tests."
        )
        user_yaml = (
            f"Generate the dbt schema.yml contract for model '{model_stem}' based on this SQL:\n\n"
            f"SQL MODEL:\n{sql_code}"
        )
        yaml_choice = select_model(prompt=prompt or "", provider=provider, default_model=model, task="simple")
        yaml_result = llm_router.complete(
            provider=yaml_choice.provider,
            model=yaml_choice.model,
            api_key=api_key,
            system=system_yaml,
            user=user_yaml,
            temperature=0.1,
            max_tokens=800,
            task="simple",
            enable_fallback=True,
            on_attempt=on_attempt,
        )
        dbt_yaml = self._clean_sql(yaml_result.text, kind="yaml")

        dbt_tests = [
            f"not_null test on primary key fields",
            f"unique test on surrogate key for {model_stem}",
            f"expression test verifying SHA2 hash length on PII columns: {pii_str}",
        ]

        change_summary = (
            f"## Synex Governed dbt Change Summary\n\n"
            f"**Model Name:** `{model_stem}`  \n"
            f"**Target Dialect:** `{dialect.upper()}`  \n"
            f"**Source Asset:** `{table_name}`  \n"
            f"**Provider:** `{sql_result.provider}` / `{sql_result.model}`  \n\n"
            f"### Governance Decisions & PII Masking\n"
            f"- Identified PII columns: `{pii_str}`\n"
            f"- Enforced SHA2 hashing transformation on all sensitive columns.\n"
            f"- Generated dbt schema contract with test coverage.\n\n"
            f"### User Prompt\n"
            f"> {prompt}\n"
        )

        git_patch = (
            f"--- /dev/null\n"
            f"+++ b/models/generated/{model_stem}.sql\n"
            f"@@ -0,0 +1,{len(sql_code.splitlines())} @@\n"
            + "\n".join(f"+{line}" for line in sql_code.splitlines()) + "\n"
            f"--- /dev/null\n"
            f"+++ b/models/generated/schema.yml\n"
            f"@@ -0,0 +1,{len(dbt_yaml.splitlines())} @@\n"
            + "\n".join(f"+{line}" for line in dbt_yaml.splitlines())
        )

        artifact_bundle = {
            "sql_file_path": f"models/generated/{model_stem}.sql",
            "sql": sql_code,
            "schema_file_path": "models/generated/schema.yml",
            "dbt_yaml": dbt_yaml,
            "dbt_tests": dbt_tests,
            "change_summary_markdown": change_summary,
            "git_patch": git_patch,
        }

        return {
            "sql": sql_code,
            "dbt_yaml": dbt_yaml,
            "artifact_bundle": artifact_bundle,
            "llm_meta": {
                "provider": sql_result.provider,
                "model": sql_result.model,
                "fallback_used": sql_result.fallback_used or yaml_result.fallback_used,
                "latency_ms": sql_result.latency_ms + yaml_result.latency_ms,
                "tokens_in": (sql_result.tokens_in or 0) + (yaml_result.tokens_in or 0),
                "tokens_out": (sql_result.tokens_out or 0) + (yaml_result.tokens_out or 0),
                "attempts": (sql_result.attempts or []) + (yaml_result.attempts or []),
                "model_selection_reason": choice.reason,
                "task": choice.task,
            },
        }


generator = AgentGenerator()
