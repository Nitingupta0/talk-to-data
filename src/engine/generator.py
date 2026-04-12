import os
from groq import Groq
from .templates import get_prompt_template

def generate_code(query: str, intent: str, profile: dict, semantic_dict: dict, chat_history: list = None) -> tuple[str, str]:
    """
    Generates Pandas code while considering the conversation context.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None, "⚠️ GROQ_API_KEY not found. Please add it to your .env file."

    try:
        client = Groq(api_key=api_key)
        MODEL = "llama-3.3-70b-versatile"
        
        # 1. Format Chat History for context
        history_context = ""
        if chat_history:
            # We only take the last 4 messages to keep the prompt clean and focused
            recent_messages = chat_history[-4:]
            history_context = "\n".join([
                f"{msg['role'].upper()}: {msg['content']}" 
                for msg in recent_messages
            ])

        # 2. Get the base template
        # Build multi-file awareness context
        all_files_context = ""
        if profile.get("sources"):
            all_files_context = f"""
            ### AVAILABLE FILES
            The user has uploaded multiple files: {profile.get('sources', [])}
            Currently working on the merged dataset.
            """
        else:
            # Check if we should mention other available files
            all_files_context = ""

        base_prompt = get_prompt_template(intent, profile, semantic_dict, query)
        base_prompt = all_files_context + base_prompt
        
        # 3. Augment the prompt with context
        full_prompt = f"""
        ### CONVERSATION HISTORY
        {history_context if history_context else "No previous conversation."}
        
        ### CURRENT TASK
        User Question: {query}
        {base_prompt}
        
        ### INSTRUCTION
        If the current question refers to 'this', 'that', 'it', or 'the previous data', 
        write code that filters or references the result from the history above. 
        Otherwise, query the full dataframe 'df'.
        """
        
        system_instruction = (
            "You are a strictly headless Pandas calculation engine. "
            "CRITICAL RULES:\n"
            "1. NEVER import streamlit, matplotlib, or seaborn.\n"
            "2. NEVER use 'st.' commands.\n"
            "3. Your ONLY job is to filter or aggregate the dataframe 'df' using pandas.\n"
            "4. Save the output to a variable named 'result'.\n"
            "5. OUTPUT ONLY PURE PYTHON CODE. No conversational filler."
            "Before writing code, add a Python comment explaining your mathematical logic (e.g., # Calculating 5-period moving average for projection)."
        )

        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.0, 
            max_tokens=1024
        )
        
        code_str = response.choices[0].message.content.strip()
        
        # --- Clean Markdown ---
        if "```python" in code_str:
            code_str = code_str.split("```python")[1].split("```")[0].strip()
        elif "```" in code_str:
            code_str = code_str.split("```")[1].split("```")[0].strip()
            
        # 🛡️ THE IRON CLAD FIREWALL 🛡️
        if "streamlit" in code_str.lower() or "st." in code_str:
            return None, "The AI stubbornly tried to build a UI. Please rephrase."
            
        return code_str, None
        
    except Exception as e:
        return None, f"Code Generation Failed: {str(e)}"