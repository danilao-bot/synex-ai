"""SQL dialect AST inspector to enforce read-only execution safety."""

import logging
import sqlglot
import sqlglot.expressions as exp

logger = logging.getLogger(__name__)

_MUTATION_CLASSES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Merge,
    exp.Create,
    exp.Drop,
    exp.Alter,
)


def inspect_sql_safety(sql: str, dialect: str = "snowflake") -> tuple[bool, str | None]:
    """Parse a generated SQL statement and verify it contains no DDL/DML mutation expressions.
    
    Returns:
        (is_safe, violation_reason)
    """
    if not sql or not isinstance(sql, str):
        return True, None

    import re
    # Strip jinja/dbt template blocks before parsing
    cleaned_sql = re.sub(r"\{\{\s*ref\(['\"]([^'\"]+)['\"]\)\s*\}\}", r"\1", sql)
    cleaned_sql = re.sub(r"\{\{[^}]*\}\}", "dummy_relation", cleaned_sql)
    cleaned_sql = re.sub(r"\{%[^%]*%\}", "", cleaned_sql)
    try:
        # Simple string-level check as safety net for common mutation keywords
        lower_sql = cleaned_sql.lower()
        forbidden_keywords = ("drop table", "alter table", "delete from", "truncate table", "insert into")
        for kw in forbidden_keywords:
            if kw in lower_sql:
                return False, f"SQL contains forbidden mutation sequence: '{kw}'"

        # AST parsing check
        parsed = sqlglot.parse(cleaned_sql, read=dialect)
        for statement in parsed:
            if not statement:
                continue
                
            # Inspect AST nodes for mutation classes
            for node in statement.walk():
                if isinstance(node, _MUTATION_CLASSES):
                    logger.warning("Dangerous SQL statement detected, class: %s", type(node).__name__)
                    return False, f"SQL contains unauthorized modification statement: '{type(node).__name__}'"
                    
            # Enforce that the top-level statement must be SELECT or WITH/CTE
            # (unless it's empty/comment)
            if not statement.find(exp.Select) and not statement.find(exp.CTE) and not isinstance(statement, (exp.Select, exp.CTE)):
                # If it's a completely unrelated statement (e.g. commands, show, etc.)
                statement_name = statement.key.upper() if hasattr(statement, "key") else "UNKNOWN"
                logger.warning("SQL statement is not a query: %s", statement_name)
                return False, f"SQL statement must be a SELECT query, found: '{statement_name}'"

        return True, None
    except Exception as e:
        logger.warning("SQL Safety AST check failed to parse query: %s", e)
        # If sqlglot parsing fails, do we reject it?
        # Yes! In a zero-trust production-grade setup, if we cannot parse it, we should reject it to be safe.
        return False, f"SQL AST parsing failure: {e}. Unable to verify query safety."
