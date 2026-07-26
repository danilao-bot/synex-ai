"""Multi-provider LLM-powered SQL and dbt contract synthesis.

Supports:
  - openrouter  → OpenAI SDK pointed at https://openrouter.ai/api/v1
  - openai      → OpenAI SDK pointed at https://api.openai.com/v1
  - anthropic   → Anthropic SDK (claude-* models)
  - Any other   → Treated as OpenRouter-compatible (OpenAI SDK with env base_url)
"""
import logging
from typing import Dict, Any, List

from app.core.config import settings

logger = logging.getLogger(__name__)

# Provider → base_url for OpenAI-compatible endpoints
_OPENAI_COMPAT_BASE_URLS: dict[str, str] = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai":     "https://api.openai.com/v1",
    "together":   "https://api.together.xyz/v1",
    "groq":       "https://api.groq.com/openai/v1",
    "mistral":    "https://api.mistral.ai/v1",
    "deepseek":   "https://api.deepseek.com/v1",
}


class AgentGenerator:
    """Synthesizes dialect-correct SQL and dbt schema contract YAML using a real LLM."""

    def _resolve_base_url(self, provider: str) -> str:
        """Return the correct API base URL for the given provider slug."""
        p = (provider or "openrouter").lower().strip()
        # Use env override if set, then provider map, then default to OpenRouter
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
        """Call any OpenAI-compatible endpoint and return the response text."""
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
        """Call Anthropic Claude API using the Anthropic SDK."""
        try:
            import anthropic
        except ImportError:
            raise RuntimeError(
                "anthropic package is not installed. Add 'anthropic>=0.25.0' to requirements.txt."
            )
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
        """Route to the correct provider SDK and return raw text."""
        p = (provider or "openrouter").lower().strip()
        logger.info("LLM call: provider=%s model=%s", p, model)

        if p == "anthropic":
            return self._call_anthropic(api_key, model, system, user, max_tokens)

        # All other providers use OpenAI-compatible SDK
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
    ) -> Dict[str, str]:
        """
        Generate SQL and dbt YAML using a real LLM call grounded in DataHub metadata.
        Provider routing: openrouter | openai | anthropic | groq | mistral | deepseek | together
        """
        api_key = llm_api_key or settings.LLM_API_KEY
        model = llm_model or settings.LLM_MODEL
        provider = llm_provider or "openrouter"

        if not api_key:
            raise RuntimeError(
                "No LLM API key configured. "
                "Add LLM_API_KEY to Render environment variables or save it via Settings."
            )

        # Build structured schema description from real DataHub fields
        schema_desc = ""
        if schema_fields:
            lines = []
            for f in schema_fields:
                path = f.get("fieldPath", "")
                dtype = f.get("nativeDataType", "UNKNOWN")
                desc = f.get("description") or ""
                tags = [t.get("tag", {}).get("name", "") for t in f.get("tags", {}).get("tags", [])]
                tag_str = f" [TAGS: {', '.join(tags)}]" if tags else ""
                lines.append(f"  - {path} ({dtype}): {desc}{tag_str}")
            schema_desc = "\n".join(lines)

        pii_str = ", ".join(pii_columns) if pii_columns else "None detected"

        system_sql = (
            f"You are Synex, an expert AI Data Engineering Agent.\n"
            f"You generate production-ready dbt SQL models in {dialect.upper()} dialect "
            f"based on real DataHub metadata.\n\n"
            f"Rules:\n"
            f"- Apply SHA2 hashing to ALL PII columns in the SELECT clause.\n"
            f"- Use dbt {{{{ ref('...') }}}} syntax for source tables.\n"
            f"- Add inline comments explaining governance decisions.\n"
            f"- Return ONLY raw SQL — no markdown, no code fences, no explanation."
        )

        if previous_sql:
            user_sql = (
                f"The user wants to modify an existing SQL model.\n\n"
                f"PREVIOUS MODEL (from this session):\n{previous_sql}\n\n"
                f"DATAHUB METADATA FOR: {table_name}\n"
                f"Schema Fields:\n{schema_desc}\n\n"
                f"PII Columns to mask: {pii_str}\n\n"
                f"USER REQUEST: {prompt}\n\n"
                f"Modify the previous model. Keep all governance rules intact."
            )
        else:
            user_sql = (
                f"Generate a production dbt SQL model for the following DataHub dataset.\n\n"
                f"DATASET: {table_name}\nDIALECT: {dialect.upper()}\n\n"
                f"Schema Fields:\n{schema_desc}\n\n"
                f"PII Columns to mask: {pii_str}\n\n"
                f"USER REQUEST: {prompt or f'Build a complete analytics model for {table_name}'}\n\n"
                f"Generate the full SQL model now."
            )

        sql_code = self._llm_call(provider, api_key, model, system_sql, user_sql, 0.2, 1500)

        # Second call: generate dbt schema.yml grounded in the real SQL
        system_yaml = "You are an expert dbt developer. Return only valid YAML — no markdown fences."
        user_yaml = (
            f"Based on this SQL model for {table_name}, generate the dbt schema.yml contract.\n"
            f"Include column descriptions and not_null tests for all SELECT columns.\n\n"
            f"SQL MODEL:\n{sql_code}"
        )
        dbt_yaml = self._llm_call(provider, api_key, model, system_yaml, user_yaml, 0.1, 800)

        return {"sql": sql_code, "dbt_yaml": dbt_yaml}


generator = AgentGenerator()
