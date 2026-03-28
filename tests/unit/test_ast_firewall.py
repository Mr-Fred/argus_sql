import pytest
from src.core.security import validate_ast, SecurityError

def test_valid_select_query():
    validate_ast("SELECT * FROM users")
    validate_ast("SELECT id, name FROM users WHERE id = 1")
    validate_ast("""
        SELECT u.name, COUNT(o.id) 
        FROM users u 
        JOIN orders o ON u.id = o.user_id 
        GROUP BY u.name
    """)

def test_valid_complex_select_query():
    validate_ast("""
        WITH recent_orders AS (
            SELECT user_id, amount FROM orders WHERE date > '2023-01-01'
        )
        SELECT u.name, r.amount
        FROM users u
        JOIN recent_orders r ON u.id = r.user_id
        WHERE u.status = 'active'
    """)
    # Union query
    validate_ast("SELECT id FROM a UNION ALL SELECT id FROM b")

def test_multiple_statements_raises_error():
    with pytest.raises(SecurityError, match="Multiple statements"):
        validate_ast("SELECT * FROM users; SELECT * FROM orders;")
        
def test_empty_statement_raises_error():
    with pytest.raises(SecurityError, match="No valid SQL"):
        validate_ast("")
    with pytest.raises(SecurityError, match="No valid SQL"):
        validate_ast("   ;")

def test_forbidden_root_commands_raise_error():
    forbidden_queries = [
        "DROP TABLE users",
        "INSERT INTO users (name) VALUES ('test')",
        "ALTER TABLE users ADD COLUMN age INT",
        "UPDATE users SET age = 20 WHERE id = 1",
        "DELETE FROM users WHERE id = 1",
        "CREATE TABLE new_users (id INT)",
        "TRUNCATE TABLE users"
    ]
    for q in forbidden_queries:
        with pytest.raises(SecurityError, match="(Forbidden SQL|Only SELECT)"):
            validate_ast(q)

def test_nested_forbidden_commands_raise_error():
    edge_cases = [
        # Subquery attempting to mutate
        "SELECT * FROM (DELETE FROM users WHERE id = 1)",
        "SELECT * FROM users WHERE id IN (DROP TABLE orders)",
        "WITH bad_cte AS (UPDATE users SET age = 20) SELECT * FROM bad_cte"
    ]
    for q in edge_cases:
        # Depending on how sqlglot parses these invalid subqueries, they might raise a parse error or a logic error.
        # Both represent a SecurityError.
        with pytest.raises(SecurityError):
            validate_ast(q)

def test_syntax_error_is_caught():
    with pytest.raises(SecurityError, match="SQL parsing error"):
        validate_ast("SELECT * FROM (((")
