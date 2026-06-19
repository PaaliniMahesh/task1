"""Page: Skill Gap Analysis"""
import streamlit as st
import plotly.express as px
from tools.db_utils import run_query


def render():
    st.title("🧩 Skill Gap Analysis")

    employee_name = st.text_input("Employee Name", placeholder="e.g. Mahesh")
    target_role   = st.text_input("Target Role (optional)", placeholder="e.g. Databricks Data Engineer")

    if not employee_name:
        # Show department-level gap heatmap
        sql = """
            SELECT department,
                   AVG(skill_gap_score)    AS avg_gap,
                   AVG(skill_score)        AS avg_skill_score,
                   COUNT(*)               AS headcount
            FROM gold.talentpulse.gold_employee_ai_features
            GROUP BY department ORDER BY avg_gap DESC
        """
        df = run_query(sql)
        if not df.empty:
            st.subheader("Department Skill Gap Overview")
            fig = px.bar(df, x="department", y="avg_gap",
                         color="avg_gap", color_continuous_scale="RdYlGn_r",
                         title="Average Skill Gap Score by Department (Higher = Bigger Gap)")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True)
        return

    sql = f"""
        SELECT employee_name, primary_role, department,
               current_skills, missing_critical_skills,
               skill_gap_score, recommended_trainings, target_role
        FROM gold.talentpulse.gold_employee_ai_features
        WHERE LOWER(employee_name) = LOWER('{employee_name}')
        LIMIT 1
    """
    df = run_query(sql)
    if df.empty:
        st.warning(f"No skill data found for '{employee_name}'.")
        return

    r = df.iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Skill Gap Score", f"{r['skill_gap_score']:.1f}", help="Lower = smaller gap")
    c2.metric("Current Role", r['primary_role'])
    c3.metric("Department", r['department'])

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("✅ Current Skills")
        skills = str(r['current_skills']).split(",") if r['current_skills'] else []
        for s in skills:
            st.markdown(f"- {s.strip()}")
    with col2:
        st.subheader("❌ Missing Skills")
        missing = str(r['missing_critical_skills']).split(",") if r['missing_critical_skills'] else []
        for s in missing:
            st.markdown(f"- 🔴 {s.strip()}")

    if r.get("recommended_trainings"):
        st.subheader("📚 Recommended Trainings")
        st.info(r["recommended_trainings"])
