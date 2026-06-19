# Employee360 AI — Streamlit on Databricks

> Conversational workforce analytics powered by Databricks Gold Layer + Claude AI

---

## Project Structure

```
employee360_streamlit/
├── streamlit_app.py              ← Main Streamlit app (entry point)
├── config.py                     ← Configuration & environment variables
├── requirements.txt              ← Dependencies (streamlit + langchain + databricks)
├── .env.example                  ← Environment variable template
├── .streamlit/
│   └── config.toml               ← Streamlit theme & server settings
├── src/
│   ├── __init__.py
│   ├── agents.py                 ← Multi-agent orchestrator + intent router
│   ├── db_connector.py           ← All 7 Gold table SQL queries
│   ├── tools.py                  ← 20 LangChain tools
│   └── rag/
│       ├── __init__.py
│       └── rag_pipeline.py       ← HR knowledge base (ChromaDB / Databricks VS)
└── notebooks/
    └── employee360_streamlit_demo.py  ← Databricks notebook
```

---

## Quick Start

```bash
# 1. Clone and install
git clone ...
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Fill in ANTHROPIC_API_KEY and Databricks credentials

# 3. Run
streamlit run streamlit_app.py
# Open http://localhost:8501
```

---

## Deploy on Databricks App

1. Upload repo to Databricks workspace (Repos)
2. Go to **Compute → Apps → Create App**
3. Select **Streamlit**
4. Point to `streamlit_app.py`
5. Add env vars: `ANTHROPIC_API_KEY`, `DATABRICKS_HTTP_PATH`
6. Deploy

---

## What's in the UI

| Section | Description |
|---------|-------------|
| Dark sidebar | Logo, 6 stat cards, 15 quick-action buttons, architecture info |
| Header banner | App title + live status + connection details |
| Chat area | `st.chat_message` bubbles with rich HTML formatting |
| Bottom input | `st.chat_input` — type or use quick actions |
| Per-response | Response time + model info as caption |

---

## Gold Tables Used

| Table | Purpose |
|-------|---------|
| `employee_360` | Master 360 view |
| `employee_attendance_summary` | Attendance, WFH, effective hours |
| `employee_training_summary` | Training completion & progress |
| `employee_performance_summary` | KRA ratings, feedback |
| `employee_ranking` | Org-wide and dept rankings |
| `promotion_readiness` | Readiness score, gaps, timeline |
| `employee_ai_features` | ML predictions |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | Streamlit 1.40 |
| LLM | Claude Sonnet 4.6 (Anthropic) |
| Agents | LangChain |
| Data | Databricks Unity Catalog (PySpark / SQL Connector) |
| RAG | ChromaDB + sentence-transformers |
| Tracking | MLflow |
