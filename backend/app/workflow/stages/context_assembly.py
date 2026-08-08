"""Assemble engineering context via the Phase-3 Context Engine (sole LLM truth source)."""

from __future__ import annotations

from app.context.engine import context_engine
from app.workflow.base import BaseStage
from app.workflow.models import EngineeringContext, WorkflowState, WorkflowStep


class ContextAssemblyWorkflow(BaseStage):
    id = "context_assembly"
    label = "Building engineering context"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        selected = state.selected_candidate or {}
        enriched = state.enriched_ctx
        if not enriched:
            raise RuntimeError("Enrichment required before Context Engine assembly.")

        intent = state.intent
        validation_rules = [
            "Only reference columns present in SCHEMA_FIELDS.",
            "Hash or mask all PII_FIELDS (e.g. SHA2).",
            "Prefer certified, non-deprecated sources.",
            "Do not invent tables or columns outside engineering context.",
            "Reuse PRODUCTION SQL PROFILE and SQL PATTERN LIBRARY before inventing joins/filters.",
            "Use BUSINESS VOCABULARY canonical terms for aliases and metrics.",
        ]
        if state.allow_deprecated_override:
            validation_rules.append("Deprecated override enabled by user.")
        if intent and intent.risk_level == "high":
            validation_rules.append("High-risk request: maximize PII protection and governance checks.")

        package = await context_engine.build(
            prompt=state.prompt,
            selected=selected,
            enriched=enriched,
            lineage_report=state.lineage_report,
            quality_report=state.quality_report,
            candidate_evaluations=state.candidate_evaluations,
            engineering_memory=state.engineering_memory
            or {
                "previous_sql": state.previous_sql,
                "previous_validation_summary": state.previous_validation_summary,
            },
            validation_rules=validation_rules,
            global_warnings=state.global_warnings,
        )
        state.context_package = package
        state.context_manifest = package.manifest.to_dict() if package.manifest else {}
        state.global_warnings = list(package.warnings)

        business = ""
        if intent:
            business = (
                f"User intent: {intent.intent}. Domain: {intent.business_domain or 'n/a'}. "
                f"Desired artifact: {intent.desired_artifact}. Risk: {intent.risk_level}."
            )
        if enriched.description:
            business += f" Dataset description: {enriched.description[:500]}"

        eng = EngineeringContext(
            business_context=business,
            schema_fields=package.schema_fields,
            lineage={
                "upstream_names": (state.lineage_report or {}).get("upstream_names") or [],
                "downstream_names": (state.lineage_report or {}).get("downstream_names") or [],
                "safer_choice_reason": (state.lineage_report or {}).get("safer_choice_reason"),
                "column_lineage": (state.lineage_report or {}).get("column_lineage") or [],
                "potential_downstream_risks": (state.lineage_report or {}).get("potential_downstream_risks") or [],
            },
            quality=state.quality_report or {},
            ownership=package.ownership.get("all_owners") or enriched.owners,
            glossary=enriched.glossary_terms,
            documentation=package.documents,
            sample_sql=(package.sql_profile.sample_queries if package.sql_profile else []),
            usage=[f"Downstream dependents: {(state.lineage_report or {}).get('downstream_impact_count', 0)}"],
            validation_rules=validation_rules,
            governance={
                "pii_fields": package.pii_fields,
                "deprecated": selected.get("is_deprecated", False),
                "certified": selected.get("is_certified", False),
                "risk_level": intent.risk_level if intent else "medium",
            },
            recommended_joins=package.recommended_joins,
            pii_fields=package.pii_fields,
            warnings=list(package.warnings),
            trust_scores=package.trust_breakdown,
            reasoning_summary=package.reasoning_summary,
            selected_urn=package.selected_urn,
            selected_name=package.selected_name,
            platform=enriched.platform,
            domain=package.domain,
            tags=enriched.tags,
            institutional_memory=package.institutional_memory,
            assertions=enriched.assertions,
            previous_sql=state.previous_sql,
            metadata_source=package.metadata_source,
            context_manifest=state.context_manifest,
            sql_profile=package.sql_profile.to_dict() if package.sql_profile else {},
            vocabulary=[v.to_dict() for v in package.vocabulary],
            pattern_library_hints=package.pattern_library_hints,
            context_sources=package.context_sources,
            prompt_version=package.prompt_version,
            compressed_block=package.compressed_prompt_block,
        )
        state.engineering_context = eng

        checklist = (package.manifest.to_checklist() if package.manifest else [])
        for line in checklist:
            step.logs.append(f"✓ {line}")

        step.complete(
            message="Engineering Context Engine package ready — sole LLM input.",
            outputs={
                "manifest": state.context_manifest,
                "sql_profile_queries": package.sql_profile.query_count if package.sql_profile else 0,
                "vocabulary_mappings": len(package.vocabulary),
                "ranked_kept": len(package.ranked_items),
                "prompt_version": package.prompt_version,
            },
            reasoning_summary=package.reasoning_summary,
            trust_score=selected.get("trust_score"),
            warnings=package.warnings[:5] or None,
        )
        return state
