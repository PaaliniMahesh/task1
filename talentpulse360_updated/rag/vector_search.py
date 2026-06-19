"""
RAG – Databricks Vector Search helper
─────────────────────────────────────────────────────────────────────────────
Wraps the databricks-vectorsearch SDK for similarity search against
Delta-Sync or Direct-Access indexes.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import yaml, os
from pathlib import Path
from databricks.vector_search.client import VectorSearchClient

_CFG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"
with open(_CFG_PATH) as f:
    _CFG = yaml.safe_load(f)

_VS_ENDPOINT = _CFG["rag"]["vector_search_endpoint"]
_EMBED_MODEL  = _CFG["rag"]["embedding_model"]
_TOP_K        = _CFG["rag"]["top_k"]

# Singleton client
_CLIENT: VectorSearchClient | None = None


def _client() -> VectorSearchClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = VectorSearchClient(
            workspace_url=os.environ.get(
                "DATABRICKS_HOST", _CFG["databricks"]["workspace_url"]
            ),
            personal_access_token=os.environ.get("DATABRICKS_TOKEN", ""),
        )
    return _CLIENT


def query_index(
    index_name: str,
    query: str,
    top_k: int = _TOP_K,
    filters: dict | None = None,
) -> list[dict]:
    """
    Run a similarity search against a Databricks Vector Search index.

    Args:
        index_name : Fully qualified UC index name
                     (e.g. 'gold.talentpulse.hr_policy_index').
        query      : Natural-language query string.
        top_k      : Number of results to return.
        filters    : Optional metadata filter dict.

    Returns:
        List of result dicts with keys: chunk_text, source_document, score.
    """
    idx = _client().get_index(
        endpoint_name=_VS_ENDPOINT,
        index_name=index_name,
    )

    kwargs: dict = {
        "query_text": query,
        "columns": ["chunk_text", "source_document", "title", "page_number"],
        "num_results": top_k,
    }
    if filters:
        kwargs["filters"] = filters

    resp = idx.similarity_search(**kwargs)
    results = resp.get("result", {}).get("data_array", [])
    col_names = [c["name"] for c in resp.get("manifest", {}).get("columns", [])]

    formatted = []
    for row in results:
        d = dict(zip(col_names, row))
        formatted.append({
            "chunk_text":       d.get("chunk_text", ""),
            "source_document":  d.get("source_document", d.get("title", "")),
            "score":            d.get("score", 0.0),
        })
    return formatted


# ─────────────────────────────────────────────────────────────────────────────
# Index creation helper  (run once from a Databricks notebook)
# ─────────────────────────────────────────────────────────────────────────────

def create_rag_indexes_notebook_code() -> str:
    """
    Returns Python code to copy-paste into a Databricks notebook to set up
    all four Vector Search indexes.
    """
    return '''
# ── Run this in a Databricks notebook (once) ────────────────────────────────
from databricks.vector_search.client import VectorSearchClient

VS_ENDPOINT = "talentpulse-vs-endpoint"
EMBED_MODEL  = "databricks-bge-large-en"

vsc = VectorSearchClient()

# 1. Create endpoint (if it doesn't exist)
try:
    vsc.create_endpoint(name=VS_ENDPOINT, endpoint_type="STANDARD")
except Exception:
    pass  # Already exists

# ── Documents table schema ───────────────────────────────────────────────────
# Each source table must have columns:
#   id (BIGINT), chunk_text (STRING), source_document (STRING),
#   title (STRING), page_number (INT), category (STRING)

INDEX_CONFIGS = [
    {
        "source_table": "gold.talentpulse.hr_policy_documents",
        "index_name":   "gold.talentpulse.hr_policy_index",
    },
    {
        "source_table": "gold.talentpulse.career_path_documents",
        "index_name":   "gold.talentpulse.career_path_index",
    },
    {
        "source_table": "gold.talentpulse.skill_framework_documents",
        "index_name":   "gold.talentpulse.skill_framework_index",
    },
    {
        "source_table": "gold.talentpulse.training_catalog_documents",
        "index_name":   "gold.talentpulse.training_catalog_index",
    },
]

for cfg in INDEX_CONFIGS:
    print(f"Creating index: {cfg['index_name']} ...")
    vsc.create_delta_sync_index(
        endpoint_name   = VS_ENDPOINT,
        source_table_name = cfg["source_table"],
        index_name      = cfg["index_name"],
        pipeline_type   = "TRIGGERED",
        primary_key     = "id",
        embedding_source_column = "chunk_text",
        embedding_model_endpoint_name = EMBED_MODEL,
    )
    print(f"  ✓ {cfg['index_name']}")

print("All indexes created!")
'''
