"""
streamlit_app.py
─────────────────────────────────────────────────────────────────────────────
Employee360 AI — Streamlit Chatbot Application

Run locally:
    streamlit run streamlit_app.py

Deploy on Databricks:
    1. Upload project to Databricks workspace (Repos)
    2. Create a Databricks App → point to streamlit_app.py
    3. Set environment variables:
       - ANTHROPIC_API_KEY
       - DATABRICKS_HTTP_PATH
       - DATABRICKS_HOST  (auto-set inside Databricks)
       - DATABRICKS_TOKEN (auto-set inside Databricks)
─────────────────────────────────────────────────────────────────────────────
"""

import os
import time

import streamlit as st

# ── Page configuration (must be first Streamlit call) ────────────────────────
st.set_page_config(
    page_title="Employee360 AI",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── App shell ── */
.main .block-container { padding-top: 1.2rem; padding-bottom: 1rem; max-width: 1100px; }
section[data-testid="stSidebar"] { background: #0f2744; min-width: 270px; }
section[data-testid="stSidebar"] * { color: #cbd5e1 !important; }

/* ── Sidebar logo card ── */
.logo-card {
    background: #1e3a5f;
    border: 1px solid #2d5a8a;
    border-radius: 10px;
    padding: 14px 16px;
    margin-bottom: 16px;
}
.logo-card h2 { color: #e2eaf6 !important; font-size: 17px; font-weight: 600; margin: 0 0 3px 0; }
.logo-card p  { color: #6b8cba !important; font-size: 11px; margin: 0; }

/* ── Sidebar stat cards ── */
.stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 7px; margin-bottom: 16px; }
.s-card { background: #1e3a5f; border: 1px solid #2d5a8a; border-radius: 8px; padding: 9px 11px; }
.s-card .s-val  { font-size: 22px; font-weight: 600; margin: 0; }
.s-card .s-lbl  { font-size: 10px; color: #6b8cba !important; margin: 0; }
.s-green  { color: #4ade80 !important; }
.s-orange { color: #fb923c !important; }
.s-blue   { color: #60a5fa !important; }
.s-white  { color: #e2eaf6 !important; }

/* ── Sidebar section label ── */
.sidebar-label {
    font-size: 10px; font-weight: 600; letter-spacing: 0.08em;
    color: #4b7aab !important; text-transform: uppercase;
    margin: 0 0 8px 0;
}

/* ── Quick action buttons ── */
div[data-testid="stButton"] > button {
    background: #1e3a5f !important;
    border: 1px solid #2d5a8a !important;
    color: #94b8d8 !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    padding: 7px 12px !important;
    text-align: left !important;
    width: 100% !important;
    margin-bottom: 3px !important;
    transition: all 0.15s !important;
}
div[data-testid="stButton"] > button:hover {
    background: #1d4ed8 !important;
    border-color: #3b82f6 !important;
    color: #bfdbfe !important;
}

/* ── Header banner ── */
.header-banner {
    background: #0f2744;
    border: 1px solid #1e3a5f;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 14px;
}
.header-banner h1 { color: #e2eaf6; font-size: 20px; font-weight: 600; margin: 0 0 3px 0; }
.header-banner p  { color: #6b8cba; font-size: 12px; margin: 0; }
.live-dot { width: 8px; height: 8px; border-radius: 50%; background: #22c55e; display: inline-block; margin-right: 6px; }
.live-tag { background: #14532d; color: #86efac; font-size: 10px; font-weight: 600; padding: 3px 9px; border-radius: 99px; display: inline-flex; align-items: center; }

/* ── Chat messages ── */
.stChatMessage { border-radius: 12px !important; }

/* ── Profile card ── */
.profile-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 14px 16px;
    margin: 8px 0;
    font-size: 13px;
}
.profile-card h4 { font-size: 15px; font-weight: 600; margin: 0 0 10px 0; color: #0f172a; }
.prow { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #f1f5f9; }
.prow:last-child { border-bottom: none; }
.pkey { color: #64748b; }
.pval { font-weight: 500; color: #0f172a; }
.prog-wrap { margin: 6px 0; }
.prog-label { font-size: 11px; color: #64748b; margin-bottom: 3px; display: flex; justify-content: space-between; }
.prog-track { background: #e2e8f0; border-radius: 99px; height: 7px; overflow: hidden; }
.prog-fill-green  { background: #22c55e; height: 7px; border-radius: 99px; }
.prog-fill-blue   { background: #3b82f6; height: 7px; border-radius: 99px; }
.prog-fill-orange { background: #f59e0b; height: 7px; border-radius: 99px; }
.prog-fill-purple { background: #8b5cf6; height: 7px; border-radius: 99px; }
.tag { display: inline-block; font-size: 10px; padding: 2px 8px; border-radius: 99px; font-weight: 600; margin: 2px; }
.tag-ok   { background: #dcfce7; color: #166534; }
.tag-warn { background: #fef3c7; color: #92400e; }
.tag-err  { background: #fee2e2; color: #991b1b; }
.tag-info { background: #dbeafe; color: #1e40af; }
.tag-gray { background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; }

/* ── Section header ── */
.sec-hd { font-size: 11px; font-weight: 600; letter-spacing: 0.06em; color: #64748b; text-transform: uppercase; margin: 10px 0 5px 0; }

/* ── Footer ── */
.app-footer {
    text-align: center; font-size: 11px; color: #94a3b8;
    padding: 12px 0 4px 0; border-top: 1px solid #f1f5f9; margin-top: 8px;
}

/* ── Chat input box ── */
.stChatInput { border-radius: 10px !important; }
.stChatInput textarea { font-size: 14px !important; }
</style>
""", unsafe_allow_html=True)


# ── Detect environment ────────────────────────────────────────────────────────
_INSIDE_DATABRICKS = bool(os.getenv("DATABRICKS_RUNTIME_VERSION"))


# ── Initialise orchestrator (cached — runs once per app session) ──────────────
@st.cache_resource(show_spinner="Connecting to Databricks Gold Layer...")
def load_orchestrator():
    from src.agents import Employee360Orchestrator
    return Employee360Orchestrator(
        use_spark=_INSIDE_DATABRICKS,
        enable_rag=True,
        enable_mlflow=_INSIDE_DATABRICKS,
    ).initialize()


orch = load_orchestrator()


# ── Session state defaults ────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "👋 Hello! I'm **Employee360 AI** — your Agentic Workforce "
                "Intelligence Assistant built on Databricks.\n\n"
                "I have access to **7 Gold tables** in `gold.talentpulse` covering "
                "attendance, training, performance, ranking, and promotion data for "
                "**150 employees** across 10 departments.\n\n"
                "Ask me anything — type below or click a quick action on the left!"
            ),
        }
    ]

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:

    # Logo
    st.markdown("""
    <div class="logo-card">
        <h2>🧠 Employee360 AI</h2>
        <p>Agentic Workforce Intelligence<br>Databricks · gold.talentpulse</p>
    </div>
    """, unsafe_allow_html=True)

    # Workforce stats
    st.markdown('<p class="sidebar-label">Workforce snapshot</p>', unsafe_allow_html=True)
    st.markdown("""
    <div class="stat-grid">
        <div class="s-card"><p class="s-val s-white">150</p><p class="s-lbl">👥 Total employees</p></div>
        <div class="s-card"><p class="s-val s-green">60</p><p class="s-lbl">✅ On track</p></div>
        <div class="s-card"><p class="s-val s-orange">90</p><p class="s-lbl">⚠️ At risk</p></div>
        <div class="s-card"><p class="s-val s-blue">45</p><p class="s-lbl">🚀 Promo ready</p></div>
        <div class="s-card"><p class="s-val s-blue">10</p><p class="s-lbl">🏢 Departments</p></div>
        <div class="s-card"><p class="s-val s-white">7</p><p class="s-lbl">🗃️ Gold tables</p></div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Quick actions
    st.markdown('<p class="sidebar-label">Quick actions</p>', unsafe_allow_html=True)

    QUICK_ACTIONS = [
        ("👤  Mahesh — full profile",           "Show me the complete Employee360 profile for Mahesh Paalini"),
        ("🚀  Is Mahesh promotion ready?",       "Is Mahesh Paalini ready for promotion? What gaps does he need to close?"),
        ("📅  Mahesh attendance summary",        "Show Mahesh Paalini's attendance summary and trends"),
        ("📚  Mahesh training status",           "What is Mahesh Paalini's training completion status?"),
        ("🏆  Top 10 performers",                "Who are the top 10 performers in the organisation?"),
        ("⚠️  At-risk employees",               "Which employees are at risk and need immediate HR intervention?"),
        ("🎯  Promotion-ready list",             "Show me all employees who are nearly ready for promotion"),
        ("🤖  AI predictions",                   "Which employees are predicted to have attendance issues next month?"),
        ("📊  AI/ML dept overview",              "Give me a complete performance overview of the AI/ML department"),
        ("🧭  Databricks role transition",       "Which employees can transition to a Databricks Data Engineer role and what are their gaps?"),
        ("📋  Workforce health dashboard",       "Give me a workforce health dashboard — overall stats and department breakdown"),
        ("📉  Training gaps",                    "Which employees have pending training completion across all departments?"),
        ("🌍  WFH utilisation analysis",         "Show me the WFH utilisation analysis across all departments"),
        ("⭐  Top performers — HR dept",         "Who are the top performers in the HR department?"),
        ("📈  Promotion pipeline — DE dept",     "Show me the promotion pipeline for the Data Engineering department"),
    ]

    for label, query in QUICK_ACTIONS:
        if st.button(label, key=f"qa_{label}", use_container_width=True):
            st.session_state.pending_query = query

    st.divider()

    # Architecture info
    with st.expander("🏗️ Architecture", expanded=False):
        st.markdown("""
        <div style="font-size:11px; color:#94b8d8; line-height:1.7">
        <b style="color:#e2eaf6">Medallion Architecture</b><br>
        Bronze → Silver → Gold<br><br>
        <b style="color:#e2eaf6">Gold Tables</b><br>
        employee_360<br>
        employee_attendance_summary<br>
        employee_training_summary<br>
        employee_performance_summary<br>
        employee_ranking<br>
        promotion_readiness<br>
        employee_ai_features<br><br>
        <b style="color:#e2eaf6">AI Stack</b><br>
        Claude Sonnet 4.6 · LangChain<br>
        RAG · MLflow · ChromaDB
        </div>
        """, unsafe_allow_html=True)

    # Clear chat
    st.divider()
    if st.button("🗑️  Clear conversation", use_container_width=True):
        st.session_state.messages = [st.session_state.messages[0]]
        orch.reset_history()
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────────────────────────────────────

# Header banner
st.markdown("""
<div class="header-banner">
    <span style="font-size:32px">🧠</span>
    <div style="flex:1">
        <h1>Employee360 AI &nbsp; <span class="live-tag"><span class="live-dot"></span>Live</span></h1>
        <p>Agentic Workforce Intelligence &nbsp;·&nbsp; Databricks gold.talentpulse
           &nbsp;·&nbsp; 7 Gold Tables &nbsp;·&nbsp; 150 Employees &nbsp;·&nbsp;
           Claude Sonnet 4.6 &nbsp;·&nbsp; RAG enabled</p>
    </div>
</div>
""", unsafe_allow_html=True)


# ── Helper: Format assistant response as rich HTML ────────────────────────────
def format_response(text: str) -> str:
    """
    Convert markdown-style text from the agent into clean HTML
    for display inside st.markdown with unsafe_allow_html=True.
    """
    import re

    lines = text.split("\n")
    html_parts = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            html_parts.append("<div style='height:6px'></div>")
            continue

        # Headings
        if stripped.startswith("### "):
            content = stripped[4:]
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
            html_parts.append(
                f"<div style='font-size:14px;font-weight:600;color:var(--text-color);"
                f"margin-top:12px;margin-bottom:3px'>{content}</div>"
            )
        elif stripped.startswith("## "):
            content = stripped[3:]
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
            html_parts.append(
                f"<div style='font-size:15px;font-weight:600;color:var(--text-color);"
                f"margin-top:14px;margin-bottom:4px'>{content}</div>"
            )
        elif stripped.startswith("# "):
            content = stripped[2:]
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
            html_parts.append(
                f"<div style='font-size:16px;font-weight:700;color:var(--text-color);"
                f"margin-top:16px;margin-bottom:4px'>{content}</div>"
            )
        # Bullet points
        elif stripped.startswith(("- ", "• ", "* ")):
            content = stripped[2:]
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
            html_parts.append(
                f"<div style='display:flex;gap:8px;margin-top:3px;padding-left:4px;font-size:13px'>"
                f"<span style='color:#94a3b8;flex-shrink:0'>·</span>"
                f"<span>{content}</span></div>"
            )
        # Numbered list
        elif re.match(r'^\d+\.', stripped):
            content = re.sub(r'^\d+\.\s*', '', stripped)
            num = re.match(r'^(\d+)\.', stripped).group(1)
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
            html_parts.append(
                f"<div style='display:flex;gap:8px;margin-top:4px;padding-left:4px;font-size:13px'>"
                f"<span style='color:#94a3b8;flex-shrink:0;min-width:16px'>{num}.</span>"
                f"<span>{content}</span></div>"
            )
        # Horizontal rule
        elif stripped in ("---", "***", "___"):
            html_parts.append("<hr style='border:none;border-top:1px solid #e2e8f0;margin:10px 0'>")
        # Regular paragraph
        else:
            content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', stripped)
            # Inline code
            content = re.sub(
                r'`(.*?)`',
                r'<code style="background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:12px">\1</code>',
                content
            )
            html_parts.append(
                f"<div style='font-size:13px;line-height:1.6;margin-top:2px'>{content}</div>"
            )

    return "\n".join(html_parts)


# ── Render existing chat messages ─────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(
        msg["role"],
        avatar="🧠" if msg["role"] == "assistant" else "👤",
    ):
        if msg["role"] == "assistant":
            st.markdown(format_response(msg["content"]), unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])


# ── Handle quick-action button click ─────────────────────────────────────────
def process_query(user_input: str):
    """Send a query, stream the response, update session state."""
    # Show user message
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Show assistant typing
    with st.chat_message("assistant", avatar="🧠"):
        placeholder = st.empty()
        placeholder.markdown(
            "<div style='color:#94a3b8;font-size:13px'>⏳ Querying Gold Layer and generating response...</div>",
            unsafe_allow_html=True,
        )
        try:
            start = time.time()
            response = orch.chat(user_input)
            elapsed = time.time() - start
            placeholder.markdown(format_response(response), unsafe_allow_html=True)
            st.caption(f"⚡ Responded in {elapsed:.1f}s · gold.talentpulse · Claude Sonnet 4.6")
        except Exception as e:
            response = f"⚠️ Something went wrong: {e}"
            placeholder.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})


# Process a queued quick-action query
if st.session_state.pending_query:
    query = st.session_state.pending_query
    st.session_state.pending_query = None
    process_query(query)

# ── Chat input (bottom bar) ───────────────────────────────────────────────────
user_input = st.chat_input(
    placeholder='Ask anything — "Show Mahesh\'s full profile" or "Who needs training support?"'
)

if user_input:
    process_query(user_input)


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-footer">
    Employee360 AI &nbsp;·&nbsp; Databricks Medallion Architecture &nbsp;·&nbsp;
    gold.talentpulse &nbsp;·&nbsp; Claude Sonnet 4.6 &nbsp;·&nbsp;
    LangChain · RAG · MLflow
</div>
""", unsafe_allow_html=True)
