"""
config.py
─────────────────────────────────────────────────────────────────────────────
Central configuration for Employee360 AI.
All settings are read from environment variables (set in Databricks Secrets
or a .env file for local development).
─────────────────────────────────────────────────────────────────────────────
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabricksConfig:
    """Databricks connection settings."""
    host:      str = field(default_factory=lambda: os.getenv("DATABRICKS_HOST", ""))
    token:     str = field(default_factory=lambda: os.getenv("DATABRICKS_TOKEN", ""))
    http_path: str = field(default_factory=lambda: os.getenv("DATABRICKS_HTTP_PATH", ""))
    catalog:   str = "gold"
    schema:    str = "talentpulse"

    # Gold Layer table names
    table_employee_360:        str = "employee_360"
    table_attendance_summary:  str = "employee_attendance_summary"
    table_training_summary:    str = "employee_training_summary"
    table_performance_summary: str = "employee_performance_summary"
    table_ranking:             str = "employee_ranking"
    table_promotion_readiness: str = "promotion_readiness"
    table_ai_features:         str = "employee_ai_features"

    def fqn(self, table: str) -> str:
        """Return fully-qualified table name: catalog.schema.table"""
        return f"{self.catalog}.{self.schema}.{table}"


@dataclass
class AnthropicConfig:
    """Anthropic / Claude settings."""
    api_key:     str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    model:       str = "claude-sonnet-4-6"
    max_tokens:  int = 2048
    temperature: float = 0.1


@dataclass
class RAGConfig:
    """RAG / Vector store settings."""
    use_databricks_vs: bool = field(
        default_factory=lambda: os.getenv("USE_DATABRICKS_VS", "false").lower() == "true"
    )
    vs_endpoint:     str = field(default_factory=lambda: os.getenv("DATABRICKS_VS_ENDPOINT", ""))
    vs_index_name:   str = "talentpulse_hr_knowledge"
    chroma_persist_dir: str = "./chroma_db"
    collection_name:    str = "hr_knowledge_base"
    embedding_model:    str = "all-MiniLM-L6-v2"
    chunk_size:         int = 512
    chunk_overlap:      int = 64
    top_k:              int = 4


@dataclass
class MLflowConfig:
    """MLflow experiment tracking."""
    experiment_name: str  = "/Shared/Employee360_AI"
    run_name_prefix: str  = "employee360"
    log_queries:     bool = True


@dataclass
class AppConfig:
    """Streamlit app settings."""
    title:              str = "Employee360 AI — Workforce Intelligence Assistant"
    max_history_turns:  int = 10


# ── Singleton config objects ──────────────────────────────────────────────────
databricks    = DatabricksConfig()
anthropic_cfg = AnthropicConfig()
rag           = RAGConfig()
mlflow_cfg    = MLflowConfig()
app           = AppConfig()
