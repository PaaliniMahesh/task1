"""Page: Training Insights"""
import streamlit as st
import plotly.express as px
from tools.db_utils import run_query


def render():
    st.title("🎓 Training Insights")

    employee_name = st.text_input("Employee Name (blank = all)", placeholder="e.g. Mahesh")
    view = st.selectbox("View", ["Completion Overview", "Pending Trainings",
                                 "Training by Category", "Employees Needing Training"])

    if view == "Completion Overview":
        name_cond = f"WHERE LOWER(employee_name)=LOWER('{employee_name}')" if employee_name else ""
        sql = f"""
            SELECT employee_name, department,
                   COUNT(*) FILTER (WHERE status='Completed')              AS completed,
                   COUNT(*) FILTER (WHERE status IN ('Pending','In Progress')) AS pending,
                   ROUND(100.0*COUNT(*) FILTER (WHERE status='Completed')/COUNT(*),1)
                     AS completion_pct
            FROM gold.talentpulse.gold_employee_training_summary
            {name_cond}
            GROUP BY employee_name, department
            ORDER BY completion_pct DESC
        """
        df = run_query(sql)
        if df.empty:
            st.warning("No data.")
            return
        agg = df.agg({"completed": "sum", "pending": "sum"})
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Completed", int(agg["completed"]))
        c2.metric("Total Pending", int(agg["pending"]))
        avg_pct = df["completion_pct"].mean()
        c3.metric("Avg Completion %", f"{avg_pct:.1f}%")

        fig = px.bar(df.head(20), x="employee_name", y="completion_pct",
                     color="completion_pct", color_continuous_scale="Blues",
                     title="Training Completion % by Employee")
        fig.add_hline(y=80, line_dash="dash", line_color="green",
                      annotation_text="80% target")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)

    elif view == "Pending Trainings":
        name_cond = f"WHERE LOWER(employee_name)=LOWER('{employee_name}')" if employee_name else ""
        sql = f"""
            SELECT employee_name, training_name, due_date,
                   training_category, priority
            FROM gold.talentpulse.gold_employee_training_summary
            {name_cond if name_cond else 'WHERE'}
            {'AND' if name_cond else ''} status IN ('Pending','In Progress')
            ORDER BY due_date ASC
            LIMIT 50
        """
        df = run_query(sql)
        st.warning(f"{len(df)} pending/in-progress trainings")
        st.dataframe(df, use_container_width=True)

    elif view == "Training by Category":
        sql = """
            SELECT training_category,
                   COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE status='Completed') AS completed
            FROM gold.talentpulse.gold_employee_training_summary
            GROUP BY training_category ORDER BY total DESC
        """
        df = run_query(sql)
        fig = px.bar(df, x="training_category", y=["completed", "total"],
                     barmode="overlay", title="Training by Category",
                     color_discrete_sequence=["#1E40AF", "#BFDBFE"])
        st.plotly_chart(fig, use_container_width=True)

    elif view == "Employees Needing Training":
        sql = """
            SELECT employee_name, department,
                   COUNT(*) FILTER (WHERE status='Pending') AS pending,
                   ROUND(100.0*COUNT(*) FILTER (WHERE status='Completed')/COUNT(*),1) AS pct
            FROM gold.talentpulse.gold_employee_training_summary
            GROUP BY employee_name, department
            HAVING pct < 50
            ORDER BY pct ASC LIMIT 20
        """
        df = run_query(sql)
        st.error(f"⚠️ {len(df)} employees with < 50% training completion")
        st.dataframe(df, use_container_width=True)
