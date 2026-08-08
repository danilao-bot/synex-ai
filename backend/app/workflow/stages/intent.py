"""Intent analysis — understand the request before searching DataHub."""

from __future__ import annotations

import re
from typing import Any

from app.workflow.base import BaseStage
from app.workflow.models import IntentResult, RunOutcome, WorkflowState, WorkflowStep

_DOMAIN_HINTS = {
    "finance": ["revenue", "finance", "billing", "invoice", "payment", "ledger", "arr", "mrr"],
    "marketing": ["campaign", "marketing", "attribution", "funnel", "lead"],
    "product": ["product", "feature", "usage", "event", "clickstream"],
    "hr": ["employee", "hr", "payroll", "people"],
    "sales": ["sales", "opportunity", "crm", "deal", "pipeline"],
    "customer": ["customer", "user", "account", "subscriber"],
}

_ARTIFACT_HINTS = {
    "dbt_sql_and_schema_yml": ["dbt", "model", "schema.yml", "sql", "transform"],
    "lineage_report": ["lineage", "impact", "downstream", "upstream", "blast"],
    "quality_audit": ["quality", "assertion", "freshness", "incident"],
    "documentation": ["document", "describe", "glossary", "enrich"],
}

_RISK_HIGH = ["pii", "gdpr", "hipaa", "ssn", "delete", "drop", "production", "prod", "sensitive"]
_AMBIGUOUS_SHORT = 12  # chars


class IntentAnalyzer(BaseStage):
    id = "intent"
    label = "Understanding request"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        prompt = (state.prompt or "").strip()
        lower = prompt.lower()
        words = re.findall(r"[a-zA-Z0-9_]+", lower)

        domain = None
        for d, keys in _DOMAIN_HINTS.items():
            if any(k in lower for k in keys):
                domain = d
                break

        artifact = "dbt_sql_and_schema_yml"
        for art, keys in _ARTIFACT_HINTS.items():
            if any(k in lower for k in keys):
                artifact = art
                break

        risk = "high" if any(k in lower for k in _RISK_HIGH) else "medium"
        if "certified" in lower or "governed" in lower:
            risk = "low" if risk != "high" else "high"

        # Target dataset hint from quoted names or table-like tokens
        target_hint = None
        quoted = re.findall(r"['\"`]([a-zA-Z0-9_.]+)['\"`]", prompt)
        if quoted:
            target_hint = quoted[0]
        else:
            tableish = [w for w in words if ("_" in w or w.startswith(("fct_", "dim_", "stg_", "raw_"))) and len(w) > 3]
            if tableish:
                target_hint = tableish[0]

        synonyms: list[str] = []
        if "revenue" in lower:
            synonyms.extend(["arr", "mrr", "sales", "income"])
        if "customer" in lower:
            synonyms.extend(["user", "account", "client"])
        if "order" in lower:
            synonyms.extend(["transaction", "purchase"])

        required_metadata = ["schema", "ownership", "lineage", "tags"]
        if risk == "high":
            required_metadata.extend(["pii", "glossary", "quality"])
        if domain:
            required_metadata.append("domain")

        confidence = 0.85
        clarifying: list[str] = []
        ambiguous = False

        if len(prompt) < _AMBIGUOUS_SHORT:
            ambiguous = True
            confidence = 0.25
            clarifying.append("What dataset or business metric should Synex model?")
            clarifying.append("Which warehouse dialect (Snowflake, BigQuery, etc.) and domain?")
        elif not domain and not target_hint and artifact == "dbt_sql_and_schema_yml":
            # Vague generation request without domain or table
            generic = {"create", "build", "make", "generate", "model", "a", "the", "for", "me", "please"}
            meaningful = [w for w in words if w not in generic and len(w) > 2]
            if len(meaningful) < 2:
                ambiguous = True
                confidence = 0.4
                clarifying.append("Which business domain or dataset should this model target?")
                clarifying.append("Any required columns, filters, or PII masking rules?")

        if "or" in words and ("dataset" in lower or "table" in lower) and not target_hint:
            ambiguous = True
            confidence = min(confidence, 0.45)
            clarifying.append("Multiple datasets were implied — which canonical source should Synex use?")

        intent_name = "generate_dbt_model"
        if artifact == "lineage_report":
            intent_name = "analyze_lineage"
        elif artifact == "quality_audit":
            intent_name = "audit_quality"
        elif artifact == "documentation":
            intent_name = "enrich_metadata"

        reasoning = (
            f"Intent={intent_name}; domain={domain or 'unspecified'}; "
            f"artifact={artifact}; risk={risk}; target_hint={target_hint or 'none'}."
        )

        intent = IntentResult(
            intent=intent_name,
            target_dataset_hint=target_hint,
            business_domain=domain,
            desired_artifact=artifact,
            risk_level=risk,
            required_metadata=required_metadata,
            confidence=confidence,
            ambiguous=ambiguous,
            clarifying_questions=clarifying,
            keywords=words[:40],
            synonyms=synonyms,
            reasoning=reasoning,
        )
        state.intent = intent

        if ambiguous and clarifying:
            state.outcome = RunOutcome.NEEDS_CLARIFICATION
            state.clarifying_questions = clarifying
            step.complete(
                message="Request is ambiguous — clarifying questions required before generation.",
                outputs=intent.to_dict(),
                warnings=["Ambiguous prompt; SQL generation deferred."],
                reasoning_summary=reasoning,
            )
            return state

        step.complete(
            message=f"Understood intent '{intent_name}' (confidence {confidence:.0%}).",
            outputs=intent.to_dict(),
            reasoning_summary=reasoning,
        )
        step.logs.append(f"Domain={domain}, risk={risk}, synonyms={synonyms}")
        return state
