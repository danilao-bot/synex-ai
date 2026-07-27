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
        llm_api_key: str | None = None,
        llm_model: str | None = None,
        llm_provider: str | None = None,
    ) -> Dict[str, Any]:
        """Generate SQL, dbt schema contract, and complete PR-ready artifact bundle."""
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

        system_sql = (
            f"You are Synex, an expert AI Data Engineering Agent.\n"
            f"You generate production-ready dbt SQL models in {dialect.upper()} dialect "
            f"based on real DataHub metadata.\n\n"
            f"Rules:\n"
            f"- Apply SHA2(column, 256) hashing to ALL PII columns in the SELECT clause.\n"
            f"- Do NOT output raw PII columns unmasked/unhashed.\n"
            f"- Select ONLY columns defined in the schema fields.\n"
            f"- Use dbt {{{{ ref('{table_name}') }}}} or {{{{ source('datahub', '{table_name}') }}}} syntax.\n"
            f"- Add inline SQL comments explaining PII masking decisions.\n"
            f"- Return ONLY raw SQL — no markdown fences, no explanation text."
        )

        user_sql = (
            f"Generate a production dbt SQL model for {table_name}.\n"
            f"DIALECT: {dialect.upper()}\n"
            f"USER REQUEST: {prompt or 'Create a governed analytics model'}\n\n"
            f"Schema Fields:\n{schema_desc}\n\n"
            f"PII Columns to transform/mask: {pii_str}\n\n"
            f"Generate the SQL model now."
        )

        sql_code = self._llm_call(provider, api_key, model, system_sql, user_sql, 0.2, 1500)
        # Strip markdown fences if LLM accidentally included them
        sql_code = re.sub(r"^```sql\s*", "", sql_code, flags=re.IGNORECASE)
        sql_code = re.sub(r"^```\s*", "", sql_code).strip()

        # Second call: generate dbt schema.yml
        system_yaml = (
            "You are an expert dbt developer. Return only valid YAML — no markdown fences.\n"
            "Define version: 2, models, column descriptions, and data contract tests."
        )
        user_yaml = (
            f"Generate the dbt schema.yml contract for model '{model_stem}' based on this SQL:\n\n"
            f"SQL MODEL:\n{sql_code}"
        )
        dbt_yaml = self._llm_call(provider, api_key, model, system_yaml, user_yaml, 0.1, 800)
        dbt_yaml = re.sub(r"^```yaml\s*", "", dbt_yaml, flags=re.IGNORECASE)
        dbt_yaml = re.sub(r"^```\s*", "", dbt_yaml).strip()

        # Build dbt tests list
        dbt_tests = [
            f"not_null test on primary key fields",
            f"unique test on surrogate key for {model_stem}",
            f"expression test verifying SHA2 hash length on PII columns: {pii_str}",
        ]

        # Build Change Summary Markdown
        change_summary = (
            f"## Synex Governed dbt Change Summary\n\n"
            f"**Model Name:** `{model_stem}`  \n"
            f"**Target Dialect:** `{dialect.upper()}`  \n"
            f"**Source Asset:** `{table_name}`  \n\n"
            f"### Governance Decisions & PII Masking\n"
            f"- Identified PII columns: `{pii_str}`\n"
            f"- Enforced SHA2 hashing transformation on all sensitive columns.\n"
            f"- Generated dbt schema contract with test coverage.\n\n"
            f"### User Prompt\n"
            f"> {prompt}\n"
        )

        # Build Git Patch (Unified Diff)
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
        }


generator = AgentGenerator()
