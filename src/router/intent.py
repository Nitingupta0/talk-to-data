import os
from groq import Groq

def classify_intent(query: str, profile: dict):
    """
    Acts as an Orchestrator Agent. 
    Returns: (intent_name, error_message)
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        # Return fallback intent + error message
        return "summary", "⚠️ GROQ_API_KEY missing. Defaulting to 'summary' intent."

    try:
        client = Groq(api_key=api_key)
        MODEL = "llama-3.3-70b-versatile"
        
        system_prompt = """You are an orchestrator agent for a data analysis tool. 
        Given a user question and a dataset schema, decide which type of analysis is needed. 
        Reply with ONLY ONE of these exact words:
        - change_analysis 
        - comparison 
        - breakdown 
        - summary"""

        # We pass only the columns and types to save tokens and speed up the routing
        schema_context = {
            "columns": profile.get("columns", []),
            "types": profile.get("types", {})
        }

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Dataset profile:\n{schema_context}\n\nQuestion: {query}"}
            ],
            max_tokens=10,
            temperature=0.0 # Strict determinism for routing
        )
        
        # Clean the output
        intent = response.choices[0].message.content.strip().lower()
        
        # Guardrail: Ensure the LLM didn't invent a new category
        valid_intents = ["change_analysis", "comparison", "breakdown", "summary"]
        if intent not in valid_intents:
            return "summary", f"⚠️ Router generated invalid intent: '{intent}'. Defaulting to summary."
            
        # Success! Return the intent and "None" for the error
        return intent, None

    except Exception as e:
        # Fallback if the API crashes
        return "summary", f"Orchestrator Error: {str(e)}. Defaulting to summary."