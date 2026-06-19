# TalentPulse360 – Agentic AI Employee Assistant
# Built on Databricks Mosaic AI Agent Framework

"""
TalentPulse360
==============

A production-ready Agentic AI system for HR Intelligence.

Architecture:
    Streamlit App → Supervisor Agent → 8 Specialist Agents
                                     → Gold Layer Tables
                                     → RAG Vector Indexes
                                     → MLflow Prediction Models

Agents:
    1. attendance_agent    – Attendance analytics
    2. training_agent      – Learning & development
    3. performance_agent   – Performance management
    4. skill_gap_agent     – Skill gap & learning paths
    5. employee360_agent   – Unified employee profiles
    6. prediction_agent    – ML-based forecasting
    7. workforce_agent     – Workforce insights
    8. rag_agent           – HR knowledge base (RAG)

Supervisor:
    supervisor_agent       – Routes all queries to the right agent
"""
