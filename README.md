# 📊 Talk to Data — Seamless Self-Service Intelligence

## Overview
Talk to Data is an AI-powered web application that lets anyone ask plain English questions about any dataset and instantly receive clear, trusted, and sourced answers. It removes the need for technical skills or complex tools — simply upload a CSV, type your question, and get an answer in seconds. Built for the NatWest Code for Purpose India Hackathon.

## Features
- Upload any CSV dataset and instantly profile it
- Ask natural language questions and get plain English answers
- Four specialised AI agents: Analysis, Comparison, Breakdown, and Summary
- Orchestrator agent automatically routes your question to the right agent
- Every answer includes a source reference showing which data was used
- Quick-action buttons for instant dataset summaries and trend detection
- Works with any CSV — fully self-service and reusable across datasets

## Install and Run Instructions

### Prerequisites
- Python 3.8 or higher
- A free Groq API key from https://console.groq.com

### Steps

1. Clone or download this repository

2. Install dependencies: pip install -r requirements.txt

3. Create a `.env` file in the root folder and add your Groq API key:         
    GROQ_API_KEY=your_api_key_here

4. Run the app: streamlit run app.py

5. Open your browser at `http://localhost:8501`

## Tech Stack
- **Language:** Python 3.12
- **Framework:** Streamlit
- **AI/ML:** Groq API (llama-3.3-70b-versatile model)
- **Data Processing:** Pandas
- **Environment Management:** python-dotenv

## Usage Examples

**Example questions you can ask:**
- "Why did revenue drop last month?"
- "Compare North region vs South region"
- "What makes up total revenue?"
- "Give me a weekly summary of this dataset"
- "What are the key trends?"

A sample dataset is provided in `sample_data/sales_data.csv` to test the app immediately.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    USER (Browser)                    │
│         Upload CSV  +  Type Question                 │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│                  app.py (UI Layer)                   │
│     Streamlit interface — renders everything         │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│              utils.py (Data Layer)                   │
│   Loads CSV → Profiles columns → Formats for AI     │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│          Orchestrator Agent (agents.py)              │
│     Reads question → Classifies intent               │
└──────┬──────────────┬──────────────┬───────┬────────┘
       │              │              │       │
       ▼              ▼              ▼       ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Analysis │  │Comparison│  │Breakdown │  │ Summary  │
│  Agent   │  │  Agent   │  │  Agent   │  │  Agent   │
│          │  │          │  │          │  │          │
│ Why did  │  │ Compare  │  │ What     │  │ Give me  │
│ X change?│  │ A vs B   │  │ makes    │  │ overview │
│          │  │          │  │ up total?│  │          │
└──────┬───┘  └──────┬───┘  └──────┬───┘  └──────┬───┘
       │              │              │              │
       └──────────────┴──────────────┴──────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────┐
│              Plain English Answer                    │
│     + Source reference (columns + rows used)        │
└─────────────────────────────────────────────────────┘
```

**Flow explanation:**
1. User uploads any CSV file and types a question in plain English
2. `utils.py` loads the CSV and builds a full profile of the data
3. The Orchestrator Agent reads the question and classifies the intent
4. The right specialist agent is called and analyses the dataset
5. A clear, sourced answer is returned and displayed in the browser

## Limitations
- Works best with structured CSV files with clear column headers
- Very large datasets (10,000+ rows) may slow down responses
- AI answers are based on dataset summaries, not live database queries

## Future Improvements
- Support for Excel and JSON file formats
- Chart and visualisation generation alongside text answers
- Chat history so users can ask follow-up questions
- Export answers as PDF reports
