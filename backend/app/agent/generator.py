"""Real LLM-powered SQL and dbt contract synthesis via OpenRouter."""
import logging
from typing import Dict, Any, List

from app.core.config import settings

logger = logging.getLogger(__name__)


class AgentGenerator:
    """Synthesizes dialect-correct SQL and dbt schema contract YAML using a real LLM."""

    def _get_openai_client(self, api_key: str):
        """Return an OpenAI-compatible client pointed at OpenRouter."""
        from openai import OpenAI
        return OpenAI(
            api_key=api_key,
            base_url=settings.OPENROUTER_BASE_URL,
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
    ) -> Dict[str, str]:
        """
        Call OpenRouter (GPT-4o) with real DataHub metadata context to synthesise SQL.
        Falls back to a transparent error if no API key is configured.
        """
        api_key = llm_api_key or settings.LLM_API_KEY
        model = llm_model or settings.LLM_MODEL

        if not api_key:
            raise RuntimeError(
                "No LLM API key is configured. "
                "Add LLM_API_KEY to your environment variables or save it via Settings."
            )

        # Build a structured schema description from real DataHub fields
        schema_desc = ""
        if schema_fields:
            field_lines = []
            for f in schema_fields:
                path = f.get("fieldPath", "")
                dtype = f.get("nativeDataType", "UNKNOWN")
                desc = f.get("description") or ""
                tags = [t.get("tag", {}).get("name", "") for t in f.get("tags", {}).get("tags", [])]
                tag_str = f" [TAGS: {', '.join(tags)}]" if tags else ""
                field_lines.append(f"  - {path} ({dtype}): {desc}{tag_str}")
            schema_desc = "\n".join(field_lines)

        pii_str = ", ".join(pii_columns) if pii_columns else "None detected"

        # Compose the system prompt
        system_prompt = f"""You are Synex, an expert AI Data Engineering Agent.
You generate production-ready dbt SQL models in {dialect.upper()} dialect based on real DataHub metadata.

Rules:
- Apply SHA2 hashing to ALL PII columns in the SELECT clause.
- Use dbt {{ ref('...') }} syntax for source tables.
- Add inline comments explaining governance decisions.
- Return ONLY raw SQL — no markdown, no code fences, no explanation."""

        # Compose the user prompt with full DataHub context
        if previous_sql:
            user_prompt = f"""The user wants to modify an existing SQL model.

PREVIOUS MODEL (from this session):
{previous_sql}

DATAHUB METADATA FOR: {table_name}
Schema Fields:
{schema_desc}

PII Columns to mask: {pii_str}

USER REQUEST: {prompt}

Modify the previous model based on the user's request. Keep all existing governance rules intact."""
        else:
            user_prompt = f"""Generate a production dbt SQL model for the following DataHub dataset.

DATASET: {table_name}
DIALECT: {dialect.upper()}

Schema Fields:
{schema_desc}

PII Columns to mask: {pii_str}

USER REQUEST: {prompt or f'Build a complete analytics model for {table_name}'}

Generate the full SQL model now."""

        client = self._get_openai_client(api_key)

        logger.info("Calling OpenRouter model=%s for table=%s", model, table_name)
        chat_response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1500,
        )
        sql_code = chat_response.choices[0].message.content.strip()

        # Second LLM call to generate the dbt schema YAML grounded in real fields
        yaml_prompt = f"""Based on this SQL model for {table_name}, generate the dbt schema.yml contract YAML.
Include column descriptions and not_null tests for all SELECT columns.
Return ONLY valid YAML — no markdown fences, no explanation.

SQL MODEL:
{sql_code}"""

        yaml_response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert dbt developer. Return only valid YAML."},
                {"role": "user", "content": yaml_prompt},
            ],
            temperature=0.1,
            max_tokens=800,
        )
        dbt_yaml = yaml_response.choices[0].message.content.strip()

        return {
            "sql": sql_code,
            "dbt_yaml": dbt_yaml,
        }


generator = AgentGenerator()
