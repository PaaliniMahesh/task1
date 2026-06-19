"""Page: Performance Insights"""
import streamlit as st
import plotly.express as px
from tools.db_utils import run_query


def render():
    st.title("🏆 Performance Insights")

    employee_name = st.text_input("Employee Name (blank = all)", placeholder="e.g. Mahesh")
    view = st.selectbox("View", ["Performance Summary", "KRA Breakdown",
                                 "Manager Ratings", "Top Performers",
                                 "Attendance vs Performance"])

    name_cond = f"WHERE LOWER(employee_name)=LOWER('{employee_name}')" if employee_name else ""

    if view == "Performance Summary":
        sql = f"""
            SELECT employee_name, department, overall_performance_score,
                   performance_grade, manager_rating, kra_avg_score,
                   goal_completion_pct, review_period
            FROM gold.talentpulse.gold_employee_performance_summary
            {name_cond}
            ORDER BY overall_performance_score DESC LIMIT 20
        """
        df = run_query(sql)
        if df.empty:
            st.warning("No data.")
            return
        c1, c2, c3 = st.columns(3)
        c1.metric("Avg Performance Score", f"{df['overall_performance_score'].mean():.1f}")
        c2.metric("Avg Manager Rating", f"{df['manager_rating'].mean():.1f}/5")
        c3.metric("Avg Goal Completion", f"{df['goal_completion_pct'].mean():.0f}%")
        st.dataframe(df, use_container_width=True)

    elif view == "KRA Breakdown":
        sql = f"""
            SELECT employee_name, kra_name, kra_score, kra_weight, review_period
            FROM gold.talentpulse.gold_employee_performance_summary
            {name_cond}
            ORDER BY kra_weight DESC LIMIT 30
        """
        df = run_query(sql)
        fig = px.bar(df, x="kra_name", y="kra_score", color="kra_weight",
                     title="KRA Scores (size = weight)",
                     color_continuous_scale="Blues")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)

    elif view == "Manager Ratings":
        sql = """
            SELECT employee_name, manager_name, manager_rating, review_period
            FROM gold.talentpulse.gold_employee_performance_summary
            ORDER BY manager_rating DESC LIMIT 20
        """
        df = run_query(sql)
        fig = px.bar(df, x="employee_name", y="manager_rating",
                     color="manager_rating", color_continuous_scale="RdYlGn",
                     title="Manager Ratings by Employee")
        fig.update_layout(yaxis_range=[0, 5])
        st.plotly_chart(fig, use_container_width=True)

    elif view == "Top Performers":
        sql = """
            SELECT employee_name, department, overall_performance_score,
                   performance_grade, manager_rating
            FROM gold.talentpulse.gold_employee_performance_summary
            ORDER BY overall_performance_score DESC LIMIT 15
        """
        df = run_query(sql)
        st.success(f"Top {len(df)} performers")
        for i, (_, r) in enumerate(df.iterrows(), 1):
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"#{i}"))
            st.write(f"{medal} **{r['employee_name']}** — {r['department']} — "
                     f"Score: {r['overall_performance_score']:.1f} ({r['performance_grade']})")

    elif view == "Attendance vs Performance":
        sql = """
            SELECT a.employee_name, a.department,
                   a.attendance_percentage, p.overall_performance_score
            FROM gold.talentpulse.gold_employee_attendance_summary a
            JOIN gold.talentpulse.gold_employee_performance_summary p
              ON a.employee_id = p.employee_id
        """
        df = run_query(sql)
        fig = px.scatter(df, x="attendance_percentage", y="overall_performance_score",
                         color="department", hover_data=["employee_name"],
                         title="Attendance % vs Performance Score",
                         trendline="ols")
        st.plotly_chart(fig, use_container_width=True)
