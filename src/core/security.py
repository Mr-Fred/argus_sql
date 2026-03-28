import sqlglot
import sqlglot.expressions as exp

class SecurityError(Exception):
    pass

def validate_ast(sql: str) -> None:
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
