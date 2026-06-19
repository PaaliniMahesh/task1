"""
src/tools.py
─────────────────────────────────────────────────────────────────────────────
LangChain Tool definitions for Employee360 AI.
21 tools mapping to Gold table queries via DatabaseConnector.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.tools import tool

from src.db_connector import DatabaseConnector

logger = logging.getLogger(__name__)

_conn: DatabaseConnector | None = None


def init_tools(connector: DatabaseConnector) -> None:
    global _conn
    _conn = connector


def _require_conn() -> DatabaseConnector:
    if _conn is None:
        raise RuntimeError("Call init_tools(connector) before using tools.")
    return _conn


def _fmt(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


# ── Core ──────────────────────────────────────────────────────────────────────

@tool
def search_employee(name: str) -> str:
    """Search employees by partial name. Returns employee_id, name, department,
    designation, location, manager, health status. Use this FIRST to resolve
    an employee name to their ID before calling other tools.
    Args: name (str) — partial or full name e.g. 'Mahesh', 'Nagesh Varma'"""
    try:
        results = _require_conn().search_employees(name)
        return _fmt(results) if results else f"No employees found matching '{name}'."
    except Exception as e:
        return f"Error: {e}"


@tool
def get_employee_full_profile(employee_id: str) -> str:
    """Retrieve the complete 360-degree profile across ALL 7 Gold tables:
    identity, attendance, training, performance, ranking, promotion, AI predictions.
    Use for 'full profile', 'Employee360', or 'complete overview' requests.
    Args: employee_id (str) — e.g. 'EMP0008'"""
    try:
        return _fmt(_require_conn().get_full_employee_profile(employee_id))
    except Exception as e:
        return f"Error: {e}"


@tool
def get_workforce_summary() -> str:
    """Return aggregate workforce health: headcount, on-track vs at-risk,
    average talent score, average attendance %, average training completion %,
    and department-level breakdown. Use for org-level or dashboard questions."""
    try:
        return _fmt({
            "overall": _require_conn().get_workforce_summary(),
            "by_department": _require_conn().get_department_summary(),
        })
    except Exception as e:
        return f"Error: {e}"


# ── Attendance ────────────────────────────────────────────────────────────────

@tool
def get_attendance_summary(employee_id: str) -> str:
    """Get attendance data for one employee: present days, leave days, WFH days,
    effective hours, attendance %, trend, overtime hours, break time.
    Args: employee_id (str) — e.g. 'EMP0008'"""
    try:
        data = _require_conn().get_attendance(employee_id)
        return _fmt(data) if data else f"No attendance data found for {employee_id}."
    except Exception as e:
        return f"Error: {e}"


@tool
def get_attendance_at_risk_employees(threshold: float = 80.0) -> str:
    """List employees with attendance below threshold %. Default threshold 80%.
    Args: threshold (float) — minimum acceptable attendance %"""
    try:
        data = _require_conn().get_attendance_at_risk(threshold)
        return _fmt(data) if data else f"No employees found with attendance below {threshold}%."
    except Exception as e:
        return f"Error: {e}"


@tool
def get_wfh_analysis(department: str = "") -> str:
    """Analyse WFH utilisation org-wide or filtered by department.
    Args: department (str) — optional e.g. 'AI/ML', 'DE', 'DevOps'"""
    try:
        return _fmt(_require_conn().get_wfh_analysis(department.strip() or None))
    except Exception as e:
        return f"Error: {e}"


# ── Training ──────────────────────────────────────────────────────────────────

@tool
def get_training_summary(employee_id: str) -> str:
    """Get training data for one employee: assigned/completed/pending courses,
    completion %, total hours, last training completed.
    Args: employee_id (str) — e.g. 'EMP0008'"""
    try:
        data = _require_conn().get_training(employee_id)
        return _fmt(data) if data else f"No training data found for {employee_id}."
    except Exception as e:
        return f"Error: {e}"


@tool
def get_employees_with_pending_training() -> str:
    """List all employees who have pending or in-progress trainings.
    Useful for identifying learning gaps and L&D intervention priorities."""
    try:
        return _fmt(_require_conn().get_pending_trainings())
    except Exception as e:
        return f"Error: {e}"


@tool
def get_training_at_risk_employees() -> str:
    """List employees with 0% training completion who have been assigned
    at least one training. These require immediate L&D attention."""
    try:
        return _fmt(_require_conn().get_training_at_risk())
    except Exception as e:
        return f"Error: {e}"


# ── Performance ───────────────────────────────────────────────────────────────

@tool
def get_performance_summary(employee_id: str) -> str:
    """Get KRA performance data for one employee: ratings, performance band,
    self vs manager rating, top areas, improvement areas, rating gap.
    Args: employee_id (str) — e.g. 'EMP0008'"""
    try:
        data = _require_conn().get_performance(employee_id)
        return _fmt(data) if data else f"No performance data found for {employee_id}."
    except Exception as e:
        return f"Error: {e}"


@tool
def get_performance_by_department(department: str) -> str:
    """Get performance summary for all employees in a department.
    Args: department (str) — e.g. 'AI/ML', 'DE', 'HR', 'DevOps'"""
    try:
        data = _require_conn().get_performance_by_department(department)
        return _fmt(data) if data else f"No performance data found for department '{department}'."
    except Exception as e:
        return f"Error: {e}"


@tool
def get_employees_needing_performance_improvement() -> str:
    """List employees in 'Below Expectations' or 'Needs Improvement' bands.
    These employees require manager attention and possibly a PIP."""
    try:
        data = _require_conn().get_performance_by_band("Below")
        if not data:
            data = _require_conn().get_performance_by_band("Needs")
        return _fmt(data)
    except Exception as e:
        return f"Error: {e}"


# ── Ranking ───────────────────────────────────────────────────────────────────

@tool
def get_employee_ranking(employee_id: str) -> str:
    """Get ranking data for one employee: overall rank, department rank,
    designation rank, performance quartile, talent tier.
    Args: employee_id (str) — e.g. 'EMP0008'"""
    try:
        data = _require_conn().get_ranking(employee_id)
        return _fmt(data) if data else f"No ranking data found for {employee_id}."
    except Exception as e:
        return f"Error: {e}"


@tool
def get_top_performers(count: int = 10, department: str = "") -> str:
    """Get top N performers by composite talent score, org-wide or by department.
    Args: count (int) — number to return (default 10)
          department (str) — optional filter"""
    try:
        return _fmt(_require_conn().get_top_performers(count, department.strip() or None))
    except Exception as e:
        return f"Error: {e}"


@tool
def get_department_rankings(department: str) -> str:
    """Get internal ranking of all employees within a department.
    Args: department (str) — e.g. 'AI/ML', 'DE', 'Testing'"""
    try:
        data = _require_conn().get_department_rankings(department)
        return _fmt(data) if data else f"No ranking data found for department '{department}'."
    except Exception as e:
        return f"Error: {e}"


# ── Promotion ─────────────────────────────────────────────────────────────────

@tool
def get_promotion_readiness(employee_id: str) -> str:
    """Get promotion readiness assessment for one employee: readiness score,
    status, recommended next role, estimated timeline, specific gaps.
    Args: employee_id (str) — e.g. 'EMP0008'"""
    try:
        data = _require_conn().get_promotion(employee_id)
        return _fmt(data) if data else f"No promotion data found for {employee_id}."
    except Exception as e:
        return f"Error: {e}"


@tool
def get_promotion_ready_list(status: str = "Nearly Ready", department: str = "") -> str:
    """List employees ready (or nearly ready) for promotion.
    Status options: 'Nearly Ready', 'Promotion Ready', 'Development Needed'.
    Args: status (str) — filter by readiness status
          department (str) — optional department filter"""
    try:
        data = _require_conn().get_promotion_ready_employees(status, department.strip() or None)
        return _fmt(data) if data else f"No employees found with status '{status}'."
    except Exception as e:
        return f"Error: {e}"


@tool
def get_skill_gap_for_target_role(target_role: str) -> str:
    """Identify employees targeting a role and show their skill gaps.
    Useful for succession planning and role transition analysis.
    Args: target_role (str) — e.g. 'Senior Data Engineer', 'Databricks Data Engineer'"""
    try:
        data = _require_conn().get_skill_gap_for_role(target_role)
        return _fmt(data) if data else f"No employees found targeting '{target_role}'."
    except Exception as e:
        return f"Error: {e}"


# ── AI Predictions ────────────────────────────────────────────────────────────

@tool
def get_ai_predictions_for_employee(employee_id: str) -> str:
    """Get ML model predictions for one employee: predicted next-month attendance %,
    predicted next-quarter performance score, confidence level, risk flags.
    Args: employee_id (str) — e.g. 'EMP0008'"""
    try:
        data = _require_conn().get_ai_predictions(employee_id)
        return _fmt(data) if data else f"No AI predictions found for {employee_id}."
    except Exception as e:
        return f"Error: {e}"


@tool
def get_high_risk_predictions() -> str:
    """List employees the AI model predicts will have low attendance (<70%) next month,
    or who have combined attendance + training risk flags. Proactive intervention targets."""
    try:
        return _fmt(_require_conn().get_high_risk_predictions())
    except Exception as e:
        return f"Error: {e}"


# ── Registry ──────────────────────────────────────────────────────────────────

ALL_TOOLS = [
    search_employee,
    get_employee_full_profile,
    get_workforce_summary,
    get_attendance_summary,
    get_attendance_at_risk_employees,
    get_wfh_analysis,
    get_training_summary,
    get_employees_with_pending_training,
    get_training_at_risk_employees,
    get_performance_summary,
    get_performance_by_department,
    get_employees_needing_performance_improvement,
    get_employee_ranking,
    get_top_performers,
    get_department_rankings,
    get_promotion_readiness,
    get_promotion_ready_list,
    get_skill_gap_for_target_role,
    get_ai_predictions_for_employee,
    get_high_risk_predictions,
]

TOOL_MAP = {t.name: t for t in ALL_TOOLS}
