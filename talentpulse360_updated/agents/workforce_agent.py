"""
Agent 7 – Workforce Insights Agent
─────────────────────────────────────────────────────────────────────────────
Purpose  : Answer aggregated workforce questions about groups, departments,
           and organisation-wide patterns.

Gold tables used:
  • gold.talentpulse.gold_employee_ranking
  • gold.talentpulse.gold_promotion_readiness
  • gold.talentpulse.gold_employee_attendance_summary
  • gold.talentpulse.gold_employee_training_summary

Input schema:
  {
    "question_type" : "top_performers" | "low_attendance"
                      | "needs_training" | "promotion_ready"
                      | "dept_summary",
    "department"    : str | None,
    "top_n"         : int | None
  }

Output schema:
  { "answer": str, "data": list[dict], "chart_hint": str }
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import Any
from tools.db_utils import run_query

RANK_TABLE  = "gold.talentpulse.gold_employee_ranking"
PROMO_TABLE = "gold.talentpulse.gold_promotion_readiness"
ATT_TABLE   = "gold.talentpulse.gold_employee_attendance_summary"
TRN_TABLE   = "gold.talentpulse.gold_employee_training_summary"

_SQL = {
    "top_performers": """
        SELECT employee_name, department, overall_rank,
               composite_score, performance_rank
        FROM {rank}
        {dept_filter}
        ORDER BY composite_score DESC
        LIMIT {n}
    """,
    "low_attendance": """
        SELECT employee_id, employee_name, department,
               attendance_percentage, total_absent_days, attendance_grade
        FROM {att}
        WHERE attendance_percentage < 75
        {dept_filter}
        ORDER BY attendance_percentage ASC
        LIMIT {n}
    """,
    "needs_training": """
        SELECT employee_id, employee_name, department,
               COUNT(*) FILTER (WHERE status='Pending') AS pending_trainings,
               ROUND(100.0*COUNT(*) FILTER (WHERE status='Completed')/NULLIF(COUNT(*),0),1)
                 AS completion_pct
        FROM {trn}
        {dept_filter}
        GROUP BY employee_id, employee_name, department
        HAVING completion_pct < 60
        ORDER BY completion_pct ASC
        LIMIT {n}
    """,
    "promotion_ready": """
        SELECT employee_name, department, promotion_readiness_label,
               promotion_score, recommended_role, estimated_promotion_timeline
        FROM {promo}
        WHERE promotion_readiness_label IN ('Ready','High Potential')
        {dept_filter}
        ORDER BY promotion_score DESC
        LIMIT {n}
    """,
    "dept_summary": """
        SELECT r.department,
               COUNT(DISTINCT r.employee_id)           AS headcount,
               ROUND(AVG(r.composite_score), 1)        AS avg_composite_score,
               ROUND(AVG(a.attendance_percentage), 1)  AS avg_attendance_pct,
               COUNT(p.employee_id) FILTER (
                 WHERE p.promotion_readiness_label='Ready') AS promotion_ready_count
        FROM {rank} r
        LEFT JOIN {att} a ON r.employee_id = a.employee_id
        LEFT JOIN {promo} p ON r.employee_id = p.employee_id
        GROUP BY r.department
        ORDER BY avg_composite_score DESC
    """,
}


def workforce_insights_agent(
    question_type: str = "top_performers",
    department: str = "",
    top_n: int = 10,
) -> dict[str, Any]:
    """
    Workforce Insights Agent – aggregated workforce analytics.

    Args:
        question_type : top_performers | low_attendance | needs_training |
                        promotion_ready | dept_summary.
        department    : Optional department filter (e.g. 'Engineering').
        top_n         : Number of employees to return.

    Returns:
        dict with answer (str), data (list[dict]), chart_hint (str).
    """
    qt = question_type.lower().strip()
    dept = department.strip().replace("'", "''")
    dept_filter = f"AND LOWER(department)=LOWER('{dept}')" if dept else ""
    n = top_n

    sql_map = {
        "top_performers": _SQL["top_performers"].format(
            rank=RANK_TABLE, dept_filter=dept_filter.replace("AND","WHERE",1)
            if "WHERE" not in dept_filter else dept_filter, n=n
        ),
        "low_attendance": _SQL["low_attendance"].format(att=ATT_TABLE, dept_filter=dept_filter, n=n),
        "needs_training": _SQL["needs_training"].format(trn=TRN_TABLE, dept_filter=dept_filter.replace("AND","WHERE",1)
            if dept_filter else "", n=n),
        "promotion_ready": _SQL["promotion_ready"].format(promo=PROMO_TABLE, dept_filter=dept_filter, n=n),
        "dept_summary": _SQL["dept_summary"].format(
            rank=RANK_TABLE, att=ATT_TABLE, promo=PROMO_TABLE
        ),
    }

    # Normalise dept_filter insertion for top_performers & needs_training
    # (already formatted above)

    if qt not in sql_map:
        return {"answer": f"Unknown question_type '{qt}'.", "data": [], "chart_hint": "table"}

    try:
        df = run_query(sql_map[qt])
        rows = df.to_dict(orient="records")

        if df.empty:
            return {"answer": "No workforce data found.", "data": [], "chart_hint": "table"}

        dept_label = f" in **{department}**" if department else ""

        if qt == "top_performers":
            answer = f"Top **{len(rows)} performers**{dept_label} by composite score."
        elif qt == "low_attendance":
            answer = (
                f"Found **{len(rows)} employees**{dept_label} "
                f"with attendance below 75%."
            )
        elif qt == "needs_training":
            answer = (
                f"**{len(rows)} employees**{dept_label} "
                f"have training completion below 60%."
            )
        elif qt == "promotion_ready":
            answer = f"**{len(rows)} employees**{dept_label} are promotion-ready."
        elif qt == "dept_summary":
            answer = f"Department summary loaded for **{len(rows)} departments**."
        else:
            answer = f"Retrieved {len(rows)} records."

        chart_map = {
            "top_performers": "table",
            "low_attendance": "table",
            "needs_training": "table",
            "promotion_ready": "table",
            "dept_summary": "bar",
        }
        return {"answer": answer, "data": rows, "chart_hint": chart_map.get(qt, "table")}

    except Exception as exc:
        return {"answer": f"Error in Workforce Agent: {exc}", "data": [], "chart_hint": "table"}
