"""Enrichment workflow inspired by DataHub Enrichment Skill."""

from __future__ import annotations

from app.services.datahub import datahub_service
from app.workflow.base import BaseStage
from app.workflow.models import WorkflowState, WorkflowStep


class EnrichmentWorkflow(BaseStage):
    id = "enrichment"
    label = "Enriching metadata context"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        selected = state.selected_candidate or {}
        urn = selected.get("urn")
        if not urn:
            raise RuntimeError("No selected dataset URN for enrichment.")

        enriched = await datahub_service.enrich_dataset(
            urn,
            prompt=state.prompt,
            previous_sql=state.previous_sql,
            previous_validation_summary=state.previous_validation_summary,
        )
        # Prefer enriched PII
        if enriched.pii_fields:
            selected["pii_fields"] = enriched.pii_fields
            state.selected_candidate = selected

        # Metadata proposals (not applied)
        missing = []
        if not enriched.description:
            missing.append("description")
        if not enriched.owners:
            missing.append("owners")
        if not enriched.domain:
            missing.append("domain")
        if not enriched.glossary_terms:
            missing.append("glossary_terms")
        if not enriched.tags:
            missing.append("tags")

        suggested_tags = ["synex_generated"]
        if enriched.pii_fields:
            suggested_tags.append("synex_pii_masked")
        if state.intent and state.intent.business_domain:
            suggested_tags.append(f"domain_{state.intent.business_domain}")

        proposals = []
        if "description" in missing:
            proposals.append({
                "op": "update_description",
                "preview": "Propose dataset description from Synex engineering context",
                "status": "proposed_only",
            })
        for t in suggested_tags:
            proposals.append({
                "op": "add_tags",
                "preview": f"Propose tag {t}",
                "params": {"tag_urns": [f"urn:li:tag:{t}"]},
                "status": "proposed_only",
            })

        state.enriched_ctx = enriched
        state.enrichment = {
            "description": enriched.description,
            "glossary": enriched.glossary_terms,
            "owners": enriched.owners,
            "domains": [enriched.domain] if enriched.domain else [],
            "business_definitions": enriched.glossary_terms,
            "institutional_memory": enriched.institutional_memory,
            "custom_properties": {},
            "documentation": enriched.documents,
            "knowledge_documents": enriched.documents,
            "suggested_tags": suggested_tags,
            "missing_metadata": missing,
            "metadata_proposals": proposals,
            "platform": enriched.platform,
            "assertions": enriched.assertions,
            "sample_queries": enriched.sample_queries,
            "metadata_source": enriched.metadata_source,
        }

        step.logs.append(f"Loaded schema fields: {len(enriched.schema_fields)}")
        step.logs.append(f"Glossary terms: {len(enriched.glossary_terms)}")
        step.logs.append(f"Documents: {len(enriched.documents)}")
        step.logs.append(f"Sample SQL snippets: {len(enriched.sample_queries)}")
        step.logs.append(f"Owners: {', '.join(enriched.owners) or 'none'}")

        step.complete(
            message=f"Enriched '{enriched.name}' via {enriched.metadata_source}.",
            outputs={
                "urn": enriched.urn,
                "missing_metadata": missing,
                "proposal_count": len(proposals),
                "schema_field_count": len(enriched.schema_fields),
                "sample_query_count": len(enriched.sample_queries),
            },
            reasoning_summary="Collected descriptions, glossary, owners, docs, queries; proposals deferred.",
            warnings=[f"Missing metadata: {', '.join(missing)}"] if missing else None,
        )
        return state
