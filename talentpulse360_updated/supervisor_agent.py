"""
Supervisor Agent – TalentPulse360
─────────────────────────────────────────────────────────────────────────────
This is the SINGLE agent that users interact with.
It:
  1. Receives the user's natural-language question.
  2. Uses an LLM (Llama-3.1-70B via Databricks) to classify intent.
  3. Routes to the correct specialist agent.
  4. Returns a unified, formatted response.

Deployed as a Databricks Mosaic AI Agent (LangChain AgentExecutor +
UCFunctionToolkit) via MLflow AI Gateway.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import json
import re
import mlflow
import yaml
from pathlib import Path
from typing import Any

from langchain_databricks import ChatDatabricks
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool

# ── Import all specialist agents ──────────────────────────────────────────────
from agents.attendance_agent   import attendance_agent
from agents.training_agent     import training_agent
from agents.performance_agent  import performance_agent
from agents.skill_gap_agent    import skill_gap_agent
from agents.employee360_agent  import employee360_agent
from agents.prediction_agent   import prediction_agent
from agents.workforce_agent    import workforce_insights_agent
from agents.rag_agent          import rag_knowledge_agent

_CFG_PATH = Path(__file__).parent / "config" / "config.yaml"
with open(_CFG_PATH) as f:
    _CFG = yaml.safe_load(f)

# ─────────────────────────────────────────────────────────────────────────────
# LangChain Tool definitions  (wraps each specialist agent)
# ─────────────────────────────────────────────────────────────────────────────

@tool
def tool_attendance(employee_name: str, question_type: str = "summary",
                    employee_id: str = "", month: str = "", top_n: int = 10) -> str:
    """
    Use for attendance questions: present days, absent days, WFH days,
    leave count, effective working hours, monthly attendance trends,
    or finding employees with low attendance.
    question_type options: summary | wfh_days | effective_hours | leave_count |
    monthly_trend | low_attendance_employees
    """
    result = attendance_agent(employee_name, employee_id, question_type, month, top_n)
    return result["answer"]


@tool
def tool_training(employee_name: str, question_type: str = "completed",
                  employee_id: str = "", quarter: str = "", top_n: int = 10) -> str:
    """
    Use for training / learning questions: completed trainings, pending trainings,
    training completion percentage, last quarter learning activity,
    or employees who need training.
    question_type options: completed | pending | completion_pct | last_quarter |
    needs_training
    """
    result = training_agent(employee_name, employee_id, question_type, quarter, top_n)
    return result["answer"]


@tool
def tool_performance(employee_name: str, question_type: str = "summary",
                     employee_id: str = "", top_n: int = 10) -> str:
    """
    Use for performance questions: overall scores, manager ratings, KRA ratings,
    compare attendance vs performance, or get top performers.
    question_type options: summary | manager_ratings | kra_ratings |
    compare_attendance_performance | top_performers
    """
    result = performance_agent(employee_name, employee_id, question_type, top_n)
    return result["answer"]


@tool
def tool_skill_gap(employee_name: str, question_type: str = "gap_analysis",
                   employee_id: str = "", target_role: str = "") -> str:
    """
    Use for skill questions: current skills an employee has, required skills for
    a role, skill gap analysis, or recommended learning path.
    question_type options: current_skills | required_skills | gap_analysis |
    learning_path
    """
    result = skill_gap_agent(employee_name, employee_id, question_type, target_role)
    return result["answer"]


@tool
def tool_employee360(employee_name: str, question_type: str = "full_profile",
                     employee_id: str = "") -> str:
    """
    Use for 360-degree employee profile questions: full combined profile,
    composite employee score, promotion readiness, or employee ranking.
    question_type options: full_profile | employee_score | promotion_readiness |
    ranking
    """
    result = employee360_agent(employee_name, employee_id, question_type)
    return result["answer"]


@tool
def tool_prediction(employee_name: str, prediction_type: str = "attendance",
                    employee_id: str = "") -> str:
    """
    Use to predict FUTURE values: predict next month attendance rate, predict
    next quarter performance score, or predict promotion readiness probability.
    prediction_type options: attendance | performance | promotion
    """
    result = prediction_agent(employee_name, employee_id, prediction_type)
    return result["answer"]


@tool
def tool_workforce(question_type: str = "top_performers",
                   department: str = "", top_n: int = 10) -> str:
    """
    Use for WORKFORCE-WIDE questions (no specific employee): top performers,
    employees with low attendance, employees needing training,
    promotion-ready employees, or department-level summary.
    question_type options: top_performers | low_attendance | needs_training |
    promotion_ready | dept_summary
    """
    result = workforce_insights_agent(question_type, department, top_n)
    return result["answer"]


@tool
def tool_rag_knowledge(query: str, index_type: str = "auto") -> str:
    """
    Use for HR policy questions, career path queries, skill framework lookups,
    or training catalog searches. This searches internal HR documents.
    index_type options: hr_policy | career_path | skill_framework |
    training_catalog | auto
    """
    result = rag_knowledge_agent(query, index_type)
    return result["answer"]


# ─────────────────────────────────────────────────────────────────────────────
# Supervisor prompt
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are TalentPulse360, an intelligent HR AI Assistant for managers
and HR teams. You help answer questions about employees' attendance, training, 
performance, skills, and career growth.

You have access to 8 specialist tools. Always choose the most appropriate tool:

- tool_attendance      → attendance, WFH, leaves, working hours, attendance trends
- tool_training        → training completed/pending, completion %, learning activity
- tool_performance     → performance scores, KRA ratings, manager ratings
- tool_skill_gap       → current skills, required skills, skill gaps, learning path
- tool_employee360     → full 360° profile, composite score, promotion readiness, ranking
- tool_prediction      → PREDICT future attendance / performance / promotion
- tool_workforce       → top performers, low attendance, needs training (workforce-wide)
- tool_rag_knowledge   → HR policies, career paths, skill frameworks, training catalog

Guidelines:
- Extract employee names from the question automatically.
- For "Show Mahesh attendance summary" → use tool_attendance with employee_name="Mahesh".
- For "Top performers" (no name given) → use tool_workforce.
- For "What is the leave policy?" → use tool_rag_knowledge.
- For "Predict next month attendance" → use tool_prediction.
- Always respond in a clear, friendly, professional tone.
- Format numbers neatly. Use markdown for structured data.
- If multiple dimensions are requested (e.g., "show attendance and performance"),
  call multiple tools and combine the answers.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Build the LangChain Agent
# ─────────────────────────────────────────────────────────────────────────────

ALL_TOOLS = [
    tool_attendance,
    tool_training,
    tool_performance,
    tool_skill_gap,
    tool_employee360,
    tool_prediction,
    tool_workforce,
    tool_rag_knowledge,
]


def build_agent() -> AgentExecutor:
    """Build and return the Supervisor AgentExecutor."""
    llm = ChatDatabricks(
        endpoint=_CFG["agent"]["llm_model"],
        temperature=_CFG["agent"]["temperature"],
        max_tokens=_CFG["agent"]["max_tokens"],
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm=llm, tools=ALL_TOOLS, prompt=prompt)
    return AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True,
    )


# ── MLflow model wrapper for Databricks Agent serving ─────────────────────────
class TalentPulse360Agent(mlflow.pyfunc.PythonModel):
    """MLflow wrapper so the agent can be deployed as a Model Serving endpoint."""

    def load_context(self, context):
        self._agent = build_agent()

    def predict(self, context, model_input, params=None):
        messages = model_input.get("messages", [])
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in messages[:-1]
        ]
        user_input = messages[-1]["content"] if messages else ""
        result = self._agent.invoke({
            "input": user_input,
            "chat_history": history,
        })
        return {"choices": [{"message": {"role": "assistant", "content": result["output"]}}]}


# ── Direct invocation (for testing) ──────────────────────────────────────────
def chat(question: str, history: list[dict] | None = None) -> str:
    agent = build_agent()
    result = agent.invoke({"input": question, "chat_history": history or []})
    return result["output"]


# ─────────────────────────────────────────────────────────────────────────────
# Registration helper  (run from a notebook)
# ─────────────────────────────────────────────────────────────────────────────
def register_agent():
    """Log and register the agent to MLflow / Databricks UC Model Registry."""
    import mlflow
    mlflow.set_registry_uri("databricks-uc")
    mlflow.set_experiment(_CFG["mlflow"]["experiment_base"] + "/supervisor")

    with mlflow.start_run(run_name="talentpulse360-supervisor"):
        mlflow.pyfunc.log_model(
            artifact_path="agent",
            python_model=TalentPulse360Agent(),
            registered_model_name="gold.talentpulse.talentpulse360_supervisor",
            pip_requirements=[
                "databricks-agents>=0.8.0",
                "langchain>=0.2.0",
                "langchain-databricks>=0.1.0",
            ],
        )
    print("Agent registered to gold.talentpulse.talentpulse360_supervisor")


if __name__ == "__main__":
    print(chat("Show Mahesh attendance summary"))
