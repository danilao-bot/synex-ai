from typing import Dict, Any, List

class AgentReasoner:
    """Reasons over DataHub metadata aspects to select canonical tables and enforce governance."""
    
    def evaluate_governance(self, aspect_data: Dict[str, Any]) -> Dict[str, Any]:
        fields = aspect_data.get("schemaMetadata", {}).get("fields", [])
        pii_columns = []
        
        for field in fields:
            tags = field.get("tags", {}).get("tags", [])
            for t in tags:
                tag_name = t.get("tag", {}).get("name", "").upper()
                if "PII" in tag_name or "SENSITIVE" in tag_name or field.get("fieldPath") in ["email", "ssn", "credit_card"]:
                    pii_columns.append(field.get("fieldPath"))
                    
        deprecated = aspect_data.get("deprecation", {}).get("deprecated", False)
        
        return {
            "urn": aspect_data.get("urn"),
            "name": aspect_data.get("name"),
            "deprecated": deprecated,
            "pii_columns": list(set(pii_columns)),
            "is_canonical": not deprecated
        }

reasoner = AgentReasoner()
