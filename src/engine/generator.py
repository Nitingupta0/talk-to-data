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
        
        # 1. Format Chat History — only USER messages for context
        # We exclude assistant messages to prevent the LLM from mimicking
        # any narrative style from previous responses.
        history_context = ""
        if chat_history:
            user_msgs = [m for m in chat_history if m["role"] == "user"]
            recent_user_msgs = user_msgs[-3:]  # last 3 user questions only
            if recent_user_msgs:
                history_context = "\n".join([
                    f"PREVIOUS USER QUESTION: {msg['content']}"
                    for msg in recent_user_msgs[:-1]  # exclude the current question
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
            "1. NEVER import streamlit, matplotlib, seaborn, or plotly.\n"
            "2. NEVER use 'st.' commands.\n"
            "3. Your ONLY job is to filter or aggregate the dataframe 'df' using pandas.\n"
            "4. Save the output to a variable named 'result'.\n"
            "5. OUTPUT ONLY PURE PYTHON CODE. Zero prose, zero explanation, zero narrative.\n"
            "6. If the user asks for a chart or visualization, produce the aggregated DataFrame "
            "that feeds the chart — do NOT describe the chart or say what you would plot.\n"
            "7. 'result' must always be a DataFrame or a scalar. Never a string description."
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

        # --- Strip any plotly/matplotlib/seaborn import lines the LLM snuck in ---
        _vizlib_names = {"plotly", "matplotlib", "seaborn", "px", "go", "plt"}
        cleaned_lines = []
        for line in code_str.splitlines():
            s = line.strip()
            if s.startswith("import ") or s.startswith("from "):
                parts = s.replace("import ", " ").replace("from ", " ").split()
                lib = parts[0].split(".")[0] if parts else ""
                if lib in _vizlib_names:
                    continue  # drop silently — charting is handled downstream
            cleaned_lines.append(line)
        code_str = "\n".join(cleaned_lines)

        # 🛡️ THE IRON CLAD FIREWALL 🛡️
        if "streamlit" in code_str.lower() or "st." in code_str:
            return None, "The AI stubbornly tried to build a UI. Please rephrase."

        return code_str, None
        
    except Exception as e:
        return None, f"Code Generation Failed: {str(e)}"