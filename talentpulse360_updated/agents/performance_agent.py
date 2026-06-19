"""
Agent 3 – Performance Agent
─────────────────────────────────────────────────────────────────────────────
Purpose  : Answer all performance-related questions including KRA ratings,
           manager ratings, performance summaries, and comparisons.

Gold tables used:
  • gold.talentpulse.gold_employee_performance_summary
  • gold.talentpulse.gold_employee_360       (for cross-dimension comparisons)

Input schema:
  {
    "employee_name"  : str | None,
    "employee_id"    : str | None,
    "question_type"  : "summary" | "manager_ratings" | "kra_ratings"
                       | "compare_attendance_performance" | "top_performers",
    "top_n"          : int | None
  }

Output schema:
  { "answer": str, "data": list[dict], "chart_hint": str }
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import Any
from tools.db_utils import run_query

PERF_TABLE = "gold.talentpulse.gold_employee_performance_summary"
EMP360_TABLE = "gold.talentpulse.gold_employee_360"

_SQL = {
    "summary": """
        SELECT employee_id, employee_name, department,
               overall_performance_score, performance_grade,
               manager_rating, self_rating, kra_avg_score,
               goal_completion_pct, review_period
        FROM {t}
        WHERE LOWER(employee_name)=LOWER('{name}') OR employee_id='{eid}'
        ORDER BY review_period DESC LIMIT 1
    """,
    "manager_ratings": """
        SELECT employee_name, manager_name, manager_rating,
               manager_feedback_summary, review_period
        FROM {t}
        WHERE LOWER(employee_name)=LOWER('{name}') OR employee_id='{eid}'
        ORDER BY review_period DESC
    """,
    "kra_ratings": """
        SELECT employee_name, kra_name, kra_score,
               kra_weight, weighted_score, review_period
        FROM {t}
        WHERE LOWER(employee_name)=LOWER('{name}') OR employee_id='{eid}'
        ORDER BY review_period DESC, kra_weight DESC
    """,
    "compare_attendance_performance": """
        SELECT e.employee_name, e.department,
               e.attendance_percentage,
               p.overall_performance_score,
               p.performance_grade,
               p.manager_rating
        FROM gold.talentpulse.gold_employee_attendance_summary e
        JOIN {perf} p
          ON e.employee_id = p.employee_id
        WHERE LOWER(e.employee_name)=LOWER('{name}') OR e.employee_id='{eid}'
        ORDER BY p.review_period DESC LIMIT 1
    """,
    "top_performers": """
        SELECT employee_id, employee_name, department,
               overall_performance_score, performance_grade,
               manager_rating, kra_avg_score
        FROM {t}
        ORDER BY overall_performance_score DESC
        LIMIT {top_n}
    """,
}

CHART_MAP = {
    "summary": "kpi",
    "manager_ratings": "table",
    "kra_ratings": "bar",
    "compare_attendance_performance": "bar",
    "top_performers": "table",
}


def performance_agent(
    employee_name: str = "",
    employee_id: str = "",
    question_type: str = "summary",
    top_n: int = 10,
) -> dict[str, Any]:
    """
    Performance Agent – retrieves performance data from the Gold layer.

    Args:
        employee_name : Employee full name.
        employee_id   : Alternate employee ID.
        question_type : summary | manager_ratings | kra_ratings |
                        compare_attendance_performance | top_performers.
        top_n         : Limit for top-N queries.

    Returns:
        dict with answer (str), data (list[dict]), chart_hint (str).
    """
    qt = question_type.lower().strip()
    name = employee_name.strip().replace("'", "''")
    eid = employee_id.strip()
    t = PERF_TABLE

    try:
        if qt == "top_performers":
            sql = _SQL[qt].format(t=t, top_n=top_n)
        elif qt == "compare_attendance_performance":
            sql = _SQL[qt].format(perf=t, name=name, eid=eid)
        elif qt in _SQL:
            sql = _SQL[qt].format(t=t, name=name, eid=eid)
        else:
            return {"answer": f"Unknown question_type '{qt}'.", "data": [], "chart_hint": "table"}

        df = run_query(sql)
        rows = df.to_dict(orient="records")

        if df.empty:
            answer = f"No performance data found for '{employee_name or employee_id}'."
        elif qt == "summary":
            r = rows[0]
            answer = (
                f"**{r['employee_name']}** Performance Summary:\n"
                f"- Overall Score: **{r['overall_performance_score']:.1f}** "
                f"(Grade: {r['performance_grade']})\n"
                f"- Manager Rating: {r['manager_rating']:.1f} / 5\n"
                f"- KRA Avg Score: {r['kra_avg_score']:.1f}\n"
                f"- Goal Completion: {r['goal_completion_pct']:.0f}%\n"
                f"- Review Period: {r['review_period']}"
            )
        elif qt == "manager_ratings":
            r = rows[0]
            answer = (
                f"**{employee_name}** Manager Rating: **{r['manager_rating']:.1f}/5** "
                f"by {r['manager_name']} ({r['review_period']}).\n"
                f"Feedback: {r.get('manager_feedback_summary','N/A')}"
            )
        elif qt == "kra_ratings":
            answer = f"**{employee_name}** has **{len(rows)} KRA entries**. "
            if rows:
                best = max(rows, key=lambda x: x.get("kra_score", 0))
                answer += f"Highest KRA: **{best['kra_name']}** at {best['kra_score']:.1f}."
        elif qt == "compare_attendance_performance":
            r = rows[0]
            answer = (
                f"**{employee_name}** – Attendance: {r['attendance_percentage']:.1f}%  |  "
                f"Performance Score: {r['overall_performance_score']:.1f} ({r['performance_grade']})"
            )
        elif qt == "top_performers":
            answer = f"Top **{len(rows)} performers** loaded by overall score."
        else:
            answer = f"Retrieved {len(rows)} records."

        return {"answer": answer, "data": rows, "chart_hint": CHART_MAP.get(qt, "table")}

    except Exception as exc:
        return {"answer": f"Error in Performance Agent: {exc}", "data": [], "chart_hint": "table"}
