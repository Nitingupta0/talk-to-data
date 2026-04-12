def generate_citation(used_columns, row_count, filters_applied="None"):
    """Builds the transparency footer for the UI."""
    return f"**Source:** Analyzed {row_count:,} rows. \n**Columns accessed:** `{', '.join(used_columns)}`."