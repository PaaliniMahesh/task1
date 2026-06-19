"""
Agent 5 – Employee360 Agent
─────────────────────────────────────────────────────────────────────────────
Purpose  : Provide a unified 360-degree view of an employee by combining
           attendance, training, performance, skills, and promotion data.

Gold tables used:
  • gold.talentpulse.gold_employee_360
  • gold.talentpulse.gold_employee_ranking
  • gold.talentpulse.gold_promotion_readiness

Input schema:
  {
    "employee_name" : str | None,
    "employee_id"   : str | None,
    "question_type" : "full_profile" | "employee_score"
                      | "promotion_readiness" | "ranking"
  }

Output schema:
  { "answer": str, "data": list[dict], "chart_hint": str }
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import Any
from tools.db_utils import run_query

E360_TABLE  = "gold.talentpulse.gold_employee_360"
RANK_TABLE  = "gold.talentpulse.gold_employee_ranking"
PROMO_TABLE = "gold.talentpulse.gold_promotion_readiness"

_SQL = {
    "full_profile": """
        SELECT *
        FROM {e360}
        WHERE LOWER(employee_name)=LOWER('{name}') OR employee_id='{eid}'
        LIMIT 1
    """,
    "employee_score": """
        SELECT employee_name, composite_score, performance_score,
               attendance_score, training_score, skill_score,
               engagement_score, score_grade
        FROM {e360}
        WHERE LOWER(employee_name)=LOWER('{name}') OR employee_id='{eid}'
        LIMIT 1
    """,
    "promotion_readiness": """
        SELECT p.employee_name, p.promotion_score, p.promotion_readiness_label,
               p.years_in_current_role, p.performance_trend,
               p.skill_readiness_pct, p.manager_recommendation,
               p.recommended_role, p.estimated_promotion_timeline
        FROM {promo} p
        WHERE LOWER(p.employee_name)=LOWER('{name}') OR p.employee_id='{eid}'
        LIMIT 1
    """,
    "ranking": """
        SELECT employee_name, department, overall_rank,
               dept_rank, performance_rank, attendance_rank,
               training_rank, composite_score
        FROM {rank}
        WHERE LOWER(employee_name)=LOWER('{name}') OR employee_id='{eid}'
        LIMIT 1
    """,
}


def employee360_agent(
    employee_name: str = "",
    employee_id: str = "",
    question_type: str = "full_profile",
) -> dict[str, Any]:
    """
    Employee360 Agent – unified employee profile view.

    Args:
        employee_name : Employee full name.
        employee_id   : Alternate employee ID.
        question_type : full_profile | employee_score | promotion_readiness |
                        ranking.

    Returns:
        dict with answer (str), data (list[dict]), chart_hint (str).
    """
    qt = question_type.lower().strip()
    name = employee_name.strip().replace("'", "''")
    eid = employee_id.strip()

    sql_map = {
        "full_profile": _SQL["full_profile"].format(e360=E360_TABLE, name=name, eid=eid),
        "employee_score": _SQL["employee_score"].format(e360=E360_TABLE, name=name, eid=eid),
        "promotion_readiness": _SQL["promotion_readiness"].format(promo=PROMO_TABLE, name=name, eid=eid),
        "ranking": _SQL["ranking"].format(rank=RANK_TABLE, name=name, eid=eid),
    }

    if qt not in sql_map:
        return {"answer": f"Unknown question_type '{qt}'.", "data": [], "chart_hint": "table"}

    try:
        df = run_query(sql_map[qt])
        rows = df.to_dict(orient="records")

        if df.empty:
            return {"answer": f"No 360 data found for '{employee_name or employee_id}'.",
                    "data": [], "chart_hint": "table"}

        r = rows[0]

        if qt == "full_profile":
            answer = (
                f"## 360° Profile – {r.get('employee_name')}\n"
                f"**Department**: {r.get('department')} | **Role**: {r.get('current_role')}\n\n"
                f"| Dimension        | Score |\n"
                f"|-----------------|-------|\n"
                f"| Performance     | {r.get('performance_score', 'N/A')} |\n"
                f"| Attendance      | {r.get('attendance_score', 'N/A')} |\n"
                f"| Training        | {r.get('training_score', 'N/A')} |\n"
                f"| Skills          | {r.get('skill_score', 'N/A')} |\n"
                f"| Engagement      | {r.get('engagement_score', 'N/A')} |\n"
                f"| **Composite**   | **{r.get('composite_score', 'N/A')}** |\n"
            )
            chart = "table"

        elif qt == "employee_score":
            answer = (
                f"**{r['employee_name']}** Composite Score: **{r['composite_score']:.1f}** "
                f"(Grade: {r['score_grade']})\n"
                f"- Performance: {r['performance_score']:.1f}\n"
                f"- Attendance:  {r['attendance_score']:.1f}\n"
                f"- Training:    {r['training_score']:.1f}\n"
                f"- Skills:      {r['skill_score']:.1f}\n"
                f"- Engagement:  {r['engagement_score']:.1f}"
            )
            chart = "kpi"

        elif qt == "promotion_readiness":
            answer = (
                f"**{r['employee_name']}** Promotion Readiness:\n"
                f"- Readiness: **{r['promotion_readiness_label']}** "
                f"(Score: {r['promotion_score']:.1f})\n"
                f"- Years in Role: {r['years_in_current_role']}\n"
                f"- Performance Trend: {r['performance_trend']}\n"
                f"- Skill Readiness: {r['skill_readiness_pct']:.0f}%\n"
                f"- Manager Recommendation: {r['manager_recommendation']}\n"
                f"- Recommended Next Role: {r['recommended_role']}\n"
                f"- Estimated Timeline: {r['estimated_promotion_timeline']}"
            )
            chart = "kpi"

        elif qt == "ranking":
            answer = (
                f"**{r['employee_name']}** Rankings:\n"
                f"- Overall Rank: #{r['overall_rank']}\n"
                f"- Dept Rank:    #{r['dept_rank']} in {r['department']}\n"
                f"- Performance:  #{r['performance_rank']}\n"
                f"- Attendance:   #{r['attendance_rank']}\n"
                f"- Training:     #{r['training_rank']}\n"
                f"- Composite Score: {r['composite_score']:.1f}"
            )
            chart = "kpi"

        else:
            answer = f"Retrieved {len(rows)} records."
            chart = "table"

        return {"answer": answer, "data": rows, "chart_hint": chart}

    except Exception as exc:
        return {"answer": f"Error in Employee360 Agent: {exc}", "data": [], "chart_hint": "table"}
