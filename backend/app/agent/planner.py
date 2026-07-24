from typing import List, Dict, Any

class AgentPlanner:
    """Decomposes user natural language prompt into structured sub-goals."""
    
    def plan_steps(self, prompt: str) -> List[Dict[str, Any]]:
        return [
            {
                "step": 1,
                "type": "ENTITY_DISCOVERY",
                "description": f"Query DataHub catalog for tables related to '{prompt}'"
            },
            {
                "step": 2,
                "type": "GOVERNANCE_AUDIT",
                "description": "Inspect candidate tables for deprecation banners, PII tags, and ownership."
            },
            {
                "step": 3,
                "type": "LINEAGE_TRAVERSAL",
                "description": "Evaluate 2-hop upstream/downstream lineage to avoid breaking production models."
            },
            {
                "step": 4,
                "type": "CODE_SYNTHESIS",
                "description": "Generate dialect-correct SQL query and dbt schema contract."
            },
            {
                "step": 5,
                "type": "AST_VALIDATION",
                "description": "Validate SQL syntax via SQLGlot and execute dry-run in DuckDB sandbox."
            },
            {
                "step": 6,
                "type": "DATAHUB_WRITEBACK",
                "description": "Emit Metadata Change Proposal (MCP) to document the generated model in DataHub."
            }
        ]

planner = AgentPlanner()
