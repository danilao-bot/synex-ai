import logging
import re
import sqlglot
import duckdb
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AgentValidator:
    """Validates SQL AST via SQLGlot and executes dry-run queries in DuckDB sandbox."""

    def validate_sql(self, sql: str, dialect: str = "snowflake") -> Dict[str, Any]:
        # 1. AST Validation
        try:
            parsed = sqlglot.parse_one(sql, read=dialect)
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
            try:
                con.execute("CREATE TABLE source_model (order_id VARCHAR, customer_id VARCHAR, email VARCHAR, amount DOUBLE, order_date TIMESTAMP)")
                con.execute("INSERT INTO source_model VALUES ('1', 'c101', 'user@example.com', 150.00, '2026-01-15 10:00:00')")
                sandbox_sql = re.sub(r"\{\{\s*ref\(['\"][^'\"]+['\"]\)\s*\}\}", "source_model", sql)
                sandbox_sql = sqlglot.transpile(sandbox_sql, read=dialect, write="duckdb")[0]
                con.execute(sandbox_sql).fetchall()
                sandbox_success = True
            finally:
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
