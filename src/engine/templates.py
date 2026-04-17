# src/engine/templates.py

def get_prompt_template(intent, schema, semantic_layer, user_query):

    columns = schema.get("columns", [])
    dtypes = schema.get("types", {})
    samples = schema.get("unique_samples", {})

    # Build a tight, explicit column reference block
    column_block = "\n".join(
        f"  - '{col}' ({dtypes.get(col, 'unknown')}) — sample values: {samples.get(col, [])}"
        for col in columns
    )

    base_prompt = f"""
You are a strictly logical pandas data analyst.

AVAILABLE COLUMNS — you may ONLY reference these exact column names:
{column_block}

Semantic Rules: {semantic_layer}

Your task: generate Python pandas code to answer: "{user_query}"

The dataframe is already loaded as 'df'. Store your final output in 'result'.

ABSOLUTE RULES:
1. Use ONLY the column names listed above. Never invent or guess a column name.
2. If the user asks for a chart (pie, bar, line, etc.) — produce the aggregated DataFrame
   that feeds the chart. Do NOT describe the chart. Do NOT say "would likely".
   Example: user says "pie chart of sales by genre"
     result = df.groupby('Genre')['Global_Sales'].sum().reset_index()
3. For a pie chart with no obvious value column, count occurrences:
     result = df['SomeColumn'].value_counts().reset_index()
     result.columns = ['Category', 'Count']
4. Return ONLY valid Python pandas code. Zero prose, zero explanation.
5. Do NOT import any library. Do NOT use plotly, matplotlib, or seaborn.
6. 'result' must always be a DataFrame.

DATE & TIME RULES:
- If a column has month name strings (Jan, Feb...), do NOT use pd.to_datetime().
- Sort by month using a manual mapping dict applied AFTER any groupby.

NULL HANDLING:
- Always call .dropna(subset=[relevant_col]) before groupby or value_counts.
"""

    templates = {
        "breakdown":       base_prompt + "\n# Use groupby + aggregation. Reset index. Return a clean 2-column DataFrame.",
        "comparison":      base_prompt + "\n# Isolate the segments being compared and return their values.",
        "change_analysis": base_prompt + "\n# Calculate percentage or absolute change over time or category.",
        "summary":         base_prompt + "\n# Return descriptive statistics as a clean DataFrame."
    }
    return templates.get(intent, base_prompt)