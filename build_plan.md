Hi, this is a solid hackathon to go after — right in the wheelhouse of building something practical with AI + data. Let me break down a detailed plan.
"Talk to Data" — Detailed Build Plan
Core Idea
A Python-based self-service data Q&A engine where users upload a CSV/Excel dataset, ask natural language questions, and get trustworthy, cited answers with zero SQL knowledge required.
Architecture Overview

```mermaid
graph TD
    A[User (Streamlit UI)] --> B(Query Router - intent classifier);
    B --> C["Semantic Layer (metric definitions, column glossary, business rules)"];
    C --> D("SQL/Pandas Code Generator (LLM)");
    D --> E("Execution Sandbox (safe eval)");
    E --> F("Result Validator (hallucination guard)");
    F --> G("Response Formatter (narrative + table/chart + citations)");
    G --> H("Chat History Manager (session context)");
```
Module-by-Module Plan
1. Data Ingestion & Profiling (src/data/)
When the user uploads a file, you auto-profile it: column names, types, null counts, unique values, sample rows. This profile becomes the "schema context" you feed the LLM. Store it in session state so every subsequent query has it. Support CSV and Excel to start — easy with pandas.
2. Semantic Layer / Metric Dictionary (src/semantic/)
This is your trust differentiator. Create a YAML/JSON config per dataset that defines: what "revenue" means (which column, any filters), what "active users" means, what "this month" resolves to, etc. The LLM references this dictionary before generating any code. If a user asks about "revenue" and your dictionary says revenue = sum(order_amount) where status != 'cancelled', the LLM uses that exact definition — no hallucination risk on metric meaning.
Auto-generate a starter dictionary from the data profile, let the user edit/confirm it.
3. Intent Classification (src/router/)
Classify every query into one of the 4 use cases from the problem statement:
Change analysis — "Why did X drop?"
Comparison — "A vs B", "this week vs last week"
Breakdown — "What makes up total X?"
Summary — "Give me a weekly summary"
Use a simple LLM prompt with few-shot examples. Each intent triggers a different code generation template, which massively reduces hallucination risk vs. a generic "do anything" prompt.
4. Code Generation & Execution (src/engine/)
The LLM generates pandas code (not raw SQL — simpler, safer, no DB needed). Key anti-hallucination measures:
Constrained generation: The prompt includes the exact column names, types, and metric definitions. The LLM can only reference columns that actually exist.
Template-guided: Each intent has a code template. For "breakdown", it's always a groupby + agg + sort. The LLM fills in the specifics, not invents the approach.
Sandboxed execution: Run generated code in a restricted exec() with only pandas/numpy in scope. No file I/O, no network, no os module. If it errors, catch it, feed the error back to the LLM for one retry.
Result validation: After execution, check — did the result dataframe have >0 rows? Do the numbers fall within the column's known min/max range? Does the sum of a breakdown match the total? If validation fails, flag it to the user instead of showing garbage.
5. Hallucination Guard System (src/guard/)
This is critical and worth calling out as a separate module:
Column existence check — reject any generated code referencing columns not in the dataset
Metric consistency check — verify the code matches the semantic layer definition
Numerical sanity check — result values should be within plausible bounds of the source data
Confidence scoring — if the query is ambiguous or the data doesn't have what's needed, say so explicitly ("I couldn't find a column related to 'customer satisfaction' in this dataset. Available metrics are: …")
Source citation — every answer includes which columns were used, what filters were applied, and the row count considered
6. Response Formatter (src/response/)
Every response has 3 layers (satisfies the "clarity" pillar):
Headline: One sentence plain-English answer ("Revenue dropped 11% in February")
Supporting detail: Table or chart (use matplotlib/plotly) + narrative explanation
Transparency footer: "Source: column order_amount, filtered by date >= 2024-02-01, 1,247 rows analyzed. Metric definition: revenue = sum(order_amount) where status ≠ cancelled"
7. Conversational Context (src/chat/)
Maintain chat history in Streamlit session state
The LLM sees the last 5 Q&A pairs for follow-up context ("what about the North region?" after a breakdown query)
Clarification flow: If the query is ambiguous, the system asks back before executing. Example: "By 'last month', did you mean March 2024 or the most recent complete month in the dataset (February 2024)?"
New chat / clear session button to reset context
8. Frontend (src/app.py — Streamlit)
File upload widget
Semantic layer editor (auto-generated, user-editable)
Chat interface with message history
Each response card shows: answer, chart (if applicable), data source citation, confidence indicator
Tech Stack
Layer
Tech
Frontend
Streamlit
LLM
Google Gemini free tier (or Groq free tier for Llama)
Data processing
Pandas, NumPy
Visualization
Plotly
Config/Semantic layer
YAML
Testing
pytest
Packaging
requirements.txt + .env.example
Folder Structure

```text
talk-to-data/
├── src/
│   ├── app.py              # Streamlit entry point
│   ├── data/
│   │   ├── loader.py        # CSV/Excel ingestion + profiling
│   │   └── profiler.py      # Auto-detect types, stats, samples
│   ├── semantic/
│   │   ├── layer.py         # Metric dictionary manager
│   │   └── templates/       # Default YAML configs
│   ├── router/
│   │   └── intent.py        # Query intent classification
│   ├── engine/
│   │   ├── generator.py     # LLM → pandas code
│   │   ├── executor.py      # Sandboxed execution
│   │   └── templates.py     # Per-intent code templates
│   ├── guard/
│   │   ├── validator.py     # Result validation
│   │   └── citation.py      # Source transparency builder
│   ├── response/
│   │   ├── formatter.py     # Narrative + chart + citation
│   │   └── charts.py        # Plotly chart generators
│   └── chat/
│       ├── history.py       # Session state manager
│       └── clarifier.py     # Ambiguity detection + follow-up
├── tests/
│   ├── test_loader.py
│   ├── test_intent.py
│   ├── test_generator.py
│   └── test_validator.py
├── assets/
│   └── sample_data.csv      # Demo dataset for judges
├── docs/
│   ├── architecture.md
│   └── semantic_layer.md
├── .env.example
├── requirements.txt
├── README.md
└── LICENSE                   # Apache 2.0
```

Anti-Hallucination Strategy (Summary)
Risk
Mitigation
LLM invents columns
Schema-constrained prompts + post-gen column check
Metric defined wrong
Semantic layer with locked definitions
Code errors silently
Sandboxed exec + error-retry loop
Numbers don't make sense
Range validation against source data
Ambiguous query
Clarification flow before execution
User trusts wrong answer
Confidence score + full citation on every response
Build Order (Priority)
Data loader + profiler (day 1 morning)
Basic LLM code generator with one intent (breakdown) — get end-to-end working
Streamlit chat UI with history
Add remaining 3 intents
Semantic layer + hallucination guards
Response formatting with charts + citations
Clarification flow
Tests + README + demo dataset
Polish + record demo