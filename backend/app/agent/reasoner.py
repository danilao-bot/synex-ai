"""Agent Reasoner module exporting context_reasoner and backward-compatible AgentReasoner."""

from typing import Dict, Any, List, Iterable
from app.agent.context_reasoner import context_reasoner, ContextReasoner


class AgentReasoner:
    """Backward compatible wrapper around ContextReasoner."""

    def evaluate_governance(self, aspect_data: Dict[str, Any]) -> Dict[str, Any]:
        evaluated = context_reasoner.evaluate_candidate(aspect_data, "")
        return {
            "urn": aspect_data.get("urn"),
            "name": aspect_data.get("name"),
            "deprecated": evaluated["is_deprecated"],
            "pii_columns": evaluated["pii_fields"],
            "is_canonical": not evaluated["is_deprecated"],
            "evaluation": evaluated,
        }

    def rank_candidates(self, candidates: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cand_list = list(candidates)
        _, ranked = context_reasoner.rank_candidates(cand_list, "")
        # Map back URNs to original dicts
        urn_to_cand = {c.get("urn"): c for c in cand_list if c.get("urn")}
        result = []
        for r in ranked:
            if r.get("urn") in urn_to_cand:
                result.append(urn_to_cand[r["urn"]])
            else:
                result.append(r)
        return result


reasoner = AgentReasoner()
