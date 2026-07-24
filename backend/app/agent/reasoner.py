import re
from typing import Dict, Any, Iterable, List

class AgentReasoner:
    """Reasons over DataHub metadata aspects to select canonical tables and enforce governance."""
    
    def evaluate_governance(self, aspect_data: Dict[str, Any]) -> Dict[str, Any]:
        fields = aspect_data.get("schemaMetadata", {}).get("fields", [])
        pii_columns = []
        
        pii_name_pattern = re.compile(r"(email|e_mail|phone|mobile|ssn|social_security|credit_?card|passport|date_?of_?birth|address)", re.I)
        for field in fields:
            field_path = field.get("fieldPath", "")
            tags = field.get("tags", {}).get("tags", [])
            for t in tags:
                tag_name = t.get("tag", {}).get("name", "").upper()
                if "PII" in tag_name or "SENSITIVE" in tag_name:
                    pii_columns.append(field_path)
            if pii_name_pattern.search(field_path) or pii_name_pattern.search(field.get("description") or ""):
                pii_columns.append(field_path)
                    
        deprecated = aspect_data.get("deprecation", {}).get("deprecated", False)
        
        return {
            "urn": aspect_data.get("urn"),
            "name": aspect_data.get("name"),
            "deprecated": deprecated,
            "pii_columns": list(set(pii_columns)),
            "is_canonical": not deprecated
        }

    def rank_candidates(self, candidates: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prefer non-deprecated, named datasets with a description over weak search matches."""
        def score(candidate: Dict[str, Any]) -> int:
            value = 0
            if candidate.get("name"):
                value += 2
            if candidate.get("properties", {}).get("description"):
                value += 1
            if "deprecated" not in str(candidate).lower():
                value += 1
            return value
        return sorted(candidates, key=score, reverse=True)

reasoner = AgentReasoner()
