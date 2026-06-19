"""
Shared Databricks SQL execution utility.
All agents and pages import from here.
"""

from __future__ import annotations
import yaml, os, functools
from pathlib import Path
import pandas as pd

# Use databricks-sql-connector which works in both notebook and app environments
try:
    from databricks.sql import connect as sql_connect
except ImportError:
    # Fallback for older environments
    from databricks import sql
    sql_connect = sql.connect

_CFG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"

@functools.lru_cache(maxsize=1)
def _cfg() -> dict:
    with open(_CFG_PATH) as f:
        return yaml.safe_load(f)


def run_query(query: str, params: dict | None = None) -> pd.DataFrame:
    """
    Execute SQL against the Databricks SQL Warehouse and return a DataFrame.
    Uses environment variables for credentials (injected by Databricks Apps).
    """
    cfg = _cfg()
    
    # Get connection parameters
    host = os.environ.get("DATABRICKS_HOST") or cfg["databricks"]["workspace_url"]
    token = os.environ.get("DATABRICKS_TOKEN") or os.environ.get("DATABRICKS_ACCESS_TOKEN", "")
    warehouse_id = cfg["databricks"]["warehouse_id"]
    
    # Remove https:// prefix if present
    if host.startswith("https://"):
        host = host.replace("https://", "")
    if host.startswith("http://"):
        host = host.replace("http://", "")

    with sql_connect(
        server_hostname=host,
        http_path=f"/sql/1.0/warehouses/{warehouse_id}",
        access_token=token,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or {})
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
    
    return pd.DataFrame(rows, columns=cols)


def table(name: str) -> str:
    """Return the fully qualified table name from config alias."""
    cfg = _cfg()
    return cfg["tables"].get(name, name)
