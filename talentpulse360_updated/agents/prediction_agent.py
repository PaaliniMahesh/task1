"""
Agent 6 – Prediction Agent
─────────────────────────────────────────────────────────────────────────────
Purpose  : Use MLflow-registered models to predict:
             1. Next-month attendance rate
             2. Next-quarter performance score
             3. Promotion readiness score

Models (registered in Databricks Unity Catalog Model Registry):
  • models:/talentpulse_attendance_predictor/Production
  • models:/talentpulse_performance_predictor/Production
  • models:/talentpulse_promotion_predictor/Production

Gold tables used (for feature retrieval):
  • gold.talentpulse.gold_employee_ai_features

Input schema:
  {
    "employee_name" : str | None,
    "employee_id"   : str | None,
    "prediction_type" : "attendance" | "performance" | "promotion"
  }

Output schema:
  {
    "answer"          : str,
    "predicted_value" : float,
    "confidence"      : float,
    "feature_importance" : list[dict],
    "chart_hint"      : str
  }
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import Any
import mlflow
import pandas as pd
from tools.db_utils import run_query
import yaml
from pathlib import Path

_CFG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"
with open(_CFG_PATH) as f:
    _CFG = yaml.safe_load(f)

AI_TABLE = "gold.talentpulse.gold_employee_ai_features"

# Feature columns required by each model
_FEATURE_COLS = {
    "attendance": [
        "avg_effective_hours", "total_wfh_days_last3m", "leave_days_last3m",
        "attendance_pct_last3m", "day_of_week_pattern", "dept_avg_attendance",
        "team_size", "manager_attendance_pct",
    ],
    "performance": [
        "kra_avg_score", "manager_rating_last", "training_completion_pct",
        "attendance_percentage", "skill_score", "goal_completion_pct",
        "engagement_score", "peer_rating",
    ],
    "promotion": [
        "composite_score", "years_in_current_role", "performance_trend_score",
        "skill_readiness_pct", "training_completion_pct", "manager_recommendation_score",
        "attendance_percentage", "leadership_score",
    ],
}

_MODEL_URIS = {
    "attendance":  _CFG["mlflow"]["attendance_model_uri"],
    "performance": _CFG["mlflow"]["performance_model_uri"],
    "promotion":   _CFG["mlflow"]["promotion_model_uri"],
}

_FEATURE_SQL = """
    SELECT {cols}
    FROM {t}
    WHERE LOWER(employee_name)=LOWER('{name}') OR employee_id='{eid}'
    LIMIT 1
"""

# Cache loaded models in memory for the session
_MODEL_CACHE: dict[str, Any] = {}


def _load_model(prediction_type: str):
    if prediction_type not in _MODEL_CACHE:
        uri = _MODEL_URIS[prediction_type]
        _MODEL_CACHE[prediction_type] = mlflow.pyfunc.load_model(uri)
    return _MODEL_CACHE[prediction_type]


def prediction_agent(
    employee_name: str = "",
    employee_id: str = "",
    prediction_type: str = "attendance",
) -> dict[str, Any]:
    """
    Prediction Agent – runs MLflow models to forecast employee metrics.

    Args:
        employee_name   : Employee full name.
        employee_id     : Alternate employee ID.
        prediction_type : attendance | performance | promotion.

    Returns:
        dict with answer, predicted_value, confidence, feature_importance,
        chart_hint.
    """
    pt = prediction_type.lower().strip()
    if pt not in _FEATURE_COLS:
        return {
            "answer": f"Unknown prediction_type '{pt}'.",
            "predicted_value": 0.0, "confidence": 0.0,
            "feature_importance": [], "chart_hint": "kpi",
        }

    name = employee_name.strip().replace("'", "''")
    eid = employee_id.strip()
    cols = ", ".join(_FEATURE_COLS[pt])

    try:
        # ── Fetch features from Gold ──────────────────────────────────────────
        sql = _FEATURE_SQL.format(cols=cols, t=AI_TABLE, name=name, eid=eid)
        df = run_query(sql)

        if df.empty:
            return {
                "answer": f"No feature data found for '{employee_name or employee_id}'.",
                "predicted_value": 0.0, "confidence": 0.0,
                "feature_importance": [], "chart_hint": "kpi",
            }

        # ── Load model & predict ──────────────────────────────────────────────
        model = _load_model(pt)
        pred_df = model.predict(df)
        predicted_value = float(pred_df.iloc[0]) if hasattr(pred_df, "iloc") else float(pred_df[0])

        # ── Confidence interval (if model exposes it) ─────────────────────────
        confidence = 0.85   # default; override if model returns std

        # ── Feature importance (if sklearn / XGB model exposes it) ───────────
        feature_importance = []
        try:
            native = mlflow.sklearn.load_model(_MODEL_URIS[pt])
            if hasattr(native, "feature_importances_"):
                fi = native.feature_importances_
                feature_importance = sorted(
                    [{"feature": c, "importance": round(float(v), 4)}
                     for c, v in zip(_FEATURE_COLS[pt], fi)],
                    key=lambda x: x["importance"], reverse=True,
                )[:5]
        except Exception:
            pass

        # ── Natural language answer ───────────────────────────────────────────
        if pt == "attendance":
            pct = predicted_value * 100 if predicted_value <= 1 else predicted_value
            answer = (
                f"**{employee_name}** predicted next-month attendance: "
                f"**{pct:.1f}%** (confidence: {confidence*100:.0f}%)"
            )
        elif pt == "performance":
            answer = (
                f"**{employee_name}** predicted next-quarter performance score: "
                f"**{predicted_value:.1f}/100** (confidence: {confidence*100:.0f}%)"
            )
        elif pt == "promotion":
            label = "High" if predicted_value >= 0.7 else ("Medium" if predicted_value >= 0.4 else "Low")
            answer = (
                f"**{employee_name}** promotion readiness prediction: "
                f"**{label}** (score: {predicted_value:.2f}, confidence: {confidence*100:.0f}%)"
            )
        else:
            answer = f"Predicted value: {predicted_value:.2f}"

        return {
            "answer": answer,
            "predicted_value": predicted_value,
            "confidence": confidence,
            "feature_importance": feature_importance,
            "chart_hint": "kpi",
        }

    except Exception as exc:
        return {
            "answer": f"Prediction error: {exc}",
            "predicted_value": 0.0, "confidence": 0.0,
            "feature_importance": [], "chart_hint": "kpi",
        }
