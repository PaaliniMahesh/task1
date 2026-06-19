"""
Agent 8 – RAG Knowledge Agent
─────────────────────────────────────────────────────────────────────────────
Purpose  : Answer policy / knowledge questions by searching vector indexes
           created from HR documents.

Vector Indexes (created in Databricks Vector Search):
  1. hr_policy_index         ← HR Policies, Leave Policies
  2. career_path_index       ← Career Ladders, Promotion Criteria
  3. skill_framework_index   ← Skill Definitions, Competency Frameworks
  4. training_catalog_index  ← Course Catalog, Certification Guides

Input schema:
  {
    "query"      : str,                # free-text question
    "index_type" : "hr_policy"
                   | "career_path"
                   | "skill_framework"
                   | "training_catalog"
                   | "auto",          # auto-selects the best index
    "top_k"      : int | None
  }

Output schema:
  { "answer": str, "sources": list[dict], "chart_hint": "table" }
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
from typing import Any
import yaml
from pathlib import Path
from rag.vector_search import query_index

_CFG_PATH = Path(__file__).parent.parent / "config" / "config.yaml"
with open(_CFG_PATH) as f:
    _CFG = yaml.safe_load(f)

_INDEX_MAP = {
    "hr_policy":       _CFG["rag"]["hr_policy_index"],
    "career_path":     _CFG["rag"]["career_path_index"],
    "skill_framework": _CFG["rag"]["skill_framework_index"],
    "training_catalog":_CFG["rag"]["training_catalog_index"],
}

# Keywords that hint which index to use for "auto" routing
_INDEX_HINTS = {
    "hr_policy":        ["leave", "policy", "wfh", "work from home", "rule",
                         "benefit", "holiday", "regulation", "code of conduct"],
    "career_path":      ["career", "promotion", "ladder", "growth", "next role",
                         "level", "path", "criteria", "eligibility"],
    "skill_framework":  ["skill", "competency", "framework", "proficiency",
                         "required skill", "skill level", "certification requirement"],
    "training_catalog": ["course", "training", "learn", "certification", "workshop",
                         "program", "udemy", "coursera", "catalog"],
}


def _auto_select_index(query: str) -> str:
    q_lower = query.lower()
    scores = {idx: sum(1 for kw in kws if kw in q_lower)
              for idx, kws in _INDEX_HINTS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "hr_policy"


def rag_knowledge_agent(
    query: str = "",
    index_type: str = "auto",
    top_k: int = 5,
) -> dict[str, Any]:
    """
    RAG Knowledge Agent – semantic search over HR knowledge documents.

    Args:
        query      : Natural language question.
        index_type : hr_policy | career_path | skill_framework |
                     training_catalog | auto.
        top_k      : Number of document chunks to retrieve.

    Returns:
        dict with answer (str), sources (list[dict]), chart_hint (str).
    """
    if not query.strip():
        return {"answer": "Please provide a query.", "sources": [], "chart_hint": "table"}

    selected = _auto_select_index(query) if index_type == "auto" else index_type
    index_name = _INDEX_MAP.get(selected, _INDEX_MAP["hr_policy"])

    try:
        results = query_index(index_name=index_name, query=query, top_k=top_k)

        if not results:
            return {
                "answer": (
                    f"No relevant documents found in the {selected.replace('_',' ')} "
                    f"knowledge base for: '{query}'"
                ),
                "sources": [],
                "chart_hint": "table",
            }

        # ── Build answer from retrieved chunks ────────────────────────────────
        answer_parts = [
            f"📚 Based on **{selected.replace('_', ' ').title()}** documents:\n"
        ]
        sources = []
        for i, doc in enumerate(results[:top_k], 1):
            chunk = doc.get("chunk_text", doc.get("text", ""))
            source = doc.get("source_document", doc.get("title", f"Document {i}"))
            score = doc.get("score", 0.0)
            answer_parts.append(f"**{i}. {source}** (relevance: {score:.2f})\n{chunk[:300]}...\n")
            sources.append({"rank": i, "source": source, "score": score, "snippet": chunk[:200]})

        return {
            "answer": "\n".join(answer_parts),
            "sources": sources,
            "chart_hint": "table",
        }

    except Exception as exc:
        return {
            "answer": f"RAG search error: {exc}",
            "sources": [],
            "chart_hint": "table",
        }
