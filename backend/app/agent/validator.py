import logging
import re
import sqlglot
import duckdb
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# Map DataHub / Snowflake native types to DuckDB-compatible types
_TYPE_MAP = {
    "VARCHAR": "VARCHAR", "STRING": "VARCHAR", "TEXT": "VARCHAR", "CHAR": "VARCHAR",
    "NUMBER": "DOUBLE", "NUMERIC": "DOUBLE", "DECIMAL": "DOUBLE",
    "INT": "INTEGER", "INTEGER": "INTEGER", "INT64": "BIGINT",
    "BIGINT": "BIGINT", "SMALLINT": "INTEGER", "TINYINT": "INTEGER",
    "FLOAT": "DOUBLE", "FLOAT64": "DOUBLE", "DOUBLE": "DOUBLE", "REAL": "DOUBLE",
    "BOOLEAN": "BOOLEAN", "BOOL": "BOOLEAN",
    "TIMESTAMP": "TIMESTAMP", "TIMESTAMP_TZ": "TIMESTAMP", "TIMESTAMP_NTZ": "TIMESTAMP",
    "DATE": "DATE", "TIME": "TIME",
    "ARRAY": "VARCHAR", "OBJECT": "VARCHAR", "VARIANT": "VARCHAR",
    "STRUCT": "VARCHAR", "MAP": "VARCHAR", "JSON": "VARCHAR",
    "BYTES": "BLOB", "BINARY": "BLOB",
}

_FALLBACK_SCHEMA = (
    "CREATE TABLE source_model ("
    "id VARCHAR, created_at TIMESTAMP, updated_at TIMESTAMP, status VARCHAR"
    ")"
)


def _build_create_table(schema_fields: List[Dict[str, Any]]) -> str:
    """Build a DuckDB CREATE TABLE statement from real DataHub schema fields."""
    if not schema_fields:
        return _FALLBACK_SCHEMA

    columns = []
    seen = set()
    for field in schema_fields:
        col = re.sub(r"[^a-zA-Z0-9_]", "_", field.get("fieldPath", "col"))
        if not col or col in seen:
            continue
        seen.add(col)
        raw_type = field.get("nativeDataType", "VARCHAR").upper().split("(")[0].strip()
        duckdb_type = _TYPE_MAP.get(raw_type, "VARCHAR")
        columns.append(f"{col} {duckdb_type}")

    if not columns:
        return _FALLBACK_SCHEMA

    return f"CREATE TABLE source_model ({', '.join(columns)})"


class AgentValidator:
    """Validates SQL AST via SQLGlot and executes dry-run queries in DuckDB sandbox."""

    def validate_sql(
        self,
        sql: str,
        dialect: str = "snowflake",
        schema_fields: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        # 1. AST Validation via SQLGlot
        try:
            sqlglot.parse_one(sql, read=dialect)
            ast_valid = True
            ast_error = None
        except Exception as e:
            ast_valid = False
            ast_error = str(e)

        # 2. In-Memory Sandbox Execution in DuckDB
        # Build schema dynamically from real DataHub fields if available
        create_stmt = _build_create_table(schema_fields or [])
        sandbox_success = False
        sandbox_error = None
        try:
            con = duckdb.connect(database=":memory:")
            try:
                con.execute(create_stmt)
                # Insert one dummy row to allow SELECT queries to run
                col_count = create_stmt.count(",") + 1
                dummy_values = ", ".join(["NULL"] * col_count)
                try:
                    con.execute(f"INSERT INTO source_model VALUES ({dummy_values})")
                except Exception:
                    pass  # Insert may fail for complex types — SELECT dry-run still works
                sandbox_sql = re.sub(
                    r"\{\{\s*ref\(['\"][^'\"]+['\"]\)\s*\}\}", "source_model", sql
                )
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
            "sandbox_error": sandbox_error,
            "schema_used": create_stmt,
        }


validator = AgentValidator()
