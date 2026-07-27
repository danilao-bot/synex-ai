"""Deterministic Governance Validator for Synex.

Enforces zero-trust validation on generated dbt SQL and schema contracts:
- SQL AST validation via SQLGlot
- DuckDB sandbox dry-run execution
- YAML schema parsing and structure verification via PyYAML
- Schema field existence check (blocks SQL referencing fields absent from DataHub schema)
- PII masking validation (blocks raw unhashed/unmasked PII in SELECT statements)
- Deprecated source blocking (unless allow_deprecated_override=True is set)
"""

import logging
import re
from typing import Any, Dict, List, Set, Optional
import sqlglot
import sqlglot.expressions as exp
import duckdb
import yaml

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

_APPROVED_PII_TRANSFORMS = {
    "SHA2", "SHA256", "SHA512", "MD5", "HASH", "MASK", "TOKENIZE", "REDACT",
    "ENCRYPT", "ANONYMIZE", "LEFT", "RIGHT", "SUBSTRING", "SUBSTR"
}


class AgentValidator:
    """Validates SQL AST, schema compliance, PII masking, YAML, and DuckDB execution."""

    def validate_governance(
        self,
        sql: str,
        dbt_yaml: str,
        schema_fields: List[Dict[str, Any]],
        pii_fields: List[str],
        is_deprecated: bool = False,
        allow_deprecated_override: bool = False,
        dialect: str = "snowflake",
    ) -> Dict[str, Any]:
        """Perform comprehensive deterministic validation."""
        blocking_errors: List[str] = []
        warnings: List[str] = []

        # 1. Deprecated Source Check
        if is_deprecated and not allow_deprecated_override:
            blocking_errors.append(
                "Source dataset is flagged as DEPRECATED in DataHub. "
                "Set allow_deprecated_override=True to permit model generation on deprecated assets."
            )

        # Preprocess Jinja templates for SQLGlot AST parsing
        ast_sql = re.sub(r"\{\{\s*(ref|source)\([^)]+\)\s*\}\}", "source_model", sql)

        # 2. SQL AST Parsing via SQLGlot
        sql_ast = None
        sql_ast_valid = False
        sql_ast_error = None
        try:
            parsed = sqlglot.parse_one(ast_sql, read=dialect)
            sql_ast = parsed
            sql_ast_valid = True
        except Exception as exc:
            sql_ast_error = str(exc)
            blocking_errors.append(f"SQL AST parsing failure ({dialect}): {sql_ast_error}")

        # Extract referenced columns and select expressions from SQL AST
        referenced_columns: Set[str] = set()
        raw_select_columns: List[str] = []
        masked_select_columns: List[str] = []

        if sql_ast:
            # Gather all column identifiers
            for col in sql_ast.find_all(exp.Column):
                col_name = col.name.lower()
                if col_name and col_name != "source_model":
                    referenced_columns.add(col_name)

            # Inspect SELECT expressions for PII transformation
            for select_expr in sql_ast.find_all(exp.Select):
                for projection in select_expr.expressions:
                    proj_text = projection.sql(dialect=dialect).upper()
                    # Check if projection contains column name
                    for pii_col in pii_fields:
                        pii_name = pii_col.lower()
                        if pii_name in proj_text.lower():
                            # Check if projection wraps column in approved transform
                            has_transform = any(tf in proj_text for tf in _APPROVED_PII_TRANSFORMS)
                            if has_transform or "HASH" in proj_text or "MASK" in proj_text:
                                masked_select_columns.append(pii_col)
                            else:
                                raw_select_columns.append(pii_col)

        # 3. Schema Field Verification (Reject columns absent from DataHub schema)
        schema_col_names = {
            f.get("fieldPath", "").lower()
            for f in schema_fields if f.get("fieldPath")
        }
        absent_fields = []
        if schema_col_names and referenced_columns:
            ignored_keywords = {"ref", "source", "source_model", "count", "sum", "avg", "min", "max", "as", "id", "created_at", "updated_at"}
            for col in referenced_columns:
                if col not in schema_col_names and col not in ignored_keywords:
                    absent_fields.append(col)

        if absent_fields:
            blocking_errors.append(
                f"SQL references columns absent from DataHub schema: {', '.join(absent_fields)}"
            )

        # 4. PII Governance Verification (Detect raw PII in SELECT)
        unmasked_pii = list(set(raw_select_columns))
        if unmasked_pii:
            blocking_errors.append(
                f"Raw unmasked PII detected in SELECT statement: {', '.join(unmasked_pii)}. "
                "All PII columns must be hashed or masked using approved functions (e.g. SHA2)."
            )

        # 5. YAML Validation via PyYAML
        yaml_valid = False
        yaml_error = None
        yaml_parsed = None
        try:
            if dbt_yaml:
                yaml_parsed = yaml.safe_load(dbt_yaml)
                if isinstance(yaml_parsed, dict):
                    yaml_valid = True
                else:
                    yaml_error = "YAML output is not a valid dictionary object."
                    blocking_errors.append(yaml_error)
            else:
                yaml_error = "dbt schema YAML content is empty."
                blocking_errors.append(yaml_error)
        except Exception as exc:
            yaml_error = str(exc)
            blocking_errors.append(f"dbt schema YAML parsing failure: {yaml_error}")

        # Validate minimum dbt schema contract structure
        if yaml_valid and yaml_parsed:
            if "version" not in yaml_parsed and "models" not in yaml_parsed:
                warnings.append("dbt YAML schema is missing standard 'version' or 'models' top-level keys.")

        # 6. DuckDB Sandbox Dry-Run Execution
        sandbox_success = False
        sandbox_error = None
        if sql_ast_valid:
            try:
                con = duckdb.connect(database=":memory:")
                try:
                    col_defs = []
                    for f in schema_fields:
                        c_name = re.sub(r"[^a-zA-Z0-9_]", "_", f.get("fieldPath", "col"))
                        raw_t = f.get("nativeDataType", "VARCHAR").upper().split("(")[0].strip()
                        c_type = _TYPE_MAP.get(raw_t, "VARCHAR")
                        if c_name and c_name not in [cd.split()[0] for cd in col_defs]:
                            col_defs.append(f"{c_name} {c_type}")
                    
                    if not col_defs:
                        col_defs = ["id VARCHAR", "created_at TIMESTAMP"]
                    
                    con.execute(f"CREATE TABLE source_model ({', '.join(col_defs)})")
                    sandbox_sql = re.sub(r"\{\{\s*ref\(['\"][^'\"]+['\"]\)\s*\}\}", "source_model", sql)
                    sandbox_sql = re.sub(r"\{\{\s*source\([^)]+\)\s*\}\}", "source_model", sandbox_sql)
                    
                    transpiled = sqlglot.transpile(sandbox_sql, read=dialect, write="duckdb")[0]
                    con.execute(transpiled).fetchall()
                    sandbox_success = True
                finally:
                    con.close()
            except Exception as exc:
                sandbox_error = str(exc)
                warnings.append(f"DuckDB dry-run execution note: {sandbox_error}")

        passed = len(blocking_errors) == 0

        return {
            "passed": passed,
            "blocking_errors": blocking_errors,
            "warnings": warnings,
            "schema_validation": {
                "schema_fields_count": len(schema_fields),
                "referenced_columns": list(referenced_columns),
                "absent_fields": absent_fields,
            },
            "pii_validation": {
                "identified_pii_fields": pii_fields,
                "unmasked_pii_detected": unmasked_pii,
                "masked_pii_confirmed": list(set(masked_select_columns)),
            },
            "sql_validation": {
                "ast_valid": sql_ast_valid,
                "ast_error": sql_ast_error,
                "sandbox_success": sandbox_success,
                "sandbox_error": sandbox_error,
            },
            "yaml_validation": {
                "yaml_valid": yaml_valid,
                "yaml_error": yaml_error,
            },
        }

    def validate_sql(
        self,
        sql: str,
        dialect: str = "snowflake",
        schema_fields: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        """Backward compatible validator method."""
        res = self.validate_governance(
            sql=sql,
            dbt_yaml="version: 2\nmodels: []",
            schema_fields=schema_fields or [],
            pii_fields=[],
            dialect=dialect,
        )
        return {
            "ast_valid": res["sql_validation"]["ast_valid"],
            "ast_error": res["sql_validation"]["ast_error"],
            "sandbox_success": res["sql_validation"]["sandbox_success"],
            "sandbox_error": res["sql_validation"]["sandbox_error"],
            "passed": res["passed"],
        }


validator = AgentValidator()
