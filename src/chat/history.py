import streamlit as st

def init_chat():
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

def append_message(role, content, chart=None):
    msg = {"role": role, "content": content}
    if chart:
        msg["chart"] = chart
    st.session_state.chat_history.append(msg)

def get_recent_context(n=5):
    """Returns the last n messages to feed back to the LLM for memory."""
    if "chat_history" in st.session_state:
        return st.session_state.chat_history[-n:]
    return []