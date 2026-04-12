import pandas as pd
from .profiler import generate_profile

def load_and_profile(file):
    if file.name.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    
    profile = generate_profile(df)
    return df, profile