"""Page: Workforce Insights"""
import streamlit as st
import plotly.express as px
from tools.db_utils import run_query


def render():
    st.title("👥 Workforce Insights")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏆 Top Performers",
        "📅 Low Attendance",
        "🎓 Needs Training",
        "🚀 Promotion Ready",
        "🏢 Dept Summary",
    ])

    with tab1:
        dept = st.selectbox("Filter by Department", ["All", "Engineering", "HR",
                                                      "Finance", "Sales"], key="t1")
        dept_cond = f"AND LOWER(department)=LOWER('{dept}')" if dept != "All" else ""
        sql = f"""
            SELECT employee_name, department, composite_score, performance_rank
            FROM gold.talentpulse.gold_employee_ranking
            WHERE 1=1 {dept_cond}
            ORDER BY composite_score DESC LIMIT 15
        """
        df = run_query(sql)
        fig = px.bar(df, x="employee_name", y="composite_score",
                     color="department", title="Top Performers by Composite Score")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)

    with tab2:
        sql = """
            SELECT employee_name, department, attendance_percentage,
                   total_absent_days, attendance_grade
            FROM gold.talentpulse.gold_employee_attendance_summary
            WHERE attendance_percentage < 75
            ORDER BY attendance_percentage ASC LIMIT 20
        """
        df = run_query(sql)
        st.error(f"⚠️ {len(df)} employees with attendance < 75%")
        fig = px.bar(df, x="employee_name", y="attendance_percentage",
                     color="attendance_percentage", color_continuous_scale="RdYlGn",
                     title="Low Attendance Employees")
        fig.add_hline(y=75, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)

    with tab3:
        sql = """
            SELECT employee_name, department,
                   COUNT(*) FILTER (WHERE status='Pending') AS pending,
                   ROUND(100.0*COUNT(*) FILTER (WHERE status='Completed')/COUNT(*),1)
                     AS completion_pct
            FROM gold.talentpulse.gold_employee_training_summary
            GROUP BY employee_name, department
            HAVING completion_pct < 60
            ORDER BY completion_pct ASC LIMIT 20
        """
        df = run_query(sql)
        st.warning(f"⚠️ {len(df)} employees with < 60% training completion")
        st.dataframe(df, use_container_width=True)

    with tab4:
        sql = """
            SELECT employee_name, department, promotion_readiness_label,
                   promotion_score, recommended_role, estimated_promotion_timeline
            FROM gold.talentpulse.gold_promotion_readiness
            WHERE promotion_readiness_label IN ('Ready','High Potential')
            ORDER BY promotion_score DESC LIMIT 20
        """
        df = run_query(sql)
        st.success(f"🚀 {len(df)} employees are promotion-ready")
        fig = px.bar(df, x="employee_name", y="promotion_score",
                     color="promotion_readiness_label",
                     title="Promotion-Ready Employees")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)

    with tab5:
        sql = """
            SELECT r.department,
                   COUNT(DISTINCT r.employee_id)          AS headcount,
                   ROUND(AVG(r.composite_score),1)        AS avg_score,
                   ROUND(AVG(a.attendance_percentage),1)  AS avg_attendance
            FROM gold.talentpulse.gold_employee_ranking r
            LEFT JOIN gold.talentpulse.gold_employee_attendance_summary a
              ON r.employee_id = a.employee_id
            GROUP BY r.department ORDER BY avg_score DESC
        """
        df = run_query(sql)
        fig = px.scatter(df, x="avg_attendance", y="avg_score",
                         size="headcount", color="department",
                         title="Department: Avg Attendance vs Avg Score",
                         hover_data=["department", "headcount"])
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
