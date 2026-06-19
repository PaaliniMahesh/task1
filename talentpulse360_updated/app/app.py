"""
TalentPulse360 - Agentic AI Employee Assistant
Databricks Mosaic AI + Streamlit App
Updated: Chatbot-only mode, no sidebar navigation
"""

import streamlit as st
import yaml
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
PARENT_DIR = Path(__file__).parent.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TalentPulse360",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Hide sidebar completely ───────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="collapsedControl"] { display: none !important; }
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    header { display: none !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
</style>
""", unsafe_allow_html=True)

# ── Load config ───────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"
with open(CONFIG_PATH) as f:
    CFG = yaml.safe_load(f)

# ── Databricks SDK / Agent endpoint ──────────────────────────────────────────
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

_ws = WorkspaceClient()
ENDPOINT = CFG["agent"]["serving_endpoint"]


def call_agent(messages: list[dict]) -> str:
    """Call the Mosaic AI Agent serving endpoint."""
    try:
        sdk_messages = [
            ChatMessage(role=ChatMessageRole(m["role"]), content=m["content"])
            for m in messages
        ]
        resp = _ws.serving_endpoints.query(
            name=ENDPOINT,
            messages=sdk_messages,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"⚠️ Agent endpoint error: {str(e)}. Please ensure the endpoint '{ENDPOINT}' is deployed and accessible."


# ── Render chatbot only ───────────────────────────────────────────────────────
from app.pages.chatbot import render
render(call_agent)
