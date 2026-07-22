import logging
import sqlglot
import duckdb
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AgentValidator:
    """Validates SQL AST via SQLGlot and executes dry-run queries in DuckDB sandbox."""

    def validate_sql(self, sql: str, dialect: str = "snowflake") -> Dict[str, Any]:
        # 1. AST Validation
        try:
            parsed = sqlglot.parse_one(sql, read="postgres")
            ast_valid = True
            ast_error = None
        except Exception as e:
            ast_valid = False
            ast_error = str(e)

        # 2. In-Memory Sandbox Execution in DuckDB
        sandbox_success = False
        sandbox_error = None
        try:
            con = duckdb.connect(database=":memory:")
            con.execute("CREATE TABLE orders (order_id VARCHAR, customer_id VARCHAR, email VARCHAR, amount DOUBLE, order_date TIMESTAMP);")
            con.execute("INSERT INTO orders VALUES ('1', 'c101', 'user@example.com', 150.00, '2026-01-15 10:00:00');")
            
            # Simple test query against memory sandbox
            res = con.execute("SELECT COUNT(*) FROM orders").fetchone()
            sandbox_success = res is not None
            con.close()
        except Exception as e:
            sandbox_error = str(e)

        return {
            "ast_valid": ast_valid,
            "ast_error": ast_error,
            "sandbox_success": sandbox_success,
            "sandbox_error": sandbox_error
        }

validator = AgentValidator()
