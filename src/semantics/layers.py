import yaml

def get_semantic_layer(profile=None):
    """
    Loads metric definitions. 
    If none exists, generates a baseline from the data profile.
    """
    if not profile:
        return {}
    
    # Baseline auto-generated semantic dictionary
    return {
        "metrics": {},
        "dimensions": profile.get("columns", []),
        "business_rules": "Always exclude rows where 'status' is 'cancelled' or 'failed', if such a column exists."
    }