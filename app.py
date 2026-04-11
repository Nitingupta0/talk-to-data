import streamlit as st
import pandas as pd
from agents import route_question
from utils import load_dataset

# Initialize session state for history
if "history" not in st.session_state:
    st.session_state.history = []

st.set_page_config(
    page_title="Talk to Data",
    page_icon="logo.png",
    layout="centered"
)

# Custom CSS for better look
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        height: 3rem;
        font-size: 1rem;
        font-weight: 600;
    }
    .answer-box {
        background-color: #1e1e2e;
        border-left: 4px solid #7c3aed;
        border-radius: 8px;
        padding: 1.5rem;
        margin-top: 1rem;
    }
    .pillar-box {
        background-color: #1e1e2e;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        margin: 0.5rem 0;
    }
    .source-box {
        background-color: #2e2e3e;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        font-size: 0.85rem;
        color: #a0a0b0;
        margin-top: 1rem;
    }
    div[data-testid="stFileUploader"] {
        border: 2px dashed #7c3aed;
        border-radius: 12px;
        padding: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Header with optional logo
from PIL import Image
import os

col_logo, col_title = st.columns([1, 5])
with col_logo:
    try:
        logo = Image.open("logo.png")
        st.image(logo, width=70)
    except:
        pass
with col_title:
    st.markdown("<h1 style='margin-top:10px;'>Talk to Data</h1>", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("## 📖 How to use")
    st.markdown("""
    1. 📂 Upload any CSV file
    2. 💬 Type your question
    3. ⚡ Press **Enter** or click **Get Answer**
    """)
    st.markdown("---")
    st.markdown("### 💡 Example questions")
    st.markdown("""
    - Why did sales drop last month?
    - Compare region A vs region B
    - What makes up total revenue?
    - Give me a summary of this data
    - What are the key trends?
    """)
    st.markdown("---")
    st.markdown("### 🎯 Three pillars")
    st.markdown("🔍 **Clarity** — Simple English answers")
    st.markdown("✅ **Trust** — Always shows data source")
    st.markdown("⚡ **Speed** — Answer in seconds")
    st.markdown("---")
    st.caption("Built for NatWest Code for Purpose Hackathon 2025")
    
    # Question history
    st.markdown("---")
    st.markdown("### 🕘 Question History")
    
    if len(st.session_state.history) == 0:
        st.caption("No questions asked yet.")
    else:
        # Clear history button
        if st.button("🗑️ Clear History", use_container_width=True):
            st.session_state.history = []
            st.rerun()
        
        # Show history in reverse (latest first)
        for i, item in enumerate(reversed(st.session_state.history)):
            with st.expander(f"Q: {item['question'][:40]}{'...' if len(item['question']) > 40 else ''}"):
                st.markdown(f"**Question:** {item['question']}")
                st.markdown("**Answer:**")
                st.markdown(item['answer'])
                if item['source']:
                    st.caption(item['source'])

# File upload section
st.markdown("### 📂 Step 1 — Upload your dataset")
uploaded_file = st.file_uploader(
    "Drag and drop or browse a CSV file",
    type=["csv"],
    help="Upload any CSV file — the app will automatically understand its structure"
)

if uploaded_file is not None:
    df = load_dataset(uploaded_file)

    # Success message with stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 Rows", len(df))
    with col2:
        st.metric("📊 Columns", len(df.columns))
    with col3:
        st.metric("✅ Status", "Ready")

    # Data preview tabs
    tab1, tab2 = st.tabs(["👀 Data Preview", "📋 Column Info"])
    with tab1:
        st.dataframe(df.head(10), use_container_width=True)
    with tab2:
        col_info = pd.DataFrame({
            "Column": df.columns,
            "Type": df.dtypes.values,
            "Non-null count": df.count().values,
            "Sample value": [
                df[col].dropna().iloc[0]
                if len(df[col].dropna()) > 0 else "N/A"
                for col in df.columns
            ]
        })
        st.dataframe(col_info, use_container_width=True)

    st.markdown("---")

    # Question section with Enter key support
    st.markdown("### 💬 Step 2 — Ask your question")

    with st.form(key="question_form", clear_on_submit=True):
        question = st.text_input(
            "Type your question here",
            placeholder="e.g. Why did revenue drop last month?",
            label_visibility="collapsed"
        )
        submitted = st.form_submit_button("🔍 Get Answer", type="primary", use_container_width=True)

    if submitted:
        if question.strip() == "":
            st.warning("⚠️ Please type a question first.")
        else:
            with st.spinner("🤔 Analysing your data..."):
                try:
                    full_answer = route_question(question, df)

                    # Split answer from source reference
                    parts = full_answer.split("\n\n---\n")
                    answer_text = parts[0]
                    source_text = parts[1] if len(parts) > 1 else ""

                    # Save to history
                    st.session_state.history.append({
                        "question": question,
                        "answer": answer_text,
                        "source": source_text
                    })

                    st.markdown("---")
                    st.markdown("### 💡 Answer")
                    st.markdown(f"""
                    <div class='answer-box'>
                        {answer_text}
                    </div>
                    """, unsafe_allow_html=True)

                    if source_text:
                        st.markdown(f"""
                        <div class='source-box'>
                            {source_text}
                        </div>
                        """, unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"❌ Something went wrong: {str(e)}")

    st.markdown("---")

    # Quick question buttons
    st.markdown("### ⚡ Quick questions")
    st.caption("Click any button below to instantly analyse your dataset")

    quick_questions = [
        ("📈 Summarise this dataset",       "Give me a concise summary of this dataset"),
        ("🔍 What are the key trends?",      "What are the key trends in this dataset?"),
        ("⚠️ Any anomalies or outliers?",    "Are there any anomalies or outliers in this dataset?"),
        ("🏆 What are the top performers?",  "What are the top performing categories or values in this dataset?"),
        ("📉 What needs attention?",         "What areas or values in this dataset need attention or are underperforming?"),
    ]

    # Row 1 — 3 buttons
    col1, col2, col3 = st.columns(3)
    cols_row1 = [col1, col2, col3]
    for i in range(3):
        with cols_row1[i]:
            label, query = quick_questions[i]
            if st.button(label, use_container_width=True, key=f"quick_{i}"):
                with st.spinner("🤔 Analysing..."):
                    full_answer = route_question(query, df)
                    parts = full_answer.split("\n\n---\n")
                    st.markdown("### 💡 Answer")
                    st.markdown(f"<div class='answer-box'>{parts[0]}</div>", unsafe_allow_html=True)
                    if len(parts) > 1:
                        st.markdown(f"<div class='source-box'>{parts[1]}</div>", unsafe_allow_html=True)

    # Row 2 — 2 buttons
    col4, col5 = st.columns(2)
    cols_row2 = [col4, col5]
    for i in range(2):
        with cols_row2[i]:
            label, query = quick_questions[i + 3]
            if st.button(label, use_container_width=True, key=f"quick_{i+3}"):
                with st.spinner("🤔 Analysing..."):
                    full_answer = route_question(query, df)
                    parts = full_answer.split("\n\n---\n")
                    st.markdown("### 💡 Answer")
                    st.markdown(f"<div class='answer-box'>{parts[0]}</div>", unsafe_allow_html=True)
                    if len(parts) > 1:
                        st.markdown(f"<div class='source-box'>{parts[1]}</div>", unsafe_allow_html=True)
else:
    # Landing state — no file uploaded yet
    st.info("👆 Upload a CSV file above to get started.")
    st.markdown("---")
    st.markdown("### 🚀 What can you ask?")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class='pillar-box'>
            <h3>📉 Analysis</h3>
            <p style='color:#a0a0b0'>"Why did revenue drop last month?"</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class='pillar-box'>
            <h3>🔀 Comparison</h3>
            <p style='color:#a0a0b0'>"Compare North vs South region"</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class='pillar-box'>
            <h3>🧩 Breakdown</h3>
            <p style='color:#a0a0b0'>"What makes up total revenue?"</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div class='pillar-box'>
            <h3>📋 Summary</h3>
            <p style='color:#a0a0b0'>"Give me a weekly summary"</p>
        </div>
        """, unsafe_allow_html=True)