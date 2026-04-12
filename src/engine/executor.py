import pandas as pd
import contextlib
import io
import ast
import math 
import numpy as np

def execute_code(code_str, df):
    """Executes code using an AST parser to guarantee no rogue imports."""
    
    # 1. AST SECURITY CHECK (The Ultimate Firewall)
    try:
        tree = ast.parse(code_str)
        for node in ast.walk(tree):
            # If the AI tries to import ANYTHING, we kill it instantly.
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return None, "Security Guardrail: The AI tried to import a library. Blocked."
            
            # If the AI tries to run dangerous functions like eval() or exec()
            if isinstance(node, ast.Call) and hasattr(node.func, 'id'):
                if node.func.id in ['eval', 'exec', 'open']:
                    return None, f"Security Guardrail: Forbidden function '{node.func.id}' detected."
    except SyntaxError as e:
        return None, f"The AI generated invalid code: {str(e)}"

    # 2. Execution Environment
    safe_builtins = {
        "print": print, "range": range, "len": len, "zip": zip,"enumerate": enumerate,
        "int": int, "float": float, "str": str, "bool": bool,
        "list": list, "dict": dict, "set": set, "tuple": tuple,
        "sum": sum, "min": min, "max": max, "abs": abs, "round": round
    }
    
    # We strictly define globals. 'st' does not exist here.
    safe_globals = {
        "__builtins__": {**safe_builtins, "math": math},
        "pd": pd,
        "np": np,
        "math": math
    }
    
    safe_locals = {
        "df": df
    }
    
    stdout_trap = io.StringIO()
    
    try:
        with contextlib.redirect_stdout(stdout_trap):
            exec(code_str, safe_globals, safe_locals)
        
        if "result" not in safe_locals:
            return None, "Error: The AI failed to save the answer to the 'result' variable."
            
        return safe_locals.get("result"), None
        
    except Exception as e:
        return None, f"Execution Error: {str(e)}"