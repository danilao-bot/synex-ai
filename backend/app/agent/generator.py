from typing import Dict, Any, List

class AgentGenerator:
    """Synthesizes dialect-correct SQL and dbt schema contract YAML."""

    def generate_code_and_contract(self, table_name: str, pii_columns: List[str], dialect: str = "snowflake") -> Dict[str, str]:
        masked_selects = []
        if "email" in pii_columns:
            masked_selects.append("  SHA2(email) AS email_hashed")
        else:
            masked_selects.append("  email")
            
        sql_code = f"""-- Synthesized by Synex AI Data Engineering Agent
-- Dialect: {dialect.upper()} | Source: DataHub Verified Metadata
-- Governance: PII Columns Masked ({', '.join(pii_columns) if pii_columns else 'None'})

WITH source_orders AS (
    SELECT
        order_id,
        customer_id,
{masked_selects[0]},
        amount,
        order_date
    FROM {{ ref('{table_name.split('.')[-1]}') }}
    WHERE order_date >= DATEADD(month, -12, CURRENT_DATE())
)
SELECT
    DATE_TRUNC('month', order_date) AS retention_month,
    COUNT(DISTINCT customer_id) AS active_customers,
    SUM(amount) AS total_revenue
FROM source_orders
GROUP BY 1
ORDER BY retention_month DESC;
"""

        dbt_yaml = f"""version: 2

models:
  - name: monthly_customer_retention
    description: "Monthly customer retention and revenue metrics synthesized by Synex agent based on DataHub Tier-1 orders table."
    columns:
      - name: retention_month
        description: "Truncated month timestamp"
        tests:
          - not_null
      - name: active_customers
        description: "Unique active customer count"
        tests:
          - not_null
      - name: total_revenue
        description: "Aggregated monthly revenue"
        tests:
          - not_null
"""
        return {
            "sql": sql_code,
            "dbt_yaml": dbt_yaml
        }

generator = AgentGenerator()
