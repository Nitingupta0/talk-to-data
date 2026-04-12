# src/engine/templates.py

def get_prompt_template(intent, schema, semantic_layer, user_query):
    base_prompt = f"""
    You are a strictly logical pandas data analyst. 
    Dataset Schema: {schema}
    Semantic Rules: {semantic_layer}
    
    Generate purely Python pandas code to answer: "{user_query}"
    The dataframe is already loaded as a variable named 'df'.
    Store the final output in a variable named 'result'.
    
    CRITICAL RULES:
    1. DO NOT import streamlit. DO NOT use st.write() or st.dataframe().
    2. DO NOT import any external libraries.
    3. Return ONLY valid Python pandas code. No explanations.
    4. Do not include markdown formatting like ```python.

    DATE & TIME HANDLING RULES:
    1. If a column contains month names (e.g., 'Jan', 'Feb', 'March'), DO NOT use pd.to_datetime().
    2. To sort by month, use a mapping dictionary: 
       month_map = {{'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}}
    3. If the user asks for a trend, sort the dataframe using that mapping before plotting.
    
    GENERALIZED PROJECTION RULES:
    1. IDENTIFY: Find the independent variable (X) and the dependent metric (Y).
    2. TREND: Calculate the mathematical relationship between X and Y using available data.
    3. EXTEND: If the user asks for 'more', 'future', or 'predictions':
    - Identify the 'step' of X (is it increments of 1? Is it a sequence?).
    - Generate the next N values of X that do not exist in the current 'df'.
    - Apply the trend to calculate the new Y values.
    4. UNION: Combine the original 'df' with the new projected rows into 'result'.
    5. SAFETY: If X is categorical and has no logical sequence, explain that prediction is not possible.
    """

    """
    DYNAMIC CATEGORY HANDLING & SORTING:
    1. SELF-CONTAINED LOGIC: You operate in a strict, headless sandbox. You do NOT have access to external helper variables or pre-defined dictionaries.
    2. DYNAMIC MAPPING: If the user asks to sort, filter, or analyze ordinal categorical data (e.g., Months, Days of Week, 'Low/Med/High', 'Q1/Q2/Q3'):
    - YOU must explicitly create a mapping dictionary INSIDE your Python code before you use it.
    - Example: 
        # AI generates this dynamically based on the column context
        category_map = {'Jan': 1, 'Feb': 2, 'Mar': 3} 
        df['sort_col'] = df['Month'].map(category_map)
    3. TIME SERIES: If columns contain string dates/months and the user wants a trend, map them to integers dynamically to avoid Pandas nanosecond boundary errors.
    4. ⚠️ ORDER OF OPERATIONS (CRITICAL) ⚠️: 
    If you need to aggregate data (groupby) AND sort by a category, you MUST apply the mapping dictionary to the RESULT dataframe AFTER the groupby, not before.
    - CORRECT: 
        result = df.groupby('Month')['Revenue'].sum().reset_index()
        result['order'] = result['Month'].map(cat_map)
        result = result.sort_values('order')
    """
    
    templates = {
        "breakdown": base_prompt + "\n# Use groupby and appropriate aggregations. Reset the index.",
        "comparison": base_prompt + "\n# Isolate the two segments, compare them, and return the difference.",
        "change_analysis": base_prompt + "\n# Calculate percentage change over the time or category variable.",
        "summary": base_prompt + "\n# Provide high-level descriptive statistics."
    }
    return templates.get(intent, base_prompt)