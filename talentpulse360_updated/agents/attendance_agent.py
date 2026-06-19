"""
Agent 1 – Attendance Agent
─────────────────────────────────────────────────────────────────────────────
Purpose  : Answer all attendance-related questions for an employee or the
           full workforce.  Covers WFH days, leave counts, effective working
           hours, monthly trends, and flags low-attendance employees.

Gold tables used:
  • gold.talentpulse.gold_employee_attendance_summary

Input schema  (passed by the Supervisor):
  {
    "employee_name" : str | None,   # e.g. "Mahesh"
    "employee_id"   : str | None,   # e.g. "EMP001"
    "question_type" : str,          # one of the Q_TYPES below
    "month"         : str | None,   # "2024-11"
    "top_n"         : int | None    # for workforce list queries
  }

Output schema:
  {
    "answer"        : str,          # human-readable answer
    "data"          : list[dict],   # raw rows for charting
    "chart_hint"    : str           # "bar" | "line" | "table" | "kpi"
  }
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import Any
import json
import mlflow
from pydantic import BaseModel, Field
from tools.db_utils import run_query, table

# ── Mosaic AI tool decorator ──────────────────────────────────────────────────
# When deployed as a Databricks Agent tool, the function is wrapped with
# @mlflow.pyfunc.tool  (or registered via UCFunctionToolkit).
# We define it as a plain callable here so it can also be unit-tested.

ATT_TABLE = "gold.talentpulse.gold_employee_attendance_summary"

Q_TYPES = {
    "summary",
    "wfh_days",
    "effective_hours",
    "leave_count",
    "monthly_trend",
    "low_attendance_employees",
}

# ─────────────────────────────────────────────────────────────────────────────
# SQL Library
# ─────────────────────────────────────────────────────────────────────────────

_SQL = {
    # Full summary for one employee
    "summary": """
        SELECT
            employee_id,
            employee_name,
            department,
            total_present_days,
            total_absent_days,
            total_wfh_days,
            total_leave_days,
            avg_effective_hours,
            attendance_percentage,
            attendance_grade,
            last_updated
        FROM {table}
        WHERE LOWER(employee_name) = LOWER('{name}')
           OR employee_id = '{emp_id}'
        ORDER BY last_updated DESC
        LIMIT 1
    """,

    # WFH days only
    "wfh_days": """
        SELECT
            employee_name,
            total_wfh_days,
            wfh_percentage,
            month_year
        FROM {table}
        WHERE LOWER(employee_name) = LOWER('{name}')
           OR employee_id = '{emp_id}'
        ORDER BY month_year DESC
    """,

    # Effective working hours
    "effective_hours": """
        SELECT
            employee_name,
            month_year,
            avg_effective_hours,
            total_effective_hours,
            target_hours
        FROM {table}
        WHERE LOWER(employee_name) = LOWER('{name}')
           OR employee_id = '{emp_id}'
        ORDER BY month_year DESC
    """,

    # Leave count
    "leave_count": """
        SELECT
            employee_name,
            month_year,
            total_leave_days,
            sick_leave_days,
            casual_leave_days,
            planned_leave_days
        FROM {table}
        WHERE LOWER(employee_name) = LOWER('{name}')
           OR employee_id = '{emp_id}'
        ORDER BY month_year DESC
    """,

    # Monthly attendance trend (for charts)
    "monthly_trend": """
        SELECT
            month_year,
            AVG(attendance_percentage)  AS avg_attendance_pct,
            SUM(total_present_days)     AS total_present,
            SUM(total_absent_days)      AS total_absent,
            SUM(total_wfh_days)         AS total_wfh,
            COUNT(DISTINCT employee_id) AS headcount
        FROM {table}
        {where}
        GROUP BY month_year
        ORDER BY month_year
    """,

    # Employees with low attendance
    "low_attendance_employees": """
        SELECT
            employee_id,
            employee_name,
            department,
            attendance_percentage,
            total_absent_days,
            attendance_grade
        FROM {table}
        WHERE attendance_percentage < 75
        ORDER BY attendance_percentage ASC
        LIMIT {top_n}
    """,
}


# ─────────────────────────────────────────────────────────────────────────────
# Tool function
# ─────────────────────────────────────────────────────────────────────────────

def attendance_agent(
    employee_name: str = "",
    employee_id: str = "",
    question_type: str = "summary",
    month: str = "",
    top_n: int = 10,
) -> dict[str, Any]:
    """
    Attendance Agent – retrieves attendance data from the Gold layer.

    Args:
        employee_name : Full or partial employee name (case-insensitive).
        employee_id   : Alternate lookup by employee ID.
        question_type : One of summary | wfh_days | effective_hours |
                        leave_count | monthly_trend | low_attendance_employees.
        month         : Optional filter 'YYYY-MM' for monthly trend.
        top_n         : Number of rows for list queries (default 10).

    Returns:
        dict with keys: answer (str), data (list[dict]), chart_hint (str).
    """
    qt = question_type.lower().strip()
    if qt not in Q_TYPES:
        return {"answer": f"Unknown question type '{qt}'.", "data": [], "chart_hint": "table"}

    t = ATT_TABLE
    name = employee_name.strip().replace("'", "''")
    emp_id = employee_id.strip()

    try:
        if qt == "low_attendance_employees":
            sql = _SQL[qt].format(table=t, top_n=top_n)

        elif qt == "monthly_trend":
            where = f"WHERE LOWER(employee_name) = LOWER('{name}')" if name else ""
            if month:
                connector = "AND" if name else "WHERE"
                where += f" {connector} month_year = '{month}'"
            sql = _SQL[qt].format(table=t, where=where)

        else:
            sql = _SQL[qt].format(table=t, name=name, emp_id=emp_id)

        df = run_query(sql)
        rows = df.to_dict(orient="records")

        # ── Build natural-language answer ─────────────────────────────────────
        if df.empty:
            answer = f"No attendance data found for '{employee_name or employee_id}'."
        elif qt == "summary":
            r = rows[0]
            answer = (
                f"**{r['employee_name']}** Attendance Summary:\n"
                f"- Present Days: {r['total_present_days']}\n"
                f"- Absent Days:  {r['total_absent_days']}\n"
                f"- WFH Days:     {r['total_wfh_days']}\n"
                f"- Leave Days:   {r['total_leave_days']}\n"
                f"- Avg Effective Hours/Day: {r['avg_effective_hours']:.1f} hrs\n"
                f"- Attendance %: {r['attendance_percentage']:.1f}%  (Grade: {r['attendance_grade']})"
            )
        elif qt == "wfh_days":
            total = sum(r["total_wfh_days"] for r in rows)
            answer = f"**{employee_name}** has taken **{total} WFH days** across {len(rows)} month(s)."
        elif qt == "effective_hours":
            avg = sum(r["avg_effective_hours"] for r in rows) / len(rows)
            answer = f"**{employee_name}** average effective working hours: **{avg:.1f} hrs/day**."
        elif qt == "leave_count":
            total = sum(r["total_leave_days"] for r in rows)
            answer = f"**{employee_name}** has taken **{total} leave days** across {len(rows)} month(s)."
        elif qt == "monthly_trend":
            answer = f"Monthly attendance trend loaded — {len(rows)} months of data."
        elif qt == "low_attendance_employees":
            answer = f"Found **{len(rows)} employees** with attendance below 75%."
        else:
            answer = f"Retrieved {len(rows)} records."

        chart_map = {
            "summary": "kpi",
            "wfh_days": "bar",
            "effective_hours": "line",
            "leave_count": "bar",
            "monthly_trend": "line",
            "low_attendance_employees": "table",
        }
        return {"answer": answer, "data": rows, "chart_hint": chart_map.get(qt, "table")}

    except Exception as exc:
        return {"answer": f"Error fetching attendance data: {exc}", "data": [], "chart_hint": "table"}
