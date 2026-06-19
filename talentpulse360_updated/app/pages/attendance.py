"""Page: Attendance Insights"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from tools.db_utils import run_query


def render():
    st.title("📅 Attendance Insights")

    col1, col2 = st.columns([3, 1])
    with col1:
        employee_name = st.text_input("Employee Name (leave blank for all)", placeholder="e.g. Mahesh")
    with col2:
        view = st.selectbox("View", ["Summary KPIs", "Monthly Trend", "WFH vs Office", "Low Attendance"])

    name_filter = f"WHERE LOWER(employee_name) = LOWER('{employee_name}')" if employee_name else ""

    if view == "Summary KPIs":
        sql = f"""
            SELECT employee_name, department,
                   AVG(attendance_percentage)  AS avg_att_pct,
                   SUM(total_present_days)     AS total_present,
                   SUM(total_absent_days)      AS total_absent,
                   SUM(total_wfh_days)         AS total_wfh,
                   AVG(avg_effective_hours)    AS avg_eff_hours
            FROM gold.talentpulse.gold_employee_attendance_summary
            {name_filter}
            GROUP BY employee_name, department
        """
        df = run_query(sql)
        if df.empty:
            st.warning("No data found.")
            return
        r = df.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Avg Attendance %", f"{r['avg_att_pct']:.1f}%")
        c2.metric("Total Present Days", int(r['total_present']))
        c3.metric("Total WFH Days", int(r['total_wfh']))
        c4.metric("Avg Effective Hrs/Day", f"{r['avg_eff_hours']:.1f} hrs")
        st.dataframe(df, use_container_width=True)

    elif view == "Monthly Trend":
        name_cond = f"AND LOWER(employee_name)=LOWER('{employee_name}')" if employee_name else ""
        sql = f"""
            SELECT month_year,
                   ROUND(AVG(attendance_percentage), 1) AS avg_att_pct,
                   SUM(total_wfh_days) AS wfh_days,
                   SUM(total_present_days) AS present_days
            FROM gold.talentpulse.gold_employee_attendance_summary
            WHERE 1=1 {name_cond}
            GROUP BY month_year ORDER BY month_year
        """
        df = run_query(sql)
        if df.empty:
            st.warning("No data.")
            return
        fig = px.line(df, x="month_year", y="avg_att_pct",
                      title="Monthly Attendance % Trend",
                      markers=True, color_discrete_sequence=["#1E3A8A"])
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.bar(df, x="month_year", y=["present_days", "wfh_days"],
                      title="Present vs WFH Days",
                      color_discrete_sequence=["#1E3A8A", "#60A5FA"],
                      barmode="group")
        st.plotly_chart(fig2, use_container_width=True)

    elif view == "WFH vs Office":
        sql = f"""
            SELECT department,
                   SUM(total_wfh_days)     AS wfh_days,
                   SUM(total_present_days) AS office_days
            FROM gold.talentpulse.gold_employee_attendance_summary
            GROUP BY department ORDER BY wfh_days DESC
        """
        df = run_query(sql)
        fig = px.bar(df, x="department", y=["wfh_days", "office_days"],
                     title="WFH vs Office Days by Department", barmode="stack",
                     color_discrete_sequence=["#60A5FA", "#1D4ED8"])
        st.plotly_chart(fig, use_container_width=True)

    elif view == "Low Attendance":
        sql = """
            SELECT employee_name, department, attendance_percentage,
                   total_absent_days, attendance_grade
            FROM gold.talentpulse.gold_employee_attendance_summary
            WHERE attendance_percentage < 75
            ORDER BY attendance_percentage ASC
        """
        df = run_query(sql)
        st.warning(f"⚠️ {len(df)} employees with attendance below 75%")
        fig = px.bar(df, x="employee_name", y="attendance_percentage",
                     color="attendance_percentage",
                     color_continuous_scale="RdYlGn",
                     title="Low Attendance Employees")
        fig.add_hline(y=75, line_dash="dash", line_color="red",
                      annotation_text="75% threshold")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(df, use_container_width=True)
