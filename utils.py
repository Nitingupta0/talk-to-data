import pandas as pd

def load_dataset(uploaded_file):
    """Load a CSV file uploaded by the user into a pandas DataFrame."""
    df = pd.read_csv(uploaded_file)
    return df

def get_dataset_profile(df):
    """Generate a detailed text summary of the dataset for the AI to understand."""
    profile = []
    profile.append(f"Number of rows: {len(df)}")
    profile.append(f"Number of columns: {len(df.columns)}")
    profile.append(f"Column names and types:")
    for col in df.columns:
        profile.append(f"  - {col} ({df[col].dtype})")
    profile.append(f"\nFull dataset:\n{df.to_string()}")
    profile.append(f"\nBasic statistics:\n{df.describe().to_string()}")
    return "\n".join(profile)

def format_source_reference(df, answer):
    """Add a source transparency note to every answer."""
    cols = ", ".join(df.columns.tolist())
    return f"{answer}\n\n---\n📊 **Source:** Dataset with columns: {cols} | Rows analysed: {len(df)}"