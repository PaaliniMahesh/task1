# Databricks notebook source
# MAGIC %md
# MAGIC # Employee360 AI — Streamlit on Databricks
# MAGIC ### Agentic Workforce Intelligence · gold.talentpulse · Streamlit App

# COMMAND ----------
# MAGIC %md
# MAGIC ## 0. Install Dependencies

# COMMAND ----------
# %pip install anthropic langchain langchain-anthropic langchain-community \
#              chromadb sentence-transformers streamlit mlflow --quiet
# dbutils.library.restartPython()

# COMMAND ----------
import os
from pyspark.sql import SparkSession

os.environ["ANTHROPIC_API_KEY"] = dbutils.secrets.get("employee360", "anthropic_api_key")
spark = SparkSession.getActiveSession()
print("✅ Ready. Spark:", spark.version)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 1. Verify Gold Tables

# COMMAND ----------
spark.sql("SHOW TABLES IN gold.talentpulse").show(truncate=False)

# COMMAND ----------
for t in ["employee_360","employee_attendance_summary","employee_training_summary",
          "employee_performance_summary","employee_ranking",
          "promotion_readiness","employee_ai_features"]:
    n = spark.sql(f"SELECT COUNT(*) FROM gold.talentpulse.{t}").collect()[0][0]
    print(f"  gold.talentpulse.{t}: {n:,} rows")

# COMMAND ----------
# MAGIC %md
# MAGIC ## 2. Test Connector & Orchestrator

# COMMAND ----------
import sys
sys.path.insert(0, "/Workspace/Repos/your_name/employee360_streamlit")

from src.db_connector import DatabaseConnector
conn = DatabaseConnector(use_spark=True)
print("Top 3 performers:")
for e in conn.get_top_performers(3):
    print(f"  #{e['overall_rank']} {e['employee_name']} ({e['department']}) — {e['composite_talent_score']}")

# COMMAND ----------
from src.agents import Employee360Orchestrator
orch = Employee360Orchestrator(use_spark=True, enable_rag=True, enable_mlflow=True).initialize()
print("✅ Orchestrator ready")

# COMMAND ----------
# Test queries
for q in [
    "Show the full Employee360 profile for Mahesh Paalini",
    "Who are the top 5 performers?",
    "Is Mahesh ready for promotion?",
    "Which employees need urgent training support?",
]:
    print(f"\nQ: {q}")
    print(orch.chat(q))
    print("-" * 60)

# COMMAND ----------
# MAGIC %md
# MAGIC ## 3. Run Streamlit App
# MAGIC
# MAGIC ### Option A: Databricks App (recommended for production)
# MAGIC 1. Go to **Compute** → **Apps** → **Create App**
# MAGIC 2. Select **Streamlit** as the app type
# MAGIC 3. Point to `/Workspace/Repos/your_name/employee360_streamlit/streamlit_app.py`
# MAGIC 4. Add environment variables:
# MAGIC    - `ANTHROPIC_API_KEY` → from Databricks Secrets
# MAGIC    - `DATABRICKS_HTTP_PATH` → your SQL warehouse path
# MAGIC 5. Click **Deploy**
# MAGIC
# MAGIC ### Option B: Cluster proxy (for testing)

# COMMAND ----------
# import subprocess
# subprocess.Popen(["streamlit", "run", "streamlit_app.py", "--server.port=8501"])
# displayHTML('<a href="/driver-proxy/o/0/8501/" target="_blank">Open Streamlit App</a>')

# COMMAND ----------
# MAGIC %md
# MAGIC ## 4. Gold Layer Analytics (bonus)

# COMMAND ----------
spark.sql("""
    SELECT department,
           COUNT(*) headcount,
           ROUND(AVG(CAST(composite_talent_score AS DOUBLE)),1) avg_score,
           SUM(CASE WHEN employee_health_status='At Risk' THEN 1 ELSE 0 END) at_risk
    FROM gold.talentpulse.employee_360
    GROUP BY department ORDER BY avg_score DESC
""").show(truncate=False)

# COMMAND ----------
spark.sql("""
    SELECT employee_name, department, promotion_readiness_status,
           promotion_readiness_score, recommended_next_designation,
           estimated_months_to_promotion
    FROM gold.talentpulse.promotion_readiness
    WHERE promotion_readiness_status IN ('Nearly Ready','Promotion Ready')
    ORDER BY promotion_readiness_score DESC LIMIT 15
""").show(truncate=False)
