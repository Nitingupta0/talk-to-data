import pandas as pd
import os
from groq import Groq
from .charts import generate_chart

def generate_welcome_message(profile):
    """Generates a dynamic greeting and 3 suggested questions based on the dataset schema."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "Data loaded successfully! What would you like to know?"

    try:
        client = Groq(api_key=api_key)
        columns = profile.get('columns', [])
        
        prompt = f"""
        You are a helpful AI Data Analyst. A user just uploaded a new dataset.
        Here are the columns in their data: {columns}
        
        Task:
        1. Write a friendly 1-sentence welcome message.
        2. Provide exactly 3 bullet points suggesting specific, interesting analytical questions they could ask you based on these exact columns.
        Keep it concise and conversational. Do not use large headers.
        """
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return "Data loaded! You can ask me to compare categories, analyze trends, or summarize the metrics."

def generate_narrative(result, query):
    """Uses LLM to explain the data table in plain English."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return ""

    try:
        client = Groq(api_key=api_key)
        data_str = result.to_string() if isinstance(result, pd.DataFrame) else str(result)
        
        prompt = f"""
        You are a senior business intelligence analyst. 
        User Question: {query}
        Data Result:
        {data_str}
        
        Analyze the data above and provide a conversational 1-2 sentence summary. 
        - Mention the specific winner or highest value if comparing.
        - Use a professional yet friendly tone.
        - If the data is empty or unclear, politely explain why.
        """
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except:
        return "Here is the analysis of your data:"

def format_response(result, query, intent):
    """Packages the response into narrative, table, and chart components."""
    chart = None
    narrative = generate_narrative(result, query)
    table_md = None 
    
    print(f"DEBUG format_response: type={type(result)}, result=\n{result}")
    
    if isinstance(result, pd.DataFrame):
        print(f"DEBUG DataFrame shape={result.shape}, columns={list(result.columns)}")
        chart = generate_chart(result, intent, query) 
        print(f"DEBUG chart generated={chart is not None}")
        table_md = result.to_markdown(index=False)
        
    elif isinstance(result, pd.Series):
        table_md = result.to_frame().reset_index().to_markdown(index=False)
        
    return {
        "narrative": narrative,
        "table": table_md, 
        "chart": chart
    }