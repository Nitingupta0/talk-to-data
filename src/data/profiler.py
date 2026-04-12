import pandas as pd

def generate_profile(df: pd.DataFrame) -> dict:
    """Extracts schema, data types, and sample values for the LLM context."""
    return {
        "columns": df.columns.tolist(),
        "types": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "null_counts": df.isnull().sum().to_dict(),
        "unique_samples": {col: df[col].dropna().unique()[:5].tolist() for col in df.columns},
        "shape": df.shape
    }