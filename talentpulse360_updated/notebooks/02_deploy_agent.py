# Databricks Notebook — Deploy TalentPulse360 Supervisor Agent
# ─────────────────────────────────────────────────────────────────────────────
# CELL 1: Install dependencies
# ─────────────────────────────────────────────────────────────────────────────
# %pip install databricks-agents langchain langchain-databricks mlflow
# dbutils.library.restartPython()

# ─────────────────────────────────────────────────────────────────────────────
# CELL 2: Register the Supervisor Agent to UC Model Registry
# ─────────────────────────────────────────────────────────────────────────────
import sys
sys.path.insert(0, "/Workspace/Repos/YOUR_USER/talentpulse360")

import mlflow
from supervisor_agent import TalentPulse360Agent

mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment("/Shared/TalentPulse360/supervisor")

with mlflow.start_run(run_name="talentpulse360-supervisor-v1"):
    mlflow.pyfunc.log_model(
        artifact_path="agent",
        python_model=TalentPulse360Agent(),
        registered_model_name="gold.talentpulse.talentpulse360_supervisor",
        pip_requirements=[
            "databricks-sdk>=0.28.0",
            "databricks-agents>=0.8.0",
            "langchain>=0.2.0",
            "langchain-databricks>=0.1.0",
            "databricks-vectorsearch>=0.40",
            "mlflow>=2.13.0",
        ],
    )
    print("✓ Model logged")

# ─────────────────────────────────────────────────────────────────────────────
# CELL 3: Set Production alias
# ─────────────────────────────────────────────────────────────────────────────
from mlflow import MlflowClient
client = MlflowClient()

model_name = "gold.talentpulse.talentpulse360_supervisor"
versions = client.search_model_versions(f"name='{model_name}'")
latest = max(versions, key=lambda v: int(v.version))
client.set_registered_model_alias(name=model_name, alias="Production",
                                   version=latest.version)
print(f"✓ {model_name} v{latest.version} → Production")

# ─────────────────────────────────────────────────────────────────────────────
# CELL 4: Deploy to Model Serving endpoint
# ─────────────────────────────────────────────────────────────────────────────
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import (
    EndpointCoreConfigInput, ServedEntityInput, AutoCaptureConfigInput
)

w = WorkspaceClient()
ENDPOINT_NAME = "talentpulse360-supervisor-agent"

try:
    w.serving_endpoints.create_and_wait(
        name=ENDPOINT_NAME,
        config=EndpointCoreConfigInput(
            served_entities=[
                ServedEntityInput(
                    entity_name=model_name,
                    entity_version=str(latest.version),
                    workload_size="Small",
                    scale_to_zero_enabled=True,
                )
            ]
        ),
        auto_capture_config=AutoCaptureConfigInput(
            catalog_name="gold",
            schema_name="talentpulse",
            table_name_prefix="talentpulse360_inference",
            enabled=True,
        ),
    )
    print(f"✓ Endpoint '{ENDPOINT_NAME}' created and ready")
except Exception as e:
    if "already exists" in str(e):
        print(f"Endpoint already exists — updating config")
        w.serving_endpoints.update_config_and_wait(
            name=ENDPOINT_NAME,
            served_entities=[
                ServedEntityInput(
                    entity_name=model_name,
                    entity_version=str(latest.version),
                    workload_size="Small",
                    scale_to_zero_enabled=True,
                )
            ]
        )
    else:
        raise

# ─────────────────────────────────────────────────────────────────────────────
# CELL 5: Smoke test the endpoint
# ─────────────────────────────────────────────────────────────────────────────
import json

resp = w.serving_endpoints.query(
    name=ENDPOINT_NAME,
    messages=[{"role": "user", "content": "Show Mahesh attendance summary"}],
)
print("Agent response:")
print(resp.choices[0].message.content)

# ─────────────────────────────────────────────────────────────────────────────
# CELL 6: Deploy Streamlit App as a Databricks App
# ─────────────────────────────────────────────────────────────────────────────
# In Databricks UI:
# 1. Go to "Apps" in the left navigation
# 2. Click "Create App"
# 3. Select "Custom App"
# 4. Upload the app/ folder or point to the Workspace path
# 5. Set the command: streamlit run app.py --server.port 8501
# 6. Set environment variables:
#    - DATABRICKS_HOST  = your workspace URL
#    - DATABRICKS_TOKEN = (use service principal or PAT)
# 7. Click Deploy

print("""
╔══════════════════════════════════════════════════════════╗
║       TalentPulse360 Deployment Complete!               ║
╠══════════════════════════════════════════════════════════╣
║ ✓ 8 Specialist Agents deployed                          ║
║ ✓ Supervisor Agent registered in UC Model Registry      ║
║ ✓ Model Serving endpoint: talentpulse360-supervisor-agent║
║ ✓ Inference logging enabled → gold.talentpulse.*        ║
╚══════════════════════════════════════════════════════════╝
""")
