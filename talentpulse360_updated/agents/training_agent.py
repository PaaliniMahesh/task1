"""
Agent 2 – Training Agent
─────────────────────────────────────────────────────────────────────────────
Purpose  : Answer all training / learning questions for an employee or the
           full workforce.

Gold tables used:
  • gold.talentpulse.gold_employee_training_summary

Input schema:
  {
    "employee_name"  : str | None,
    "employee_id"    : str | None,
    "question_type"  : "completed" | "pending" | "completion_pct"
                       | "last_quarter" | "needs_training",
    "quarter"        : str | None,   # "Q1-2024"
    "top_n"          : int | None
  }

Output schema:
  { "answer": str, "data": list[dict], "chart_hint": str }
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import Any
from tools.db_utils import run_query

TRN_TABLE = "gold.talentpulse.gold_employee_training_summary"

_SQL = {
    "completed": """
        SELECT employee_name, training_name, completion_date,
               training_category, training_hours, score
        FROM {t}
        WHERE (LOWER(employee_name)=LOWER('{name}') OR employee_id='{eid}')
          AND status = 'Completed'
        ORDER BY completion_date DESC
    """,
    "pending": """
        SELECT employee_name, training_name, due_date,
               training_category, priority
        FROM {t}
        WHERE (LOWER(employee_name)=LOWER('{name}') OR employee_id='{eid}')
          AND status IN ('Pending','In Progress')
        ORDER BY due_date ASC
    """,
    "completion_pct": """
        SELECT employee_name,
               COUNT(*) FILTER (WHERE status='Completed')              AS completed,
               COUNT(*) FILTER (WHERE status IN ('Pending','In Progress')) AS pending,
               ROUND(
                 100.0 * COUNT(*) FILTER (WHERE status='Completed') / COUNT(*), 1
               )                                                        AS completion_pct
        FROM {t}
        WHERE LOWER(employee_name)=LOWER('{name}') OR employee_id='{eid}'
        GROUP BY employee_name
    """,
    "last_quarter": """
        SELECT employee_name, training_name, completion_date,
               training_category, training_hours, score, status
        FROM {t}
        WHERE (LOWER(employee_name)=LOWER('{name}') OR employee_id='{eid}')
          AND quarter = '{quarter}'
        ORDER BY completion_date DESC
    """,
    "needs_training": """
        SELECT employee_id, employee_name, department,
               COUNT(*) FILTER (WHERE status='Completed') AS completed,
               COUNT(*) FILTER (WHERE status='Pending')   AS pending,
               ROUND(
                 100.0 * COUNT(*) FILTER (WHERE status='Completed') / NULLIF(COUNT(*),0), 1
               ) AS completion_pct
        FROM {t}
        GROUP BY employee_id, employee_name, department
        HAVING completion_pct < 50
        ORDER BY completion_pct ASC
        LIMIT {top_n}
    """,
}

CHART_MAP = {
    "completed": "table",
    "pending": "table",
    "completion_pct": "kpi",
    "last_quarter": "bar",
    "needs_training": "table",
}


def training_agent(
    employee_name: str = "",
    employee_id: str = "",
    question_type: str = "completed",
    quarter: str = "",
    top_n: int = 10,
) -> dict[str, Any]:
    """
    Training Agent – retrieves training & learning data from the Gold layer.

    Args:
        employee_name : Employee full name (case-insensitive).
        employee_id   : Alternate employee ID lookup.
        question_type : completed | pending | completion_pct | last_quarter |
                        needs_training.
        quarter       : e.g. 'Q1-2024' (used for last_quarter).
        top_n         : Limit for list queries.

    Returns:
        dict with answer (str), data (list[dict]), chart_hint (str).
    """
    qt = question_type.lower().strip()
    name = employee_name.strip().replace("'", "''")
    eid = employee_id.strip()
    t = TRN_TABLE

    try:
        if qt == "needs_training":
            sql = _SQL[qt].format(t=t, top_n=top_n)
        elif qt == "last_quarter":
            q = quarter or "Q1-2024"
            sql = _SQL[qt].format(t=t, name=name, eid=eid, quarter=q)
        elif qt in _SQL:
            sql = _SQL[qt].format(t=t, name=name, eid=eid)
        else:
            return {"answer": f"Unknown question_type '{qt}'.", "data": [], "chart_hint": "table"}

        df = run_query(sql)
        rows = df.to_dict(orient="records")

        if df.empty:
            answer = f"No training data found for '{employee_name or employee_id}'."
        elif qt == "completed":
            total_hours = sum(r.get("training_hours", 0) for r in rows)
            answer = (
                f"**{employee_name}** has completed **{len(rows)} trainings** "
                f"totalling **{total_hours:.0f} hours**."
            )
        elif qt == "pending":
            answer = f"**{employee_name}** has **{len(rows)} pending/in-progress trainings**."
        elif qt == "completion_pct":
            r = rows[0]
            answer = (
                f"**{employee_name}** training completion: **{r['completion_pct']}%** "
                f"({r['completed']} completed, {r['pending']} pending)."
            )
        elif qt == "last_quarter":
            answer = f"**{employee_name}** had **{len(rows)} training activities** in {quarter}."
        elif qt == "needs_training":
            answer = f"**{len(rows)} employees** have training completion below 50%."
        else:
            answer = f"Retrieved {len(rows)} records."

        return {"answer": answer, "data": rows, "chart_hint": CHART_MAP.get(qt, "table")}

    except Exception as exc:
        return {"answer": f"Error in Training Agent: {exc}", "data": [], "chart_hint": "table"}
