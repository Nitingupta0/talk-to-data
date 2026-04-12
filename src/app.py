import streamlit as st
import pandas as pd
import os
import uuid
from dotenv import load_dotenv
import plotly.graph_objects as go

# --- CORE IMPORTS ---
from response.formatter import format_response, generate_welcome_message
from data.loader import load_and_profile
from chat.clarifier import check_for_ambiguity
from router.intent import classify_intent
from semantics.layers import get_semantic_layer
from engine.generator import generate_code
from engine.executor import execute_code

load_dotenv()

# ==========================================
# CUSTOM UI STYLING
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300&display=swap');

:root {
    --accent: #00D4AA;
    --accent-dim: rgba(0, 212, 170, 0.08);
    --accent-mid: rgba(0, 212, 170, 0.25);
    --accent-glow: rgba(0, 212, 170, 0.15);
    --purple: #7B61FF;
    --purple-dim: rgba(123, 97, 255, 0.08);
    --bg-deep: #080C14;
    --bg-card: #0F1623;
    --bg-elevated: #141D2E;
    --bg-hover: #1A2438;
    --border-subtle: rgba(255,255,255,0.05);
    --border-mid: rgba(255,255,255,0.08);
    --border-accent: rgba(0, 212, 170, 0.3);
    --text-primary: #EEF2FF;
    --text-secondary: #7A8BA0;
    --text-muted: #3D4F63;
    --user-bg: #0D1F35;
    --user-border: rgba(123, 97, 255, 0.35);
    --bot-bg: #0F1623;
    --bot-border: rgba(0, 212, 170, 0.15);
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
    background-color: var(--bg-deep) !important;
    color: var(--text-primary) !important;
}

.main .block-container {
    padding: 1.5rem 2.5rem 5rem !important;
    max-width: 900px !important;
}

::-webkit-scrollbar { width: 3px; height: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--accent-mid); border-radius: 4px; }

h1 {
    font-family: 'Syne', sans-serif !important;
    font-weight: 800 !important;
    font-size: 2rem !important;
    background: linear-gradient(120deg, #00D4AA 0%, #7B61FF 60%, #00D4AA 100%) !important;
    background-size: 200% auto !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    animation: shimmer 4s linear infinite !important;
    letter-spacing: -0.03em !important;
    margin-bottom: 0 !important;
}

@keyframes shimmer {
    0% { background-position: 0% center; }
    100% { background-position: 200% center; }
}

h2, h3 {
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
}

[data-testid="stSidebar"] {
    background: var(--bg-card) !important;
    border-right: 1px solid var(--border-subtle) !important;
}

[data-testid="stSidebar"] .block-container {
    padding: 1.25rem 0.875rem !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: 'Syne', sans-serif !important;
    font-size: 0.65rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    color: var(--text-muted) !important;
    -webkit-text-fill-color: var(--text-muted) !important;
    background: none !important;
    margin: 0.25rem 0 0.5rem !important;
}

.stButton > button {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border-mid) !important;
    color: var(--text-secondary) !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    padding: 0.45rem 0.875rem !important;
    transition: all 0.18s ease !important;
    width: 100% !important;
}

.stButton > button:hover {
    background: var(--accent-dim) !important;
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px var(--accent-glow) !important;
}

[data-testid="stFileUploader"] {
    background: var(--bg-deep) !important;
    border: 1.5px dashed var(--border-accent) !important;
    border-radius: 10px !important;
    padding: 0.25rem !important;
    transition: all 0.2s !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: var(--accent) !important;
    background: var(--accent-dim) !important;
}

[data-testid="stRadio"] > div {
    gap: 3px !important;
    display: flex !important;
    flex-direction: column !important;
}

[data-testid="stRadio"] label {
    background: var(--bg-deep) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 7px !important;
    padding: 0.45rem 0.75rem !important;
    font-size: 0.82rem !important;
    color: var(--text-secondary) !important;
    transition: all 0.15s ease !important;
    cursor: pointer !important;
}

[data-testid="stRadio"] label:hover {
    border-color: var(--border-accent) !important;
    background: var(--bg-hover) !important;
    color: var(--text-primary) !important;
}

[data-testid="stChatMessage"] {
    border-radius: 14px !important;
    padding: 1rem 1.25rem !important;
    margin-bottom: 0.6rem !important;
    border: 1px solid var(--border-subtle) !important;
    transition: border-color 0.2s !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background: var(--user-bg) !important;
    border-color: var(--user-border) !important;
    border-left: 3px solid var(--purple) !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background: var(--bot-bg) !important;
    border-color: var(--bot-border) !important;
    border-left: 3px solid var(--accent) !important;
}

[data-testid="stChatMessage"] p {
    line-height: 1.75 !important;
    font-size: 0.93rem !important;
    color: var(--text-primary) !important;
}

[data-testid="stChatMessage"] code {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border-mid) !important;
    border-radius: 4px !important;
    padding: 0.1em 0.35em !important;
    font-size: 0.82em !important;
    color: var(--text-primary) !important;
    font-family: 'DM Mono', 'Fira Code', monospace !important;
}

[data-testid="stChatInput"] {
    background: var(--bg-card) !important;
    border: 1.5px solid var(--border-mid) !important;
    border-radius: 14px !important;
    transition: all 0.2s !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-glow) !important;
}

[data-testid="stChatInput"] textarea {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important;
    color: var(--text-primary) !important;
    background: transparent !important;
}

[data-testid="stTextInput"] input {
    background: var(--bg-deep) !important;
    border: 1px solid var(--border-mid) !important;
    border-radius: 8px !important;
    color: var(--text-primary) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 0.85rem !important;
}

[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accent-glow) !important;
}

[data-testid="stExpander"] {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: 10px !important;
}

[data-testid="stExpander"]:hover {
    border-color: var(--border-accent) !important;
}

[data-testid="stExpander"] summary {
    font-size: 0.82rem !important;
    color: var(--text-secondary) !important;
    padding: 0.5rem 0.875rem !important;
    font-family: 'DM Sans', sans-serif !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--border-mid) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

[data-testid="stAlert"] {
    background: var(--accent-dim) !important;
    border: 1px solid var(--border-accent) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-size: 0.88rem !important;
}

[data-testid="stCaptionContainer"] p {
    color: var(--text-muted) !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.03em !important;
}

hr {
    border-color: var(--border-subtle) !important;
    margin: 0.6rem 0 !important;
}

.active-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--accent-dim);
    border: 1px solid var(--border-accent);
    color: var(--accent);
    border-radius: 20px;
    padding: 3px 14px;
    font-size: 0.75rem;
    font-weight: 500;
    letter-spacing: 0.04em;
    margin-bottom: 1rem;
    font-family: 'DM Sans', sans-serif;
}

.js-plotly-plot {
    border-radius: 12px !important;
    overflow: hidden !important;
    border: 1px solid var(--border-subtle) !important;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1. ATOMIC STATE INITIALIZATION
# ==========================================
if "datasets" not in st.session_state:
    st.session_state.datasets = {}
if "chats" not in st.session_state:
    init_id = str(uuid.uuid4())
    st.session_state.chats = {init_id: {"title": "New Chat", "history": [], "selected_files": []}}
    st.session_state.current_chat_id = init_id

# ==========================================
# 2. STATE CONTROLLERS
# ==========================================
def on_new_chat():
    new_id = str(uuid.uuid4())
    st.session_state.chats[new_id] = {
        "title": "New Chat",
        "history": [],
        "selected_files": []
    }
    st.session_state.current_chat_id = new_id

def on_delete_chat():
    curr_id = st.session_state.current_chat_id
    if len(st.session_state.chats) > 1:
        del st.session_state.chats[curr_id]
        st.session_state.current_chat_id = list(st.session_state.chats.keys())[0]
    else:
        init_id = str(uuid.uuid4())
        st.session_state.chats = {init_id: {"title": "New Chat", "history": [], "selected_files": []}}
        st.session_state.current_chat_id = init_id

# ==========================================
# 3. SIDEBAR
# ==========================================
with st.sidebar:
    st.button("➕ New Chat", on_click=on_new_chat, use_container_width=True)

    st.divider()
    st.header("🗂️ Chat Dataset")

    chat_specific_key = f"uploader_{st.session_state.current_chat_id}"

    files = st.file_uploader(
        "Upload data for this chat",
        type=["csv", "xlsx"],
        accept_multiple_files=True,
        key=chat_specific_key
    )

    active_chat = st.session_state.chats[st.session_state.current_chat_id]

    if files:
        for f in files:
            if f.name not in st.session_state.datasets:
                with st.spinner(f"Loading {f.name}..."):
                    df_l, prof_l = load_and_profile(f)
                    st.session_state.datasets[f.name] = {"df": df_l, "profile": prof_l}

        current_files = active_chat.get("selected_files", [])
        for f in files:
            if f.name not in current_files:
                current_files.append(f.name)
                active_chat["selected_files"] = current_files
                welcome_msg = generate_welcome_message(st.session_state.datasets[f.name]["profile"])
                multi_file_tip = ""
                if len(current_files) > 1:
                    multi_file_tip = "\n\n💡 **Tip:** I'll answer questions about each file independently. Say **'merge'**, **'combine'**, or **'for both files'** if you want me to analyse them together."
                active_chat["history"].append({
                    "role": "assistant",
                    "content": f"📂 **{f.name}** loaded!\n\n{welcome_msg}{multi_file_tip}"
                })
                st.rerun()

    st.divider()
    st.header("💬 Conversations")
    chat_list = list(st.session_state.chats.keys())
    chosen_id = st.radio(
        "History",
        options=chat_list,
        format_func=lambda x: st.session_state.chats[x]["title"],
        index=chat_list.index(st.session_state.current_chat_id),
        label_visibility="collapsed"
    )

    if chosen_id != st.session_state.current_chat_id:
        st.session_state.current_chat_id = chosen_id
        st.rerun()

    with st.expander("✏️ Rename Chat"):
        new_title = st.text_input(
            "New name",
            value=active_chat["title"],
            key=f"rename_{st.session_state.current_chat_id}",
            label_visibility="collapsed",
            placeholder="Enter new chat name..."
        )
        if st.button("✅ Save Name", use_container_width=True):
            active_chat["title"] = new_title
            st.rerun()

    st.button("🗑️ Delete Chat", on_click=on_delete_chat, use_container_width=True)

# ==========================================
# 4. INTENT KEYWORDS
# ==========================================
MERGE_KEYWORDS = [
    "merge", "combine", "together", "across files",
    "between files", "all datasets", "both datasets",
]

PER_FILE_KEYWORDS = [
    "both files", "all files", "both the files",
    "each file", "every file", "for both", "for each",
    "for all files", "both data", "both the data",
    "both csvs", "all csvs", "multiple files",
    "both the data files", "both data files",
    "for both files", "for all", "two files"
]

# ==========================================
# 5. MAIN CHAT AREA
# ==========================================
st.title("📊 Talk to Data")

active_id = st.session_state.current_chat_id
active_chat = st.session_state.chats[active_id]
active_files = active_chat.get("selected_files", [])
active_files = [f for f in active_files if f in st.session_state.datasets]

if active_files:

    # Show file badges
    if len(active_files) == 1:
        st.markdown(f"<div class='active-badge'>📂 {active_files[0]}</div>", unsafe_allow_html=True)
    else:
        badges = " ".join([f"<span class='active-badge'>📂 {f}</span>" for f in active_files])
        st.markdown(f"<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:1rem'>{badges}</div>", unsafe_allow_html=True)

    # Display chat history
    for i, msg in enumerate(active_chat["history"]):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("table"):
                with st.expander("📄 Data Table"):
                    st.markdown(msg["table"])
            if msg.get("chart"):
                fig = go.Figure(msg["chart"])
                st.plotly_chart(fig, width='stretch', key=f"c_{active_id}_{i}")
            for j, extra_chart in enumerate(msg.get("extra_charts", [])):
                if extra_chart:
                    fig = go.Figure(extra_chart)
                    st.plotly_chart(fig, width='stretch', key=f"ec_{active_id}_{i}_{j}")
            for j, extra_table in enumerate(msg.get("extra_tables", [])):
                if extra_table:
                    with st.expander(f"📄 Data Table {j + 2}"):
                        st.markdown(extra_table)

    # Chat input
    user_input = st.chat_input(f"Ask about: {', '.join(active_files)}")

    if user_input:
        if active_chat["title"] == "New Chat":
            active_chat["title"] = user_input[:25] + "..."
        active_chat["history"].append({"role": "user", "content": user_input})
        st.rerun()

    # ==========================================
    # 6. AI PROCESSOR
    # ==========================================
    if active_chat["history"] and active_chat["history"][-1]["role"] == "user":
        last_prompt = active_chat["history"][-1]["content"]
        last_prompt_lower = last_prompt.lower()

        # Determine intent from the CURRENT message
        should_merge = any(k in last_prompt_lower for k in MERGE_KEYWORDS)
        is_per_file = (
            len(active_files) > 1 and
            any(k in last_prompt_lower for k in PER_FILE_KEYWORDS) and
            not should_merge
        )

        print(f"DEBUG last_prompt: {last_prompt_lower}")
        print(f"DEBUG should_merge: {should_merge}")
        print(f"DEBUG is_per_file: {is_per_file}")
        print(f"DEBUG active_files: {active_files}")

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):

                if is_per_file:
                    # Process each file independently
                    all_narratives = []
                    all_charts = []
                    all_tables = []

                    for fname in active_files:
                        file_data = st.session_state.datasets[fname]
                        sem = get_semantic_layer(file_data["profile"])
                        intent, _ = classify_intent(last_prompt, file_data["profile"])
                        code, err = generate_code(
                            last_prompt, intent, file_data["profile"],
                            sem, chat_history=active_chat["history"]
                        )
                        if err:
                            all_narratives.append(f"⚠️ **{fname}:** {err}")
                            all_charts.append(None)
                            all_tables.append(None)
                        else:
                            res, exec_err = execute_code(code, file_data["df"])
                            if exec_err:
                                all_narratives.append(f"⚠️ **{fname}:** {exec_err}")
                                all_charts.append(None)
                                all_tables.append(None)
                            else:
                                final = format_response(res, last_prompt, intent)
                                all_narratives.append(f"**📂 {fname}**\n{final['narrative']}")
                                all_charts.append(final["chart"])
                                all_tables.append(final["table"])

                    print(f"DEBUG charts generated: {[c is not None for c in all_charts]}")

                    active_chat["history"].append({
                        "role": "assistant",
                        "content": "\n\n---\n\n".join(all_narratives),
                        "table": all_tables[0] if all_tables else None,
                        "chart": all_charts[0] if all_charts else None,
                        "extra_charts": all_charts[1:] if len(all_charts) > 1 else [],
                        "extra_tables": all_tables[1:] if len(all_tables) > 1 else []
                    })

                elif should_merge:
                    # Merge all files
                    combined_df = pd.concat(
                        [st.session_state.datasets[f]["df"] for f in active_files],
                        ignore_index=True
                    )
                    combined_profile = {
                        "columns": list(combined_df.columns),
                        "shape": combined_df.shape,
                        "dtypes": combined_df.dtypes.astype(str).to_dict(),
                        "sample": combined_df.head(3).to_dict(),
                        "sources": active_files
                    }
                    data_ref = {"df": combined_df, "profile": combined_profile}

                    is_vague, clarify = check_for_ambiguity(last_prompt, data_ref["profile"])
                    if is_vague:
                        active_chat["history"].append({"role": "assistant", "content": clarify})
                    else:
                        sem = get_semantic_layer(data_ref["profile"])
                        intent, _ = classify_intent(last_prompt, data_ref["profile"])
                        code, err = generate_code(last_prompt, intent, data_ref["profile"], sem, chat_history=active_chat["history"])
                        if err:
                            active_chat["history"].append({"role": "assistant", "content": f"⚠️ {err}"})
                        else:
                            res, exec_err = execute_code(code, data_ref["df"])
                            if exec_err:
                                active_chat["history"].append({"role": "assistant", "content": f"⚠️ {exec_err}"})
                            else:
                                final = format_response(res, last_prompt, intent)
                                active_chat["history"].append({
                                    "role": "assistant",
                                    "content": final["narrative"],
                                    "table": final["table"],
                                    "chart": final["chart"],
                                    "extra_charts": [],
                                    "extra_tables": []
                                })

                else:
                    # Single file — use most recently uploaded
                    data_ref = st.session_state.datasets[active_files[-1]]
                    is_vague, clarify = check_for_ambiguity(last_prompt, data_ref["profile"])
                    if is_vague:
                        active_chat["history"].append({"role": "assistant", "content": clarify})
                    else:
                        sem = get_semantic_layer(data_ref["profile"])
                        intent, _ = classify_intent(last_prompt, data_ref["profile"])
                        code, err = generate_code(last_prompt, intent, data_ref["profile"], sem, chat_history=active_chat["history"])
                        if err:
                            active_chat["history"].append({"role": "assistant", "content": f"⚠️ {err}"})
                        else:
                            res, exec_err = execute_code(code, data_ref["df"])
                            if exec_err:
                                active_chat["history"].append({"role": "assistant", "content": f"⚠️ {exec_err}"})
                            else:
                                final = format_response(res, last_prompt, intent)
                                active_chat["history"].append({
                                    "role": "assistant",
                                    "content": final["narrative"],
                                    "table": final["table"],
                                    "chart": final["chart"],
                                    "extra_charts": [],
                                    "extra_tables": []
                                })
        st.rerun()

else:
    st.info("👈 Upload one or more CSV/Excel files in the sidebar to get started!")