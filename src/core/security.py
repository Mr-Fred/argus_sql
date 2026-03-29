"""
Security module for validating SQL statements.

This module provides functionality to parse and validate SQL queries using an AST
to ensure they conform to security constraints, specifically restricting commands to 
read-only operations like SELECT and UNION, and blocking unauthorized operations like 
DROP, INSERT, UPDATE, DELETE, etc.
"""

import sqlglot
import sqlglot.expressions as exp

class SecurityError(Exception):
    """Exception raised for security violations or forbidden SQL commands."""
    pass

def validate_ast(sql: str) -> None:
    """
    Validate a SQL query string by parsing its Abstract Syntax Tree (AST).
    
    Ensures that the SQL statement is syntactically correct, consists of a
    single SELECT or UNION query, and does not contain any forbidden operations
    (e.g., DROP, INSERT, ALTER, DELETE, CREATE, UPDATE).
    
    Args:
        sql: The SQL query string to validate.
        
    Raises:
        SecurityError: If there is a parsing error, no valid statement, multiple 
            statements, non-SELECT queries, or forbidden nodes are detected.
    """
    try:
        # We use error_level=RAISE to ensure syntax errors are caught
        statements = sqlglot.parse(sql, read="bigquery", error_level=sqlglot.ErrorLevel.RAISE)
    except sqlglot.errors.ParseError as e:
        raise SecurityError(f"SQL parsing error: {e}") from e

    statements = [s for s in statements if s is not None]

    if not statements:
        raise SecurityError("No valid SQL statement found.")

    if len(statements) > 1:
        raise SecurityError("Multiple statements are not allowed. Only a single SELECT query is permitted.")

    ast = statements[0]

    if not isinstance(ast, (exp.Select, exp.Union)):
        raise SecurityError("Only SELECT queries are allowed.")

    forbidden_nodes = (
        exp.Drop,
        exp.Insert,
        exp.Alter,
        exp.Update,
        exp.Delete,
        exp.Create,
        exp.Command,
        exp.Commit,
        exp.Rollback,
        exp.Merge,
    )

    for forbidden in forbidden_nodes:
        if ast.find(forbidden):
            raise SecurityError(f"Forbidden SQL command detected: {forbidden.__name__}")
