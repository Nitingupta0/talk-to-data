# src/chat/clarifier.py
import os
from groq import Groq

def check_for_ambiguity(query, profile):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key: return False, ""

    client = Groq(api_key=api_key)
    
    schema_info = {
        "columns": profile.get("columns", []),
        "types": profile.get("types", {})
    }

    # --- THE IMPROVED "SMART" PROMPT ---
    prompt = f"""
    You are a data analyst assistant. 
    User Query: "{query}"
    Data Schema: {schema_info}
    
    Your goal is to decide if you can fulfill this request with a REASONABLE ASSUMPTION.
    
    RULES:
    1. If the user is slightly vague (e.g., "compare regions" instead of "compare Sales by Region"), do NOT ask for context. Just pick the most logical columns and proceed.
    2. Only stop and ask for clarification if:
       - The request is a single word (e.g., "Data").
       - There are multiple columns with similar names and you can't tell which one matters (e.g., 'Gross_Profit' vs 'Net_Profit' when they just say 'Profit').
       - The request is completely unrelated to the data.
    
    If it is even 70% clear, reply with exactly 'CLEAR'.
    If it is impossible to answer, provide a SHORT, 1-sentence clarification question.
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0 # Keep this 0.0 for consistent logic
    )
    
    answer = response.choices[0].message.content.strip()
    
    # Check if 'CLEAR' is anywhere in the response
    if "CLEAR" in answer.upper():
        return False, ""
    return True, answer