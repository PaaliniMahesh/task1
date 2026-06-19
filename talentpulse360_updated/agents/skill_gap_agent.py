"""
Agent 4 – Skill Gap Agent
─────────────────────────────────────────────────────────────────────────────
Purpose  : Analyse skill gaps between current employee skills and role
           requirements.  Also generates personalised learning path
           recommendations by querying the RAG vector index for training
           catalog matches.

Gold tables used:
  • gold.talentpulse.gold_employee_ai_features   (current skills + role)
  • gold.talentpulse.gold_employee_360           (skill scores)

RAG index used:
  • gold.talentpulse.skill_framework_index
  • gold.talentpulse.training_catalog_index

Input schema:
  {
    "employee_name" : str | None,
    "employee_id"   : str | None,
    "question_type" : "current_skills" | "required_skills" | "gap_analysis"
                      | "learning_path",
    "target_role"   : str | None    # e.g. "Databricks Data Engineer"
  }

Output schema:
  { "answer": str, "data": list[dict], "chart_hint": str,
    "rag_context": str | None }
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import Any
from tools.db_utils import run_query
from rag.vector_search import query_index
import yaml, os
from pathlib import Path

AI_TABLE  = "gold.talentpulse.gold_employee_ai_features"
EMP360    = "gold.talentpulse.gold_employee_360"

_SQL = {
    "current_skills": """
        SELECT employee_name, current_skills,
               primary_role, department, experience_years
        FROM {t}
        WHERE LOWER(employee_name)=LOWER('{name}') OR employee_id='{eid}'
        LIMIT 1
    """,
    "gap_analysis": """
        SELECT f.employee_name,
               f.current_skills,
               f.skill_gap_score,
               f.missing_critical_skills,
               f.target_role,
               f.recommended_trainings
        FROM {t} f
        WHERE LOWER(f.employee_name)=LOWER('{name}') OR f.employee_id='{eid}'
        LIMIT 1
    """,
    "required_skills_for_role": """
        SELECT DISTINCT role_name, required_skills, skill_level_required
        FROM gold.talentpulse.gold_role_skill_framework
        WHERE LOWER(role_name) LIKE LOWER('%{role}%')
        LIMIT 5
    """,
}


def skill_gap_agent(
    employee_name: str = "",
    employee_id: str = "",
    question_type: str = "gap_analysis",
    target_role: str = "",
) -> dict[str, Any]:
    """
    Skill Gap Agent – identifies skill gaps and recommends learning paths.

    Args:
        employee_name : Employee full name.
        employee_id   : Alternate employee ID.
        question_type : current_skills | required_skills | gap_analysis |
                        learning_path.
        target_role   : Role to compare against (e.g. 'Databricks Data Engineer').

    Returns:
        dict with answer, data, chart_hint, rag_context.
    """
    qt = question_type.lower().strip()
    name = employee_name.strip().replace("'", "''")
    eid = employee_id.strip()
    t = AI_TABLE
    rag_context = None

    try:
        # ── Current skills ────────────────────────────────────────────────────
        if qt == "current_skills":
            sql = _SQL["current_skills"].format(t=t, name=name, eid=eid)
            df = run_query(sql)
            rows = df.to_dict(orient="records")
            if df.empty:
                return {"answer": f"No skill data for '{name}'.", "data": [],
                        "chart_hint": "table", "rag_context": None}
            r = rows[0]
            skills = r.get("current_skills", "")
            answer = (
                f"**{r['employee_name']}** current skills:\n{skills}\n\n"
                f"Role: {r['primary_role']} | Experience: {r['experience_years']} yrs"
            )
            return {"answer": answer, "data": rows, "chart_hint": "table", "rag_context": None}

        # ── Required skills for a role (RAG-enhanced) ────────────────────────
        elif qt == "required_skills":
            role = target_role or "Data Engineer"
            # Try Gold table first
            sql = _SQL["required_skills_for_role"].format(role=role)
            df = run_query(sql)
            rows = df.to_dict(orient="records")

            # Augment with RAG vector search
            try:
                rag_context = query_index(
                    index_name="gold.talentpulse.skill_framework_index",
                    query=f"required skills for {role}",
                    top_k=3,
                )
            except Exception:
                rag_context = None

            if df.empty and not rag_context:
                answer = f"No skill framework found for role '{role}'."
            else:
                answer = (
                    f"Skills required for **{role}**:\n"
                    + "\n".join(f"- {r.get('required_skills','')}" for r in rows[:3])
                )
                if rag_context:
                    answer += f"\n\n📚 From HR skill framework: {rag_context[:500]}..."
            return {"answer": answer, "data": rows, "chart_hint": "table", "rag_context": rag_context}

        # ── Gap analysis ──────────────────────────────────────────────────────
        elif qt == "gap_analysis":
            sql = _SQL["gap_analysis"].format(t=t, name=name, eid=eid)
            df = run_query(sql)
            rows = df.to_dict(orient="records")
            if df.empty:
                return {"answer": f"No gap analysis data for '{name}'.",
                        "data": [], "chart_hint": "table", "rag_context": None}
            r = rows[0]
            missing = r.get("missing_critical_skills", "None identified")
            gap_score = r.get("skill_gap_score", 0)
            answer = (
                f"**{r['employee_name']}** Skill Gap Analysis:\n"
                f"- Gap Score: **{gap_score:.1f}** (lower = better)\n"
                f"- Target Role: {r.get('target_role','N/A')}\n"
                f"- Missing Critical Skills:\n  {missing}\n"
                f"- Recommended Trainings: {r.get('recommended_trainings','N/A')}"
            )
            return {"answer": answer, "data": rows, "chart_hint": "bar", "rag_context": None}

        # ── Learning path (RAG-enhanced) ─────────────────────────────────────
        elif qt == "learning_path":
            # Get employee gap first
            sql = _SQL["gap_analysis"].format(t=t, name=name, eid=eid)
            df = run_query(sql)
            rows = df.to_dict(orient="records")
            missing = rows[0].get("missing_critical_skills","") if rows else ""

            # RAG: find matching trainings from catalog
            try:
                rag_context = query_index(
                    index_name="gold.talentpulse.training_catalog_index",
                    query=f"courses to learn: {missing or target_role}",
                    top_k=5,
                )
            except Exception:
                rag_context = None

            answer = (
                f"**Learning Path for {employee_name}**:\n"
                f"Based on your skill gaps ({missing}), here are recommended steps:\n"
            )
            if rag_context:
                answer += f"\n{rag_context[:800]}"
            else:
                answer += "\n_(Connect Training Catalog vector index for personalised paths.)_"

            return {"answer": answer, "data": rows, "chart_hint": "table", "rag_context": rag_context}

        else:
            return {"answer": f"Unknown question_type '{qt}'.", "data": [],
                    "chart_hint": "table", "rag_context": None}

    except Exception as exc:
        return {"answer": f"Error in Skill Gap Agent: {exc}", "data": [],
                "chart_hint": "table", "rag_context": None}
