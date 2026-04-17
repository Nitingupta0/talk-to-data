import pandas as pd
import contextlib
import io
import ast
import math 
import numpy as np

# Libraries the LLM is allowed to reference (already in safe_globals)
_ALLOWED_IMPORTS = {"pandas", "pd", "numpy", "np", "math"}

# Dangerous builtins to block
_FORBIDDEN_CALLS = {"eval", "exec", "open", "compile", "__import__"}

def _strip_allowed_imports(code_str: str) -> str:
    """Remove import lines for allowed libraries so the AST check doesn't
    block them, while still catching dangerous imports below."""
    clean_lines = []
    for line in code_str.splitlines():
        stripped = line.strip()
        # Drop lines like: import numpy as np / import pandas as pd / from numpy import ...
        if stripped.startswith("import ") or stripped.startswith("from "):
            # Check if it's an allowed library
            parts = stripped.replace("import ", " ").replace("from ", " ").split()
            lib = parts[0].split(".")[0] if parts else ""
            if lib in _ALLOWED_IMPORTS:
                continue  # silently drop — it's already in safe_globals
            # Otherwise keep it so the AST check below catches it
        clean_lines.append(line)
    return "\n".join(clean_lines)


def execute_code(code_str, df):
    """Executes code using an AST parser to guarantee no rogue imports."""

    # 1. PRE-CLEAN: strip redundant but harmless imports (pd, np, math)
    code_str = _strip_allowed_imports(code_str)

    # 2. AST SECURITY CHECK
    try:
        tree = ast.parse(code_str)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                # Any import that survived stripping is dangerous
                return None, "Security Guardrail: The AI tried to import a forbidden library. Blocked."

            if isinstance(node, ast.Call) and hasattr(node.func, 'id'):
                if node.func.id in _FORBIDDEN_CALLS:
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