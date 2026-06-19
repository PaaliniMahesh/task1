"""
Page: TalentPulse360 Chatbot
Multi-agent routing with specialized agents per domain.
Sidebar hidden; clean full-screen chat UI.
"""
import streamlit as st
import re
import sys
import time
from pathlib import Path

parent_dir = Path(__file__).parent.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from tools.db_utils import run_query

# ── Agent definitions ─────────────────────────────────────────────────────────
AGENTS = {
    "attendance":   {"label": "Attendance Agent",   "icon": "📅", "color": "#3B7EF6"},
    "performance":  {"label": "Performance Agent",  "icon": "🏆", "color": "#F5A623"},
    "training":     {"label": "Training Agent",     "icon": "🎓", "color": "#10B981"},
    "skills":       {"label": "Skills Agent",       "icon": "🧩", "color": "#A855F7"},
    "employee360":  {"label": "360° Agent",         "icon": "🌐", "color": "#06B6D4"},
    "workforce":    {"label": "Workforce Agent",    "icon": "👥", "color": "#F97316"},
    "prediction":   {"label": "Prediction Agent",   "icon": "🤖", "color": "#EC4899"},
}

QUICK_PROMPTS = [
    ("📅", "Show attendance summary for Bhavani Shaganti"),
    ("🏆", "What is the performance score of Bhavani Shaganti?"),
    ("🎓", "Show training completion for Bhavani Shaganti"),
    ("🧩", "What skills does Bhavani Shaganti have?"),
    ("🌟", "Who are the top performers in AI/ML?"),
    ("🌐", "Show complete 360 profile for Bhavani Shaganti"),
    ("🚀", "Is Bhavani Shaganti ready for promotion?"),
    ("⚠️", "Show employees with low attendance"),
]

# ── Agent router ──────────────────────────────────────────────────────────────
def detect_agent(question: str) -> str:
    q = question.lower()
    if re.search(r"attendance|present|absent|wfh|leave|hours|check.?in|trend", q):
        return "attendance"
    if re.search(r"performance|kra|rating|score|band|manager.?rating|self.?rating|appraisal", q):
        return "performance"
    if re.search(r"train|course|learning|certif|completion|pending train", q):
        return "training"
    if re.search(r"skill|technolog|python|java|ml|ai|gap", q):
        return "skills"
    if re.search(r"360|complete.?profile|composite|health|risk", q):
        return "employee360"
    if re.search(r"top performer|low attend|rank|workforce|department|all employee|list of", q):
        return "workforce"
    if re.search(r"predict|forecast|next month|next quarter|promotion.?read|when.*promot", q):
        return "prediction"
    return "employee360"


# ── Extract employee name ─────────────────────────────────────────────────────
def extract_name(question: str):
    m = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', question)
    return m.group(0) if m else None


# ── Per-agent SQL answer functions ────────────────────────────────────────────

def attendance_answer(question: str, name: str) -> str:
    q = question.lower()

    if name:
        safe_name = name.replace("'", "''")

        if "wfh" in q:
            df = run_query(f"""
                SELECT employee_name, wfh_days
                FROM gold.talentpulse.gold_employee_360
                WHERE LOWER(employee_name) = LOWER('{safe_name}') LIMIT 1
            """)
            if df.empty: return f"❌ No WFH data found for {name}."
            r = df.iloc[0]
            return f"🏠 **{r['employee_name']}** has **{int(r['wfh_days'])} WFH days** recorded."

        if "hour" in q or "effective" in q:
            df = run_query(f"""
                SELECT employee_name, avg_effective_hours_per_day, total_effective_hours
                FROM gold.talentpulse.gold_employee_360
                WHERE LOWER(employee_name) = LOWER('{safe_name}') LIMIT 1
            """)
            if df.empty: return f"❌ No hours data for {name}."
            r = df.iloc[0]
            return f"⏱️ **{r['employee_name']}** — Avg: **{float(r['avg_effective_hours_per_day']):.1f} hrs/day** | Total: **{float(r['total_effective_hours']):.1f} hrs**"

        if "leave" in q:
            df = run_query(f"""
                SELECT employee_name, leave_days
                FROM gold.talentpulse.gold_employee_360
                WHERE LOWER(employee_name) = LOWER('{safe_name}') LIMIT 1
            """)
            if df.empty: return f"❌ No leave data for {name}."
            r = df.iloc[0]
            return f"🗓️ **{r['employee_name']}** has taken **{int(r['leave_days'])} leave days**."

        # Full attendance summary
        df = run_query(f"""
            SELECT employee_name, department, attendance_percentage,
                   present_days, leave_days, wfh_days,
                   avg_effective_hours_per_day, attendance_trend,
                   last_attendance_date, attendance_risk_flag
            FROM gold.talentpulse.gold_employee_360
            WHERE LOWER(employee_name) = LOWER('{safe_name}') LIMIT 1
        """)
        if df.empty: return f"❌ No attendance data found for {name}."
        r = df.iloc[0]
        pct = float(r['attendance_percentage'])
        grade = "🟢 Excellent" if pct > 90 else "🟡 Good" if pct > 80 else "🔴 Needs Attention"
        return f"""📅 **Attendance Summary — {r['employee_name']}**

- **Department**: {r['department']}
- **Attendance %**: {pct:.1f}% {grade}
- **Present Days**: {int(r['present_days'])} | **Leave**: {int(r['leave_days'])} | **WFH**: {int(r['wfh_days'])}
- **Avg Effective Hours**: {float(r['avg_effective_hours_per_day']):.1f} hrs/day
- **Trend**: {r['attendance_trend']} | **Last Date**: {r['last_attendance_date']}
- **Risk Flag**: {"⚠️ At Risk" if str(r['attendance_risk_flag']).lower() == 'true' else "✅ Normal"}"""

    # Low attendance workforce query
    if "low" in q or "risk" in q:
        df = run_query("""
            SELECT employee_name, department, attendance_percentage
            FROM gold.talentpulse.gold_employee_360
            WHERE attendance_percentage < 75
            ORDER BY attendance_percentage ASC LIMIT 10
        """)
        if df.empty: return "✅ No employees with low attendance!"
        rows = "\n".join([f"- **{r['employee_name']}** ({r['department']}) — {float(r['attendance_percentage']):.1f}%" for _, r in df.iterrows()])
        return f"⚠️ **Employees with Low Attendance (<75%)**\n\n{rows}"

    return "❓ Please specify an employee name or ask about low attendance employees."


def performance_answer(question: str, name: str) -> str:
    if not name:
        df = run_query("""
            SELECT employee_name, department, weighted_performance_score, performance_band
            FROM gold.talentpulse.gold_employee_360
            ORDER BY weighted_performance_score DESC LIMIT 10
        """)
        rows = "\n".join([f"{i+1}. **{r['employee_name']}** ({r['department']}) — {float(r['weighted_performance_score']):.2f} | {r['performance_band']}" for i, (_, r) in enumerate(df.iterrows())])
        return f"🏆 **Top Performers**\n\n{rows}"

    safe_name = name.replace("'", "''")
    df = run_query(f"""
        SELECT employee_name, department, weighted_performance_score, performance_band,
               avg_self_rating, avg_manager_rating, avg_final_rating,
               total_kras, top_performing_areas, improvement_areas
        FROM gold.talentpulse.gold_employee_360
        WHERE LOWER(employee_name) = LOWER('{safe_name}') LIMIT 1
    """)
    if df.empty: return f"❌ No performance data for {name}."
    r = df.iloc[0]
    return f"""🏆 **Performance Summary — {r['employee_name']}**

- **Department**: {r['department']}
- **Performance Score**: {float(r['weighted_performance_score']):.2f} | **Band**: {r['performance_band']}
- **Self Rating**: {float(r['avg_self_rating']):.2f} | **Manager Rating**: {float(r['avg_manager_rating']):.2f} | **Final**: {float(r['avg_final_rating']):.2f}
- **Total KRAs**: {int(r['total_kras'])}
- **Top Areas**: {r['top_performing_areas']}
- **Improvement Areas**: {r['improvement_areas']}"""


def training_answer(question: str, name: str) -> str:
    if not name:
        df = run_query("""
            SELECT employee_name, department, training_completion_percentage
            FROM gold.talentpulse.gold_employee_360
            WHERE training_completion_percentage < 60
            ORDER BY training_completion_percentage ASC LIMIT 10
        """)
        if df.empty: return "✅ All employees have good training completion!"
        rows = "\n".join([f"- **{r['employee_name']}** ({r['department']}) — {float(r['training_completion_percentage']):.1f}%" for _, r in df.iterrows()])
        return f"📚 **Employees Needing Training (<60% completion)**\n\n{rows}"

    safe_name = name.replace("'", "''")
    df = run_query(f"""
        SELECT employee_name, total_trainings_assigned, trainings_completed,
               training_completion_percentage, total_training_hours,
               training_risk_flag
        FROM gold.talentpulse.gold_employee_360
        WHERE LOWER(employee_name) = LOWER('{safe_name}') LIMIT 1
    """)
    if df.empty: return f"❌ No training data for {name}."
    r = df.iloc[0]
    pending = int(r['total_trainings_assigned']) - int(r['trainings_completed'])
    return f"""🎓 **Training Summary — {r['employee_name']}**

- **Assigned**: {int(r['total_trainings_assigned'])} | **Completed**: {int(r['trainings_completed'])} | **Pending**: {pending}
- **Completion %**: {float(r['training_completion_percentage']):.1f}%
- **Total Training Hours**: {float(r['total_training_hours']):.1f} hrs
- **Risk Flag**: {"⚠️ Training Risk" if str(r['training_risk_flag']).lower() == 'true' else "✅ On Track"}"""


def skills_answer(question: str, name: str) -> str:
    if not name:
        return "❓ Please specify an employee name to check skills."
    safe_name = name.replace("'", "''")
    df = run_query(f"""
        SELECT employee_name, designation, department, primary_skills
        FROM gold.talentpulse.gold_employee_360
        WHERE LOWER(employee_name) = LOWER('{safe_name}') LIMIT 1
    """)
    if df.empty: return f"❌ No skills data for {name}."
    r = df.iloc[0]
    return f"""🧩 **Skills Profile — {r['employee_name']}**

- **Role**: {r['designation']} | **Dept**: {r['department']}
- **Primary Skills**: {r['primary_skills']}

💡 For detailed skill gap analysis, compare against role-based requirements for {r['designation']}."""


def employee360_answer(question: str, name: str) -> str:
    if not name:
        return "❓ Please specify an employee name for a 360° profile."
    safe_name = name.replace("'", "''")
    df = run_query(f"""
        SELECT e.employee_name, e.department, e.designation, e.location,
               e.tenure_years, e.employment_type, e.manager_name,
               e.attendance_percentage, e.weighted_performance_score,
               e.training_completion_percentage, e.composite_talent_score,
               e.performance_band, e.employee_health_status,
               e.attendance_risk_flag, e.training_risk_flag, e.performance_risk_flag,
               p.promotion_readiness_status, p.promotion_readiness_score,
               p.recommended_next_designation, p.estimated_months_to_promotion
        FROM gold.talentpulse.gold_employee_360 e
        LEFT JOIN gold.talentpulse.gold_promotion_readiness p
          ON e.employee_id = p.employee_id
        WHERE LOWER(e.employee_name) = LOWER('{safe_name}') LIMIT 1
    """)
    if df.empty: return f"❌ No 360° profile found for {name}."
    r = df.iloc[0]
    return f"""🌐 **Employee 360° Profile — {r['employee_name']}**

- **Role**: {r['designation']} | **Dept**: {r['department']} | **Location**: {r['location']}
- **Manager**: {r['manager_name']} | **Tenure**: {float(r['tenure_years']):.1f} yrs | **Type**: {r['employment_type']}

📊 **Key Metrics**
- Attendance: **{float(r['attendance_percentage']):.1f}%** | Performance: **{float(r['weighted_performance_score']):.2f}** ({r['performance_band']})
- Training: **{float(r['training_completion_percentage']):.1f}%** | Talent Score: **{float(r['composite_talent_score']):.2f}**

🚨 **Risk Flags**: Attendance {"⚠️" if str(r['attendance_risk_flag']).lower()=="true" else "✅"} | Training {"⚠️" if str(r['training_risk_flag']).lower()=="true" else "✅"} | Performance {"⚠️" if str(r['performance_risk_flag']).lower()=="true" else "✅"}

🚀 **Promotion**: {r.get('promotion_readiness_status','N/A')} | Score: {float(r['promotion_readiness_score']):.1f} | Next Role: {r.get('recommended_next_designation','N/A')} (~{r.get('estimated_months_to_promotion','?')} months)
- **Health Status**: {r['employee_health_status']}"""


def workforce_answer(question: str, name: str) -> str:
    q = question.lower()
    if "top" in q and "performer" in q:
        df = run_query("""
            SELECT employee_name, department, designation,
                   weighted_performance_score, performance_band
            FROM gold.talentpulse.gold_employee_360
            ORDER BY weighted_performance_score DESC LIMIT 10
        """)
        rows = "\n".join([f"{i+1}. **{r['employee_name']}** ({r['department']}) — {float(r['weighted_performance_score']):.2f} | {r['performance_band']}" for i, (_, r) in enumerate(df.iterrows())])
        return f"🌟 **Top 10 Performers**\n\n{rows}"

    if "rank" in q or "ranking" in q:
        df = run_query("""
            SELECT employee_name, department, overall_rank, composite_talent_score,
                   ranking_category, performance_tier
            FROM gold.talentpulse.gold_employee_ranking
            ORDER BY overall_rank ASC LIMIT 10
        """)
        rows = "\n".join([f"{int(r['overall_rank'])}. **{r['employee_name']}** ({r['department']}) — Score: {float(r['composite_talent_score']):.2f} | {r['performance_tier']}" for _, r in df.iterrows()])
        return f"🏅 **Employee Rankings (Top 10)**\n\n{rows}"

    if "promotion" in q:
        df = run_query("""
            SELECT employee_name, department, promotion_readiness_status,
                   promotion_readiness_score, recommended_next_designation
            FROM gold.talentpulse.gold_promotion_readiness
            WHERE promotion_readiness_status IN ('Ready', 'High Potential')
            ORDER BY promotion_readiness_score DESC LIMIT 10
        """)
        if df.empty: return "📊 No employees currently marked as promotion-ready."
        rows = "\n".join([f"- **{r['employee_name']}** ({r['department']}) — {r['promotion_readiness_status']} → {r['recommended_next_designation']}" for _, r in df.iterrows()])
        return f"🚀 **Promotion-Ready Employees**\n\n{rows}"

    if "low" in q and "attend" in q:
        return attendance_answer(question, None)

    if "training" in q:
        return training_answer(question, None)

    # Department summary
    df = run_query("""
        SELECT department,
               COUNT(*) as headcount,
               ROUND(AVG(attendance_percentage),1) as avg_attendance,
               ROUND(AVG(weighted_performance_score),2) as avg_performance,
               ROUND(AVG(training_completion_percentage),1) as avg_training
        FROM gold.talentpulse.gold_employee_360
        GROUP BY department ORDER BY headcount DESC
    """)
    rows = "\n".join([f"- **{r['department']}**: {int(r['headcount'])} employees | Att: {r['avg_attendance']}% | Perf: {r['avg_performance']} | Training: {r['avg_training']}%" for _, r in df.iterrows()])
    return f"👥 **Workforce Department Summary**\n\n{rows}"


def prediction_answer(question: str, name: str) -> str:
    if not name:
        return "❓ Please specify an employee name for predictions."
    safe_name = name.replace("'", "''")

    df_ai = run_query(f"""
        SELECT employee_name, predicted_next_month_attendance,
               predicted_next_quarter_performance, prediction_confidence,
               composite_talent_score, attendance_risk, training_risk, performance_risk
        FROM gold.talentpulse.gold_employee_ai_features
        WHERE LOWER(employee_name) = LOWER('{safe_name}') LIMIT 1
    """)
    df_pr = run_query(f"""
        SELECT promotion_readiness_status, promotion_readiness_score,
               recommended_next_designation, estimated_months_to_promotion,
               tenure_gap, performance_gap, attendance_gap, training_gap
        FROM gold.talentpulse.gold_promotion_readiness
        WHERE LOWER(employee_name) = LOWER('{safe_name}') LIMIT 1
    """)

    if df_ai.empty: return f"❌ No prediction data for {name}."
    r = df_ai.iloc[0]
    result = f"""🤖 **AI Predictions — {r['employee_name']}**

- **Predicted Next Month Attendance**: {float(r['predicted_next_month_attendance']):.1f}%
- **Predicted Next Quarter Performance**: {float(r['predicted_next_quarter_performance']):.2f}
- **Prediction Confidence**: {r['prediction_confidence']}
- **Composite Talent Score**: {float(r['composite_talent_score']):.2f}
- **Risk Flags**: Attendance {"⚠️" if int(r['attendance_risk']) else "✅"} | Training {"⚠️" if int(r['training_risk']) else "✅"} | Performance {"⚠️" if int(r['performance_risk']) else "✅"}"""

    if not df_pr.empty:
        p = df_pr.iloc[0]
        result += f"""

🚀 **Promotion Readiness**
- **Status**: {p['promotion_readiness_status']} | **Score**: {float(p['promotion_readiness_score']):.1f}
- **Next Role**: {p['recommended_next_designation']} | **ETA**: {p['estimated_months_to_promotion']} months
- **Gaps**: Tenure: {p['tenure_gap'] or 'None'} | Performance: {p['performance_gap'] or 'None'} | Training: {p['training_gap'] or 'None'}"""

    return result


# ── Main answer dispatcher ─────────────────────────────────────────────────────
def answer_question(question: str) -> tuple[str, str]:
    """Returns (answer, agent_type)"""
    agent_type = detect_agent(question)
    name = extract_name(question)

    try:
        if agent_type == "attendance":
            return attendance_answer(question, name), agent_type
        elif agent_type == "performance":
            return performance_answer(question, name), agent_type
        elif agent_type == "training":
            return training_answer(question, name), agent_type
        elif agent_type == "skills":
            return skills_answer(question, name), agent_type
        elif agent_type == "employee360":
            return employee360_answer(question, name), agent_type
        elif agent_type == "workforce":
            return workforce_answer(question, name), agent_type
        elif agent_type == "prediction":
            return prediction_answer(question, name), agent_type
        else:
            return employee360_answer(question, name), "employee360"
    except Exception as e:
        return f"❌ **Database Error**: {str(e)}\n\nPlease verify your Databricks connection and table permissions.", agent_type


# ── Streamlit render ───────────────────────────────────────────────────────────
def render(call_agent_fn):
    # Custom CSS - dark professional theme, no sidebar
    st.markdown("""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

      html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

      /* Main background */
      .stApp { background: #0B0F1A !important; }
      .main .block-container { padding: 0 !important; max-width: 100% !important; }

      /* Hide all default Streamlit chrome */
      [data-testid="stSidebar"], [data-testid="collapsedControl"],
      #MainMenu, footer, header { display: none !important; }

      /* Header */
      .tp-header {
        background: #111827;
        border-bottom: 1px solid #1E2D45;
        padding: 14px 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        position: sticky; top: 0; z-index: 100;
      }
      .tp-logo {
        display: flex; align-items: center; gap: 12px;
      }
      .tp-logo-icon {
        width: 40px; height: 40px; border-radius: 10px;
        background: linear-gradient(135deg, #3B7EF6, #7C3AED);
        display: flex; align-items: center; justify-content: center;
        font-size: 20px;
      }
      .tp-title { font-size: 20px; font-weight: 700; color: #E8EDF5; margin: 0; }
      .tp-title span { color: #3B7EF6; }
      .tp-sub { font-size: 11px; color: #7B8FA8; margin: 0; letter-spacing: 0.3px; }

      /* Agent badge pill */
      .agent-badge {
        display: inline-flex; align-items: center; gap: 6px;
        padding: 3px 10px; border-radius: 20px;
        font-size: 11px; font-weight: 600;
        margin-bottom: 6px;
      }

      /* Chat messages */
      [data-testid="stChatMessage"] {
        background: transparent !important;
        border: none !important;
      }
      [data-testid="stChatMessageContent"] {
        background: #1A2235 !important;
        border: 1px solid #1E2D45 !important;
        border-radius: 4px 16px 16px 16px !important;
        padding: 12px 16px !important;
        color: #E8EDF5 !important;
        font-size: 13.5px !important;
        line-height: 1.6 !important;
      }
      [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
        background: #1E3A6E !important;
        border-color: #3B7EF640 !important;
        border-radius: 16px 4px 16px 16px !important;
      }

      /* Welcome screen */
      .welcome-container {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; padding: 40px 20px; text-align: center;
      }
      .quick-grid {
        display: grid; grid-template-columns: repeat(2,1fr);
        gap: 10px; max-width: 560px; margin: 0 auto;
      }
      .quick-btn {
        background: #1A2235; border: 1px solid #1E2D45;
        border-radius: 12px; padding: 14px 16px;
        color: #7B8FA8; font-size: 13px; cursor: pointer;
        text-align: left; display: flex; align-items: center; gap: 10px;
        transition: all 0.15s;
      }
      .quick-btn:hover {
        border-color: #3B7EF6; background: rgba(59,126,246,0.08); color: #E8EDF5;
      }

      /* Chat input */
      [data-testid="stChatInput"] {
        background: #111827 !important;
        border-top: 1px solid #1E2D45 !important;
        padding: 12px 16px !important;
      }
      [data-testid="stChatInput"] textarea {
        background: #1A2235 !important;
        border: 1px solid #1E2D45 !important;
        border-radius: 14px !important;
        color: #E8EDF5 !important;
        font-size: 14px !important;
        font-family: 'Inter', sans-serif !important;
      }
      [data-testid="stChatInput"] textarea::placeholder { color: #4A5E78 !important; }
      [data-testid="stChatInput"] button {
        background: linear-gradient(135deg, #3B7EF6, #7C3AED) !important;
        border-radius: 10px !important;
        border: none !important;
      }
    </style>
    """, unsafe_allow_html=True)

    # ── Header ──
    st.markdown("""
    <div class="tp-header">
      <div class="tp-logo">
        <div class="tp-logo-icon">🧠</div>
        <div>
          <p class="tp-title">TalentPulse<span>360</span></p>
          <p class="tp-sub">HR Intelligence Platform</p>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Session state ──
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None

    # ── Welcome screen (no messages yet) ──
    if not st.session_state.messages:
        st.markdown("""
        <div class="welcome-container">
          <div style="font-size:48px;margin-bottom:16px">🧠</div>
          <h2 style="color:#E8EDF5;font-size:24px;font-weight:700;margin:0 0 8px">How can I help you today?</h2>
          <p style="color:#7B8FA8;font-size:14px;max-width:400px;margin:0 0 28px">
            Ask about any employee — attendance, performance, training, skills, or workforce insights.
          </p>
        </div>
        """, unsafe_allow_html=True)

        # Quick action grid via columns
        cols = st.columns(2)
        for i, (icon, prompt) in enumerate(QUICK_PROMPTS):
            label = prompt.split("for")[0].strip() if "for" in prompt else prompt[:40]
            with cols[i % 2]:
                if st.button(f"{icon} {label}", key=f"quick_{i}", use_container_width=True):
                    st.session_state.pending_prompt = prompt
                    st.rerun()

    # ── Chat history ──
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and "agent_type" in msg:
                ag = AGENTS.get(msg["agent_type"], {"label": "TalentPulse AI", "icon": "✨", "color": "#3B7EF6"})
                st.markdown(
                    f'<div class="agent-badge" style="background:{ag["color"]}18;border:1px solid {ag["color"]}40;color:{ag["color"]}">'
                    f'{ag["icon"]} {ag["label"]}</div>',
                    unsafe_allow_html=True
                )
            st.markdown(msg["content"])

    # ── Quick chips row (when chat active) ──
    if st.session_state.messages:
        chip_cols = st.columns(5)
        chips = [
            ("📅", "Attendance", "Show attendance summary for Bhavani Shaganti"),
            ("🏆", "Performance", "Performance score of Bhavani Shaganti"),
            ("🎓", "Training", "Training status of Bhavani Shaganti"),
            ("🌟", "Top Performers", "Who are the top performers?"),
            ("🚀", "Promotion", "Promotion readiness of Bhavani Shaganti"),
        ]
        for i, (icon, label, prompt) in enumerate(chips):
            with chip_cols[i]:
                if st.button(f"{icon} {label}", key=f"chip_{i}", use_container_width=True):
                    st.session_state.pending_prompt = prompt
                    st.rerun()

    # ── Handle pending prompt ──
    user_input = st.chat_input("Ask about attendance, performance, training, skills...")

    if st.session_state.pending_prompt:
        user_input = st.session_state.pending_prompt
        st.session_state.pending_prompt = None

    if user_input:
        # Show user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Get answer from correct agent
        with st.chat_message("assistant"):
            with st.spinner(""):
                start = time.time()
                answer, agent_type = answer_question(user_input)
                elapsed = time.time() - start

            ag = AGENTS.get(agent_type, {"label": "TalentPulse AI", "icon": "✨", "color": "#3B7EF6"})
            st.markdown(
                f'<div class="agent-badge" style="background:{ag["color"]}18;border:1px solid {ag["color"]}40;color:{ag["color"]}">'
                f'{ag["icon"]} {ag["label"]} &nbsp;·&nbsp; {elapsed:.1f}s</div>',
                unsafe_allow_html=True
            )
            st.markdown(answer)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "agent_type": agent_type,
        })
        st.rerun()
