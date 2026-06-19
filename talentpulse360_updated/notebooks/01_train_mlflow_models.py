# Databricks Notebook — MLflow Model Training
# Run cells sequentially in your Databricks cluster
# ─────────────────────────────────────────────────────────────────────────────
# CELL 1: Setup
# ─────────────────────────────────────────────────────────────────────────────

import mlflow
import mlflow.sklearn
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score
from databricks.feature_store import FeatureStoreClient
import yaml

mlflow.set_registry_uri("databricks-uc")
mlflow.set_experiment("/Shared/TalentPulse360/model-training")

CATALOG = "gold"
SCHEMA  = "talentpulse"
AI_TABLE = f"{CATALOG}.{SCHEMA}.gold_employee_ai_features"

# ─────────────────────────────────────────────────────────────────────────────
# CELL 2: Load feature data
# ─────────────────────────────────────────────────────────────────────────────

df = spark.table(AI_TABLE).toPandas()
print(f"Feature table shape: {df.shape}")
df.head()

# ─────────────────────────────────────────────────────────────────────────────
# CELL 3: Train Attendance Prediction Model
# ─────────────────────────────────────────────────────────────────────────────

ATT_FEATURES = [
    "avg_effective_hours", "total_wfh_days_last3m", "leave_days_last3m",
    "attendance_pct_last3m", "dept_avg_attendance", "team_size",
    "manager_attendance_pct", "day_of_week_pattern",
]
ATT_TARGET = "attendance_pct_next_month"

att_df = df[ATT_FEATURES + [ATT_TARGET]].dropna()
X_att = att_df[ATT_FEATURES]
y_att = att_df[ATT_TARGET]

X_tr, X_te, y_tr, y_te = train_test_split(X_att, y_att, test_size=0.2, random_state=42)

with mlflow.start_run(run_name="attendance-predictor"):
    model = GradientBoostingRegressor(
        n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42
    )
    model.fit(X_tr, y_tr)
    preds = model.predict(X_te)

    mae = mean_absolute_error(y_te, preds)
    r2  = r2_score(y_te, preds)

    mlflow.log_params({"n_estimators": 200, "max_depth": 4, "lr": 0.05})
    mlflow.log_metrics({"mae": mae, "r2": r2})
    mlflow.sklearn.log_model(
        model,
        artifact_path="model",
        registered_model_name=f"{CATALOG}.{SCHEMA}.talentpulse_attendance_predictor",
        input_example=X_te.head(3),
    )
    print(f"Attendance Model — MAE: {mae:.3f}, R²: {r2:.3f}")

# ─────────────────────────────────────────────────────────────────────────────
# CELL 4: Train Performance Prediction Model
# ─────────────────────────────────────────────────────────────────────────────

PERF_FEATURES = [
    "kra_avg_score", "manager_rating_last", "training_completion_pct",
    "attendance_percentage", "skill_score", "goal_completion_pct",
    "engagement_score", "peer_rating",
]
PERF_TARGET = "performance_score_next_quarter"

perf_df = df[PERF_FEATURES + [PERF_TARGET]].dropna()
X_p = perf_df[PERF_FEATURES]
y_p = perf_df[PERF_TARGET]

X_tr2, X_te2, y_tr2, y_te2 = train_test_split(X_p, y_p, test_size=0.2, random_state=42)

with mlflow.start_run(run_name="performance-predictor"):
    model_p = GradientBoostingRegressor(
        n_estimators=150, max_depth=5, learning_rate=0.08, random_state=42
    )
    model_p.fit(X_tr2, y_tr2)
    preds_p = model_p.predict(X_te2)

    mae_p = mean_absolute_error(y_te2, preds_p)
    r2_p  = r2_score(y_te2, preds_p)

    mlflow.log_metrics({"mae": mae_p, "r2": r2_p})
    mlflow.sklearn.log_model(
        model_p,
        artifact_path="model",
        registered_model_name=f"{CATALOG}.{SCHEMA}.talentpulse_performance_predictor",
        input_example=X_te2.head(3),
    )
    print(f"Performance Model — MAE: {mae_p:.3f}, R²: {r2_p:.3f}")

# ─────────────────────────────────────────────────────────────────────────────
# CELL 5: Train Promotion Readiness Model
# ─────────────────────────────────────────────────────────────────────────────

PROMO_FEATURES = [
    "composite_score", "years_in_current_role", "performance_trend_score",
    "skill_readiness_pct", "training_completion_pct", "manager_recommendation_score",
    "attendance_percentage", "leadership_score",
]
PROMO_TARGET = "is_promotion_ready"   # binary 0/1

promo_df = df[PROMO_FEATURES + [PROMO_TARGET]].dropna()
X_pr = promo_df[PROMO_FEATURES]
y_pr = promo_df[PROMO_TARGET].astype(int)

X_tr3, X_te3, y_tr3, y_te3 = train_test_split(X_pr, y_pr, test_size=0.2,
                                                random_state=42, stratify=y_pr)

with mlflow.start_run(run_name="promotion-predictor"):
    model_pr = GradientBoostingClassifier(
        n_estimators=100, max_depth=4, learning_rate=0.1, random_state=42
    )
    model_pr.fit(X_tr3, y_tr3)
    preds_pr = model_pr.predict(X_te3)

    acc = accuracy_score(y_te3, preds_pr)
    mlflow.log_metrics({"accuracy": acc})
    mlflow.sklearn.log_model(
        model_pr,
        artifact_path="model",
        registered_model_name=f"{CATALOG}.{SCHEMA}.talentpulse_promotion_predictor",
        input_example=X_te3.head(3),
    )
    print(f"Promotion Model — Accuracy: {acc:.3f}")

# ─────────────────────────────────────────────────────────────────────────────
# CELL 6: Set all models to Production alias
# ─────────────────────────────────────────────────────────────────────────────

from mlflow import MlflowClient
client = MlflowClient()

MODELS = [
    f"{CATALOG}.{SCHEMA}.talentpulse_attendance_predictor",
    f"{CATALOG}.{SCHEMA}.talentpulse_performance_predictor",
    f"{CATALOG}.{SCHEMA}.talentpulse_promotion_predictor",
]

for model_name in MODELS:
    versions = client.search_model_versions(f"name='{model_name}'")
    latest = max(versions, key=lambda v: int(v.version))
    client.set_registered_model_alias(
        name=model_name, alias="Production", version=latest.version
    )
    print(f"✓ {model_name} v{latest.version} → Production")
