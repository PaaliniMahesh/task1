"""
src/db_connector.py
─────────────────────────────────────────────────────────────────────────────
Databricks SQL connector that queries the 7 Gold tables in
gold.talentpulse.* using Databricks Connect (SparkSession) when running
inside Databricks, or the SQL Connector for external / local use.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pandas as pd

import config as cfg

logger = logging.getLogger(__name__)


class DatabaseConnector:
    """
    Thin wrapper around Databricks SQL.

    Parameters
    ----------
    use_spark : bool
        True  → SparkSession (running inside a Databricks cluster)
        False → databricks-sql-connector (external / local dev)
    """

    def __init__(self, use_spark: bool = True):
        self.use_spark = use_spark
        self._spark    = None
        self._sql_conn = None
        if use_spark:
            self._init_spark()
        else:
            self._init_sql_connector()

    def _init_spark(self):
        from pyspark.sql import SparkSession
        self._spark = SparkSession.getActiveSession() or SparkSession.builder.getOrCreate()
        logger.info("SparkSession initialised (Databricks Runtime).")

    def _init_sql_connector(self):
        from databricks import sql as dbsql
        self._sql_conn = dbsql.connect(
            server_hostname=cfg.databricks.host,
            http_path=cfg.databricks.http_path,
            access_token=cfg.databricks.token,
        )
        logger.info("Databricks SQL Connector initialised (external mode).")

    def query(self, sql: str) -> list[dict]:
        try:
            if self.use_spark:
                df = self._spark.sql(sql).toPandas()
            else:
                with self._sql_conn.cursor() as cursor:
                    cursor.execute(sql)
                    rows = cursor.fetchall()
                    cols = [d[0] for d in cursor.description]
                    df   = pd.DataFrame(rows, columns=cols)
            df = df.where(pd.notnull(df), None)
            return df.to_dict(orient="records")
        except Exception as e:
            logger.error("Query failed: %s\nSQL: %s", e, sql)
            raise

    def _t(self, table_attr: str) -> str:
        return cfg.databricks.fqn(getattr(cfg.databricks, table_attr))

    # ── employee_360 ─────────────────────────────────────────────────────────

    def get_employee_360(self, name_or_id: str) -> list[dict]:
        predicate = (
            f"UPPER(employee_id) = UPPER('{name_or_id}')"
            if name_or_id.upper().startswith("EMP")
            else f"LOWER(employee_name) LIKE LOWER('%{name_or_id}%')"
        )
        return self.query(f"SELECT * FROM {self._t('table_employee_360')} WHERE {predicate} LIMIT 5")

    def search_employees(self, partial_name: str) -> list[dict]:
        return self.query(f"""
            SELECT employee_id, employee_name, department, designation,
                   location, manager_name, employee_health_status
            FROM {self._t('table_employee_360')}
            WHERE LOWER(employee_name) LIKE LOWER('%{partial_name}%')
            LIMIT 10
        """)

    # ── attendance ───────────────────────────────────────────────────────────

    def get_attendance(self, employee_id: str) -> list[dict]:
        return self.query(f"""
            SELECT * FROM {self._t('table_attendance_summary')}
            WHERE employee_id = '{employee_id}'
            ORDER BY current_month DESC LIMIT 3
        """)

    def get_attendance_at_risk(self, threshold: float = 80.0) -> list[dict]:
        return self.query(f"""
            SELECT a.employee_id, e.employee_name, e.department, e.designation,
                   a.attendance_percentage, a.present_days, a.absent_days,
                   a.leave_days, a.attendance_trend, a.last_attendance_date
            FROM {self._t('table_attendance_summary')} a
            JOIN {self._t('table_employee_360')} e ON a.employee_id = e.employee_id
            WHERE a.attendance_percentage < {threshold}
            ORDER BY a.attendance_percentage ASC LIMIT 20
        """)

    def get_wfh_analysis(self, department: str | None = None) -> list[dict]:
        dept_filter = f"AND e.department = '{department}'" if department else ""
        return self.query(f"""
            SELECT e.department, e.employee_name,
                   a.wfh_days, a.present_days,
                   ROUND(a.wfh_days * 100.0 / NULLIF(a.total_days_recorded, 0), 1) AS wfh_pct,
                   a.avg_effective_hours_per_day
            FROM {self._t('table_attendance_summary')} a
            JOIN {self._t('table_employee_360')} e ON a.employee_id = e.employee_id
            WHERE 1=1 {dept_filter}
            ORDER BY wfh_pct DESC LIMIT 20
        """)

    # ── training ─────────────────────────────────────────────────────────────

    def get_training(self, employee_id: str) -> list[dict]:
        return self.query(f"SELECT * FROM {self._t('table_training_summary')} WHERE employee_id = '{employee_id}'")

    def get_training_at_risk(self) -> list[dict]:
        return self.query(f"""
            SELECT t.employee_id, e.employee_name, e.department, e.designation,
                   t.total_trainings_assigned, t.trainings_completed,
                   t.training_completion_percentage, t.last_training_completed,
                   t.last_training_assigned_date
            FROM {self._t('table_training_summary')} t
            JOIN {self._t('table_employee_360')} e ON t.employee_id = e.employee_id
            WHERE t.training_completion_percentage = 0 AND t.total_trainings_assigned > 0
            ORDER BY t.last_training_assigned_date DESC LIMIT 25
        """)

    def get_pending_trainings(self) -> list[dict]:
        return self.query(f"""
            SELECT t.employee_id, e.employee_name, e.department,
                   t.trainings_pending, t.trainings_in_progress,
                   t.training_completion_percentage, t.last_training_completed
            FROM {self._t('table_training_summary')} t
            JOIN {self._t('table_employee_360')} e ON t.employee_id = e.employee_id
            WHERE t.trainings_pending > 0 OR t.trainings_in_progress > 0
            ORDER BY t.training_completion_percentage ASC LIMIT 25
        """)

    # ── performance ──────────────────────────────────────────────────────────

    def get_performance(self, employee_id: str) -> list[dict]:
        return self.query(f"SELECT * FROM {self._t('table_performance_summary')} WHERE employee_id = '{employee_id}'")

    def get_performance_by_band(self, band: str) -> list[dict]:
        return self.query(f"""
            SELECT p.employee_id, e.employee_name, e.department, e.designation,
                   p.performance_band, p.weighted_performance_score,
                   p.avg_manager_rating, p.avg_self_rating,
                   p.top_performing_areas, p.improvement_areas
            FROM {self._t('table_performance_summary')} p
            JOIN {self._t('table_employee_360')} e ON p.employee_id = e.employee_id
            WHERE LOWER(p.performance_band) LIKE LOWER('%{band}%')
            ORDER BY p.weighted_performance_score DESC LIMIT 20
        """)

    def get_performance_by_department(self, department: str) -> list[dict]:
        return self.query(f"""
            SELECT e.employee_name, e.designation,
                   p.weighted_performance_score, p.performance_band,
                   p.avg_manager_rating, p.avg_self_rating,
                   p.top_performing_areas, p.improvement_areas,
                   p.excellent_ratings_count, p.below_average_ratings_count
            FROM {self._t('table_performance_summary')} p
            JOIN {self._t('table_employee_360')} e ON p.employee_id = e.employee_id
            WHERE LOWER(e.department) = LOWER('{department}')
            ORDER BY p.weighted_performance_score DESC
        """)

    # ── ranking ──────────────────────────────────────────────────────────────

    def get_ranking(self, employee_id: str) -> list[dict]:
        return self.query(f"SELECT * FROM {self._t('table_ranking')} WHERE employee_id = '{employee_id}'")

    def get_top_performers(self, n: int = 10, department: str | None = None) -> list[dict]:
        dept_filter = f"AND LOWER(department) = LOWER('{department}')" if department else ""
        return self.query(f"""
            SELECT employee_id, employee_name, department, designation,
                   composite_talent_score, weighted_performance_score,
                   attendance_percentage, training_completion_percentage,
                   overall_rank, ranking_category, performance_tier
            FROM {self._t('table_ranking')}
            WHERE 1=1 {dept_filter}
            ORDER BY overall_rank ASC LIMIT {n}
        """)

    def get_department_rankings(self, department: str) -> list[dict]:
        return self.query(f"""
            SELECT r.employee_id, e.employee_name, e.designation,
                   r.department_rank, r.total_in_department,
                   r.composite_talent_score, r.performance_tier, r.ranking_category
            FROM {self._t('table_ranking')} r
            JOIN {self._t('table_employee_360')} e ON r.employee_id = e.employee_id
            WHERE LOWER(r.department) = LOWER('{department}')
            ORDER BY r.department_rank ASC
        """)

    # ── promotion ────────────────────────────────────────────────────────────

    def get_promotion(self, employee_id: str) -> list[dict]:
        return self.query(f"SELECT * FROM {self._t('table_promotion_readiness')} WHERE employee_id = '{employee_id}'")

    def get_promotion_ready_employees(self, status: str = "Nearly Ready", department: str | None = None) -> list[dict]:
        dept_filter = f"AND LOWER(p.department) = LOWER('{department}')" if department else ""
        return self.query(f"""
            SELECT p.employee_id, p.employee_name, p.department, p.designation,
                   p.promotion_readiness_score, p.promotion_readiness_status,
                   p.recommended_next_designation, p.estimated_months_to_promotion,
                   p.tenure_eligible, p.performance_eligible,
                   p.performance_gap, p.training_gap, p.attendance_gap
            FROM {self._t('table_promotion_readiness')} p
            WHERE LOWER(p.promotion_readiness_status) LIKE LOWER('%{status}%')
            {dept_filter}
            ORDER BY p.promotion_readiness_score DESC LIMIT 20
        """)

    def get_skill_gap_for_role(self, target_role: str) -> list[dict]:
        return self.query(f"""
            SELECT p.employee_id, p.employee_name, p.department, p.designation,
                   p.recommended_next_designation, p.promotion_readiness_score,
                   p.estimated_months_to_promotion,
                   p.performance_gap, p.training_gap, p.attendance_gap,
                   e.primary_skills
            FROM {self._t('table_promotion_readiness')} p
            JOIN {self._t('table_employee_360')} e ON p.employee_id = e.employee_id
            WHERE LOWER(p.recommended_next_designation) LIKE LOWER('%{target_role}%')
               OR LOWER(p.designation) LIKE LOWER('%{target_role}%')
            ORDER BY p.promotion_readiness_score DESC LIMIT 15
        """)

    # ── AI features ──────────────────────────────────────────────────────────

    def get_ai_predictions(self, employee_id: str) -> list[dict]:
        return self.query(f"""
            SELECT employee_id, employee_name, department, designation,
                   predicted_next_month_attendance,
                   predicted_next_quarter_performance,
                   prediction_confidence,
                   composite_talent_score,
                   attendance_risk, training_risk, performance_risk
            FROM {self._t('table_ai_features')}
            WHERE employee_id = '{employee_id}'
        """)

    def get_high_risk_predictions(self) -> list[dict]:
        return self.query(f"""
            SELECT a.employee_id, e.employee_name, e.department, e.designation,
                   a.predicted_next_month_attendance,
                   a.predicted_next_quarter_performance,
                   a.prediction_confidence,
                   a.attendance_risk, a.training_risk, a.performance_risk
            FROM {self._t('table_ai_features')} a
            JOIN {self._t('table_employee_360')} e ON a.employee_id = e.employee_id
            WHERE a.predicted_next_month_attendance < 70
               OR (a.attendance_risk = 1 AND a.training_risk = 1)
            ORDER BY a.predicted_next_month_attendance ASC LIMIT 20
        """)

    # ── Cross-table analytics ─────────────────────────────────────────────────

    def get_workforce_summary(self) -> dict:
        rows = self.query(f"""
            SELECT
                COUNT(*) AS total_employees,
                SUM(CASE WHEN employee_health_status = 'On Track' THEN 1 ELSE 0 END) AS on_track,
                SUM(CASE WHEN employee_health_status = 'At Risk'  THEN 1 ELSE 0 END) AS at_risk,
                SUM(CASE WHEN attendance_risk_flag  = true THEN 1 ELSE 0 END) AS attendance_risk,
                SUM(CASE WHEN training_risk_flag    = true THEN 1 ELSE 0 END) AS training_risk,
                SUM(CASE WHEN performance_risk_flag = true THEN 1 ELSE 0 END) AS performance_risk,
                ROUND(AVG(CAST(composite_talent_score         AS DOUBLE)), 2) AS avg_talent_score,
                ROUND(AVG(CAST(weighted_performance_score     AS DOUBLE)), 2) AS avg_performance_score,
                ROUND(AVG(CAST(attendance_percentage          AS DOUBLE)), 2) AS avg_attendance_pct,
                ROUND(AVG(CAST(training_completion_percentage AS DOUBLE)), 2) AS avg_training_pct
            FROM {self._t('table_employee_360')}
        """)
        return rows[0] if rows else {}

    def get_department_summary(self) -> list[dict]:
        return self.query(f"""
            SELECT
                department,
                COUNT(*) AS headcount,
                ROUND(AVG(CAST(composite_talent_score         AS DOUBLE)), 2) AS avg_talent_score,
                ROUND(AVG(CAST(attendance_percentage          AS DOUBLE)), 2) AS avg_attendance_pct,
                ROUND(AVG(CAST(training_completion_percentage AS DOUBLE)), 2) AS avg_training_pct,
                ROUND(AVG(CAST(weighted_performance_score     AS DOUBLE)), 2) AS avg_perf_score,
                SUM(CASE WHEN employee_health_status = 'At Risk'  THEN 1 ELSE 0 END) AS at_risk_count,
                SUM(CASE WHEN employee_health_status = 'On Track' THEN 1 ELSE 0 END) AS on_track_count
            FROM {self._t('table_employee_360')}
            GROUP BY department
            ORDER BY avg_talent_score DESC
        """)

    def get_full_employee_profile(self, employee_id: str) -> dict[str, Any]:
        return {
            "employee_360":   self.get_employee_360(employee_id),
            "attendance":     self.get_attendance(employee_id),
            "training":       self.get_training(employee_id),
            "performance":    self.get_performance(employee_id),
            "ranking":        self.get_ranking(employee_id),
            "promotion":      self.get_promotion(employee_id),
            "ai_predictions": self.get_ai_predictions(employee_id),
        }
