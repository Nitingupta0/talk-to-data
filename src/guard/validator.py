import pandas as pd

def validate_code(code_str, schema_columns):
    """Pre-execution checks."""
    forbidden_imports = ["os", "sys", "subprocess", "shutil", "requests"]
    if any(bad in code_str for bad in forbidden_imports):
        return False, "Blocked: Code contains forbidden system modules."
    return True, "Valid"

def validate_result(result):
    """Post-execution checks."""
    if result is None:
        return False, "Execution produced no result."
    if isinstance(result, pd.DataFrame) and result.empty:
        return False, "The query executed properly, but returned an empty dataset."
    return True, "Valid"