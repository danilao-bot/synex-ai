"""Intelligent catalog search inspired by DataHub Search Skill."""

from __future__ import annotations

from app.services.datahub import datahub_service
from app.workflow.base import BaseStage
from app.workflow.models import WorkflowState, WorkflowStep


class SearchWorkflow(BaseStage):
    id = "search"
    label = "Finding datasets"

    async def execute(self, state: WorkflowState, step: WorkflowStep) -> WorkflowState:
        intent = state.intent
        # Multi-signal query: domain + synonyms + target hint
        parts = []
        if intent:
            if intent.business_domain:
                parts.append(intent.business_domain)
            if intent.target_dataset_hint:
                parts.append(intent.target_dataset_hint)
            parts.extend(intent.synonyms[:5])
        
        if not parts:
            parts.append(state.prompt)

        query = " ".join(dict.fromkeys(p for p in parts if p))  # dedupe preserve order

        step.logs.append(f"Search query composed: {query[:200]}")
        step.logs.append(
            "Search signals: descriptions, glossary, ownership, usage, domains, "
            "quality, documentation, tags, platform, business terminology, synonyms"
        )

        raw, source = await datahub_service.search(query, limit=8)
        if not raw and intent and intent.target_dataset_hint:
            step.logs.append("Primary search empty — retrying with target hint only.")
            raw, source = await datahub_service.search(intent.target_dataset_hint, limit=8)
        if not raw:
            raise RuntimeError(f"DataHub returned no dataset candidates for prompt '{state.prompt}'.")

        state.raw_candidates = raw
        state.search_source = source

        # Attach rank explanation placeholders (filled by Trust stage)
        for i, c in enumerate(raw):
            c["_search_rank"] = i + 1
            c["_search_query"] = query
            c["_search_signals"] = [
                "name_match",
                "description",
                "glossary",
                "domain",
                "tags",
                "ownership",
                "platform",
            ]

        step.complete(
            message=f"Found {len(raw)} candidate(s) via {source}.",
            outputs={
                "provider": source,
                "candidate_count": len(raw),
                "candidates": [
                    {"urn": c.get("urn"), "name": c.get("name"), "search_rank": c.get("_search_rank")}
                    for c in raw
                ],
                "query": query,
            },
            reasoning_summary=f"Catalog search via {source} using multi-signal query.",
        )
        return state
