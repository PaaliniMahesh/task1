"""
src/agents.py
─────────────────────────────────────────────────────────────────────────────
Employee360 AI — Multi-Agent Orchestrator

  User Query
       │
  RouterAgent  (intent classification via keyword matching)
       │
  Tool Executor (queries Gold tables via LangChain tools)
       │
  RAG Pipeline  (retrieves relevant HR knowledge)
       │
  Claude Sonnet (synthesizes final response)
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import logging
import re
import time
from enum import Enum
from typing import Any

import mlflow
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

import config as cfg
from src.db_connector import DatabaseConnector
from src.rag.rag_pipeline import RAGPipeline
from src.tools import ALL_TOOLS, TOOL_MAP, init_tools, search_employee

logger = logging.getLogger(__name__)


# ── Intent enum ───────────────────────────────────────────────────────────────

class QueryIntent(str, Enum):
    EMPLOYEE_360 = "employee_360"
    ATTENDANCE   = "attendance"
    TRAINING     = "training"
    PERFORMANCE  = "performance"
    RANKING      = "ranking"
    PROMOTION    = "promotion"
    PREDICTION   = "prediction"
    WORKFORCE    = "workforce"
    GENERAL      = "general"


# ── System prompts ────────────────────────────────────────────────────────────

_BASE = """
You are Employee360 AI, an Agentic Workforce Intelligence Assistant for Bilvantis,
built on Databricks. You answer questions from HR managers and team leads about
employee performance, attendance, training, promotion readiness, and workforce trends.

You query 7 Gold Layer tables in gold.talentpulse:
  employee_360, employee_attendance_summary, employee_training_summary,
  employee_performance_summary, employee_ranking, promotion_readiness,
  employee_ai_features

RESPONSE RULES:
- Always cite specific numbers from the data provided
- Structure responses with clear bold headers for complex profiles
- Highlight risk flags (att_risk, tr_risk, perf_risk) proactively
- For promotion queries: explain EXACTLY what gaps need closing
- For workforce queries: surface patterns and actionable recommendations
- talent_score: 0-100; promo_score: 0-100 (higher = better)
- pred_att and pred_perf are AI-generated — label them as AI forecasts
- When an employee name is mentioned, their ID has already been resolved
- Keep responses concise but complete
"""

SYSTEM_PROMPTS = {
    QueryIntent.EMPLOYEE_360: _BASE + """
TASK: Complete Employee360 profile with these sections:
  👤 Identity — name, role, dept, tenure, manager
  📊 Attendance — attendance %, WFH days, effective hrs, trend
  📚 Training — completion %, courses done, pending
  ⭐ Performance — KRA score, band, top areas, improvement areas
  🏆 Ranking — overall rank, dept rank, performance tier
  🚀 Promotion — readiness score, status, next role, timeline, gaps
  🤖 AI Forecast — predicted attendance and performance
""",
    QueryIntent.ATTENDANCE: _BASE + "TASK: Answer attendance questions. Focus on attendance %, WFH, effective hours, overtime, leave patterns.",
    QueryIntent.TRAINING: _BASE + "TASK: Answer training/L&D questions. Focus on completion rates, pending courses, hours, skill gaps.",
    QueryIntent.PERFORMANCE: _BASE + "TASK: Answer performance/KRA questions. Focus on scores, rating gaps, performance bands, top/improvement areas.",
    QueryIntent.RANKING: _BASE + "TASK: Answer ranking questions. Focus on composite talent scores, ranks, tiers, percentiles.",
    QueryIntent.PROMOTION: _BASE + """TASK: Answer promotion readiness questions. Always specify:
  1. Current readiness score and status
  2. Exact gaps to close (performance, training, attendance, tenure)
  3. Recommended next designation
  4. Estimated timeline
  5. Specific action items to accelerate readiness""",
    QueryIntent.PREDICTION: _BASE + "TASK: Answer AI prediction questions. Always label predictions as AI-generated estimates. Explain confidence levels.",
    QueryIntent.WORKFORCE: _BASE + "TASK: Answer workforce-level questions. Focus on dept health, risk distribution, talent spread, actionable recommendations.",
    QueryIntent.GENERAL: _BASE,
}

# Intent keyword patterns
_PATTERNS = [
    (QueryIntent.EMPLOYEE_360, ["360", "full profile", "complete profile", "overview", "tell me about", "who is", "summary of"]),
    (QueryIntent.ATTENDANCE,   ["attendance", "present", "absent", "leave", "wfh", "work from home", "effective hours", "overtime"]),
    (QueryIntent.TRAINING,     ["training", "course", "learning", "certification", "completion", "upskill", "l&d", "pending"]),
    (QueryIntent.PERFORMANCE,  ["performance", "kra", "rating", "feedback", "score", "band", "exceeds", "meets expectations", "appraisal"]),
    (QueryIntent.RANKING,      ["rank", "ranking", "top performer", "best employee", "leaderboard", "tier", "talent score", "percentile"]),
    (QueryIntent.PROMOTION,    ["promot", "career", "next role", "ready for", "transition", "move to", "skill gap", "succession", "growth"]),
    (QueryIntent.PREDICTION,   ["predict", "forecast", "next month", "next quarter", "future", "ai model", "risk flag"]),
    (QueryIntent.WORKFORCE,    ["workforce", "department", "organisation", "org", "headcount", "intervention", "at risk employees"]),
]

# Tools per intent
_INTENT_TOOLS = {
    QueryIntent.EMPLOYEE_360: ["search_employee", "get_employee_full_profile", "get_ai_predictions_for_employee"],
    QueryIntent.ATTENDANCE:   ["search_employee", "get_attendance_summary", "get_attendance_at_risk_employees", "get_wfh_analysis"],
    QueryIntent.TRAINING:     ["search_employee", "get_training_summary", "get_employees_with_pending_training", "get_training_at_risk_employees"],
    QueryIntent.PERFORMANCE:  ["search_employee", "get_performance_summary", "get_performance_by_department", "get_employees_needing_performance_improvement"],
    QueryIntent.RANKING:      ["search_employee", "get_employee_ranking", "get_top_performers", "get_department_rankings"],
    QueryIntent.PROMOTION:    ["search_employee", "get_promotion_readiness", "get_promotion_ready_list", "get_skill_gap_for_target_role"],
    QueryIntent.PREDICTION:   ["search_employee", "get_ai_predictions_for_employee", "get_high_risk_predictions"],
    QueryIntent.WORKFORCE:    ["get_workforce_summary", "get_top_performers", "get_attendance_at_risk_employees",
                               "get_training_at_risk_employees", "get_promotion_ready_list", "get_high_risk_predictions"],
    QueryIntent.GENERAL:      [t.name for t in ALL_TOOLS],
}


def classify_intent(query: str) -> QueryIntent:
    q = query.lower()
    scores = {i: 0 for i in QueryIntent}
    for intent, keywords in _PATTERNS:
        for kw in keywords:
            if kw in q:
                scores[intent] += 1
    best = max(scores, key=lambda k: scores[k])
    return best if scores[best] > 0 else QueryIntent.GENERAL


# ── Orchestrator ──────────────────────────────────────────────────────────────

class Employee360Orchestrator:

    def __init__(self, use_spark: bool = True, enable_rag: bool = True, enable_mlflow: bool = True):
        self.use_spark     = use_spark
        self.enable_rag    = enable_rag
        self.enable_mlflow = enable_mlflow
        self._connector    = None
        self._rag          = None
        self._llm          = None
        self._history: list[dict] = []
        self._mlflow_run   = None

    def initialize(self) -> "Employee360Orchestrator":
        self._connector = DatabaseConnector(use_spark=self.use_spark)
        init_tools(self._connector)
        self._llm = ChatAnthropic(
            api_key=cfg.anthropic_cfg.api_key,
            model=cfg.anthropic_cfg.model,
            max_tokens=cfg.anthropic_cfg.max_tokens,
            temperature=cfg.anthropic_cfg.temperature,
        )
        if self.enable_rag:
            self._rag = RAGPipeline().build()
        if self.enable_mlflow:
            try:
                mlflow.set_experiment(cfg.mlflow_cfg.experiment_name)
                self._mlflow_run = mlflow.start_run(
                    run_name=f"{cfg.mlflow_cfg.run_name_prefix}_{int(time.time())}"
                )
            except Exception as e:
                logger.warning("MLflow init failed: %s", e)
        logger.info("Employee360 Orchestrator ready.")
        return self

    def chat(self, user_query: str) -> str:
        start = time.time()
        intent     = classify_intent(user_query)
        emp_id     = self._resolve_employee_id(user_query)
        tool_data  = self._execute_tools(user_query, intent, emp_id)
        rag_ctx    = self._rag.retrieve(user_query) if (self.enable_rag and self._rag) else ""
        response   = self._synthesize(user_query, intent, tool_data, rag_ctx)

        self._history.append({"role": "user",      "content": user_query})
        self._history.append({"role": "assistant", "content": response})
        max_turns = cfg.app.max_history_turns * 2
        if len(self._history) > max_turns:
            self._history = self._history[-max_turns:]

        if self.enable_mlflow:
            self._log_mlflow(user_query, intent, response, time.time() - start)
        return response

    def _resolve_employee_id(self, query: str) -> str | None:
        candidates = re.findall(r'\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\b', query)
        stopwords = {"Show", "What", "Which", "Give", "List", "Find", "Tell",
                     "Who", "How", "Can", "Has", "The", "For", "With", "Is"}
        for name in candidates:
            if name.split()[0] in stopwords:
                continue
            try:
                import json
                result = search_employee.invoke({"name": name})
                rows = json.loads(result)
                if rows:
                    return rows[0]["employee_id"]
            except Exception:
                continue
        return None

    def _execute_tools(self, query: str, intent: QueryIntent, employee_id: str | None) -> dict:
        tool_names = _INTENT_TOOLS.get(intent, [t.name for t in ALL_TOOLS])
        results = {}
        for name in tool_names:
            fn = TOOL_MAP.get(name)
            if fn is None:
                continue
            try:
                if employee_id and name in (
                    "get_employee_full_profile", "get_attendance_summary",
                    "get_training_summary", "get_performance_summary",
                    "get_employee_ranking", "get_promotion_readiness",
                    "get_ai_predictions_for_employee",
                ):
                    results[name] = fn.invoke({"employee_id": employee_id})

                elif name == "get_top_performers":
                    results[name] = fn.invoke({"count": 10})

                elif name in (
                    "get_attendance_at_risk_employees", "get_training_at_risk_employees",
                    "get_employees_with_pending_training",
                    "get_employees_needing_performance_improvement",
                    "get_high_risk_predictions", "get_workforce_summary",
                ):
                    results[name] = fn.invoke({})

                elif name == "get_promotion_ready_list":
                    results[name] = fn.invoke({"status": "Nearly Ready"})

                elif name == "get_skill_gap_for_target_role":
                    m = re.search(r'(?:to|for|as)\s+(?:a\s+|an\s+)?(.{5,40}?)(?:\s+role|\?|$)', query, re.I)
                    if m:
                        results[name] = fn.invoke({"target_role": m.group(1).strip()})

                elif name == "get_performance_by_department":
                    m = re.search(r'\b(AI/ML|DE|CDE|DevOps|HR|Testing|Power BI|Heritage|'
                                  r'Business Deployment|Support Team)\b', query, re.I)
                    if m:
                        results[name] = fn.invoke({"department": m.group(1)})

                elif name == "get_department_rankings":
                    m = re.search(r'\b(AI/ML|DE|CDE|DevOps|HR|Testing|Power BI|Heritage|'
                                  r'Business Deployment|Support Team)\b', query, re.I)
                    if m:
                        results[name] = fn.invoke({"department": m.group(1)})

            except Exception as e:
                logger.warning("Tool %s failed: %s", name, e)
        return results

    def _synthesize(self, query: str, intent: QueryIntent, tool_data: dict, rag_ctx: str) -> str:
        system = SYSTEM_PROMPTS.get(intent, SYSTEM_PROMPTS[QueryIntent.GENERAL])
        sections = []
        for name, result in tool_data.items():
            if result and not str(result).startswith("Error"):
                truncated = str(result)[:3000]
                sections.append(f"[{name.upper()}]\n{truncated}")
        data_block = "\n\n".join(sections) if sections else "No data retrieved."

        messages = [SystemMessage(content=system)]
        for turn in self._history[-6:]:
            if turn["role"] == "user":
                messages.append(HumanMessage(content=turn["content"]))
            else:
                messages.append(AIMessage(content=turn["content"]))

        user_content = f"USER QUESTION: {query}\n\n--- GOLD LAYER DATA ---\n{data_block}\n--- END DATA ---"
        if rag_ctx:
            user_content += f"\n\n{rag_ctx}"
        messages.append(HumanMessage(content=user_content))

        try:
            resp: AIMessage = self._llm.invoke(messages)
            return resp.content
        except Exception as e:
            logger.error("LLM synthesis failed: %s", e)
            return f"Error generating response: {e}"

    def _log_mlflow(self, query: str, intent: QueryIntent, response: str, latency: float):
        try:
            mlflow.log_params({"intent": intent.value, "query_length": len(query)})
            mlflow.log_metrics({"response_latency_sec": round(latency, 3), "response_length": len(response)})
        except Exception:
            pass

    def reset_history(self):
        self._history = []

    def close(self):
        if self.enable_mlflow and self._mlflow_run:
            try:
                mlflow.end_run()
            except Exception:
                pass
