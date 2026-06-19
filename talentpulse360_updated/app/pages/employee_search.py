"""Page: Employee Search"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from tools.db_utils import run_query


def render():
    st.title("🔍 Employee Search")
    st.caption("Search for any employee and view their complete profile at a glance.")

    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("🔍 Enter employee name or ID", placeholder="e.g. Mahesh")
    with col2:
        dept_filter = st.selectbox("Department", ["All", "Engineering", "HR", "Finance",
                                                   "Sales", "Marketing", "Operations"])

    if not search_term:
        st.info("Enter an employee name to search.")
        return

    dept_sql = f"AND LOWER(department) = LOWER('{dept_filter}')" if dept_filter != "All" else ""

    sql = f"""
        SELECT e.employee_id, e.employee_name, e.department, e.current_role,
               e.composite_score, e.score_grade,
               e.performance_score, e.attendance_score,
               e.training_score, e.skill_score
        FROM gold.talentpulse.gold_employee_360 e
        WHERE (LOWER(e.employee_name) LIKE LOWER('%{search_term}%')
               OR e.employee_id LIKE '%{search_term}%')
        {dept_sql}
        ORDER BY e.composite_score DESC
        LIMIT 20
    """

    try:
        df = run_query(sql)
    except Exception as e:
        st.error(f"Query error: {e}")
        return

    if df.empty:
        st.warning(f"No employees found matching '{search_term}'.")
        return

    st.success(f"Found **{len(df)} employee(s)**")

    for _, row in df.iterrows():
        with st.expander(f"👤 {row['employee_name']} — {row['current_role']} ({row['department']})",
                         expanded=len(df) == 1):
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Composite Score", f"{row['composite_score']:.1f}", delta=row['score_grade'])
            c2.metric("Performance", f"{row['performance_score']:.1f}")
            c3.metric("Attendance", f"{row['attendance_score']:.1f}")
            c4.metric("Training", f"{row['training_score']:.1f}")
            c5.metric("Skills", f"{row['skill_score']:.1f}")

            # Radar chart
            categories = ["Performance", "Attendance", "Training", "Skills"]
            values = [
                row["performance_score"], row["attendance_score"],
                row["training_score"], row["skill_score"],
            ]
            fig = go.Figure(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                fillcolor="rgba(30, 90, 200, 0.2)",
                line_color="rgba(30, 90, 200, 0.8)",
            ))
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                showlegend=False, height=300,
            )
            st.plotly_chart(fig, use_container_width=True, key=f"radar_{row['employee_id']}")
