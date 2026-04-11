import os
from groq import Groq
from dotenv import load_dotenv
from utils import get_dataset_profile, format_source_reference

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

def ask_orchestrator(question, df):
    """Decides which agent should handle the question."""
    profile = get_dataset_profile(df)
    
    system_prompt = """You are an orchestrator agent. Given a user question and a dataset profile,
    decide which type of analysis is needed. Reply with ONLY one of these words:
    - ANALYSIS (for trends, drivers, why something changed)
    - COMPARISON (for comparing time periods, regions, products)
    - BREAKDOWN (for decomposing totals into parts)
    - SUMMARY (for general summaries or weekly/monthly digests)"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Dataset profile:\n{profile}\n\nQuestion: {question}"}
        ],
        max_tokens=10
    )
    return response.choices[0].message.content.strip()


def ask_analysis_agent(question, df):
    """Identifies drivers and reasons behind changes in data."""
    profile = get_dataset_profile(df)
    
    system_prompt = """You are a data analysis expert. The user will ask why something changed or 
    what the trend is. Analyse the dataset profile and answer clearly in simple English. 
    Always reference which columns or values support your answer.
    Keep your answer under 5 sentences. No jargon."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Dataset:\n{profile}\n\nQuestion: {question}"}
        ],
        max_tokens=300
    )
    answer = response.choices[0].message.content.strip()
    return format_source_reference(df, answer)


def ask_comparison_agent(question, df):
    """Compares values across time, regions, or categories."""
    profile = get_dataset_profile(df)
    
    system_prompt = """You are a comparison analyst. The user wants to compare values in the dataset.
    Provide a clear, easy-to-understand comparison. Mention specific numbers where possible.
    Keep your answer under 5 sentences. No jargon."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Dataset:\n{profile}\n\nQuestion: {question}"}
        ],
        max_tokens=300
    )
    answer = response.choices[0].message.content.strip()
    return format_source_reference(df, answer)


def ask_breakdown_agent(question, df):
    """Breaks down totals into components and highlights biggest contributors."""
    profile = get_dataset_profile(df)
    
    system_prompt = """You are a breakdown analyst. The user wants to understand what makes up a total.
    Decompose the numbers, highlight the biggest contributors, and explain clearly.
    Keep your answer under 5 sentences. No jargon."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Dataset:\n{profile}\n\nQuestion: {question}"}
        ],
        max_tokens=300
    )
    answer = response.choices[0].message.content.strip()
    return format_source_reference(df, answer)


def ask_summary_agent(question, df):
    """Produces a concise summary of the dataset highlighting key insights."""
    profile = get_dataset_profile(df)
    
    system_prompt = """You are a business intelligence summariser. Scan the dataset and produce 
    a concise, clear summary. Focus on what truly matters — key trends, anomalies, and shifts.
    Write for a non-technical audience. Keep it under 6 sentences."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Dataset:\n{profile}\n\nQuestion: {question}"}
        ],
        max_tokens=300
    )
    answer = response.choices[0].message.content.strip()
    return format_source_reference(df, answer)


def get_conversational_reply(question):
    """Handle casual/irrelevant messages with friendly responses."""
    
    casual_map = {
        # Greetings
        "hi": "👋 Hey there! I'm your data assistant. Upload a CSV and ask me anything about it!",
        "hello": "👋 Hello! Ready to explore some data? Upload a CSV file and fire away!",
        "hey": "👋 Hey! I'm here to help you understand your data. Upload a CSV to get started!",
        
        # Thanks
        "thanks": "😊 You're welcome! Got more questions about your data? I'm here!",
        "thank you": "😊 Happy to help! Feel free to ask anything else about your dataset.",
        "thankyou": "😊 Anytime! Let me know if you have more data questions.",
        
        # Affirmations
        "ok": "👍 Alright! What would you like to know about your data?",
        "okay": "👍 Sure thing! Ask me anything about your dataset.",
        "cool": "😎 Glad you think so! What else can I help you analyse?",
        "nice": "😊 Thanks! Want to explore more insights from your data?",
        "great": "🙌 Great! What else would you like to dig into?",
        "good": "👍 Good to hear! Any more questions about your data?",
        "alright": "👍 Alright! What would you like to explore next?",
        
        # Farewells
        "bye": "👋 Goodbye! Come back anytime you have data to explore!",
        "goodbye": "👋 See you later! Your data will be waiting!",
        "see you": "👋 See you! Come back anytime!",
        
        # Reactions
        "wow": "😄 I know right! Data can be pretty revealing. Want to explore more?",
        "lol": "😄 Haha! Anything else you'd like to know about your data?",
        "haha": "😄 Glad I could amuse! Need any more data insights?",
        "interesting": "🤓 Data is always interesting! Want to dig deeper?",
        "amazing": "🌟 Right?! There's always more to discover. What else can I help with?",
        
        # Confusion/unsure
        "idk": "🤔 Not sure what to ask? Try: 'Summarise this dataset' or click one of the quick question buttons!",
        "i don't know": "🤔 That's okay! Try asking: 'What are the key trends?' or 'Give me a summary'.",
        "help": "🆘 Sure! Here's what I can do:\n- Explain why something changed\n- Compare regions or products\n- Break down totals\n- Summarise your dataset\n\nJust ask in plain English!",
        
        # Compliments
        "good job": "🙏 Thank you so much! I'm doing my best to make data easy for you!",
        "well done": "🙏 That means a lot! What else can I help you discover?",
        "awesome": "🌟 Thanks! Want to keep exploring your data?",
        "love it": "❤️ So glad! Ask me anything else about your dataset!",
        "love this": "❤️ That makes me happy! What else would you like to know?",
        
        # Frustration
        "this is bad": "😔 I'm sorry to hear that. Could you tell me what went wrong? I'll try to do better!",
        "wrong": "😔 Sorry about that! Try rephrasing your question or use the quick question buttons below.",
        "not working": "🔧 Let's fix that! Try uploading your CSV again or rephrase your question.",
        "useless": "😔 I'm sorry! Try asking something like 'Summarise this dataset' and I'll do my best!",
        
        # Random/test
        "test": "🧪 Test received! I'm working perfectly. Now try a real data question!",
        "testing": "🧪 All systems go! Upload a CSV and ask me something meaningful.",
        "random": "🎲 That's pretty random! But I'm here whenever you have a data question.",
    }
    
    cleaned = question.strip().lower()
    
    # Check for exact or partial matches
    for key, reply in casual_map.items():
        if key == cleaned or cleaned.startswith(key) or cleaned.endswith(key):
            return reply
    
    return None


def is_relevant_question(question, df):
    """Check if the question is actually relevant to data analysis."""
    
    irrelevant_phrases = [
        "thanks", "thank you", "hello", "hi", "hey", "ok", "okay",
        "cool", "nice", "great", "bye", "goodbye", "yes", "no", "yep",
        "nope", "lol", "haha", "wow", "sure", "alright", "fine",
        "good", "bad", "test", "testing", "random", "nothing", "idk",
        "awesome", "love it", "love this", "good job", "well done",
        "interesting", "amazing", "wrong", "useless", "not working"
    ]
    
    cleaned = question.strip().lower()
    
    if len(cleaned.split()) <= 3:
        for phrase in irrelevant_phrases:
            if phrase in cleaned:
                return False
    
    if len(cleaned) < 8 and not any(
        word in cleaned for word in ["why", "what", "how", "who", "when",
                                      "where", "show", "give", "compare",
                                      "top", "best", "worst", "trend"]
    ):
        return False

    system_prompt = """You are a strict gatekeeper for a data analysis app.
    The user must ask a genuine question about data, numbers, trends, comparisons, 
    summaries, or business insights.
    
    IRRELEVANT examples: "thanks", "hello", "ok cool", "bye", "test", 
    "what is love", "tell me a joke", random gibberish.
    
    RELEVANT examples: "why did sales drop", "compare regions", 
    "what is the trend", "summarise the data", "show breakdown".
    
    Reply with ONLY one word — RELEVANT or IRRELEVANT. Nothing else."""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User message: '{question}'\nDataset columns: {list(df.columns)}\nIs this a genuine data question?"}
        ],
        max_tokens=5
    )
    result = response.choices[0].message.content.strip().upper()
    return "RELEVANT" in result


def route_question(question, df):
    """Main function — orchestrates which agent handles the question."""
    
    # First check for casual conversation
    casual_reply = get_conversational_reply(question)
    if casual_reply:
        return casual_reply
    
    # Then check if relevant to data
    if not is_relevant_question(question, df):
        return "⚠️ That doesn't look like a data question. Try asking something like:\n- *Why did sales drop last month?*\n- *Compare region A vs region B*\n- *What makes up total revenue?*\n\n---\n📊 **Source:** No data was analysed for this response."

    intent = ask_orchestrator(question, df)
    
    if "ANALYSIS" in intent:
        return ask_analysis_agent(question, df)
    elif "COMPARISON" in intent:
        return ask_comparison_agent(question, df)
    elif "BREAKDOWN" in intent:
        return ask_breakdown_agent(question, df)
    else:
        return ask_summary_agent(question, df)