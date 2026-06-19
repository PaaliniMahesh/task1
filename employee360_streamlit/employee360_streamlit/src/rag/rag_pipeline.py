"""
src/rag/rag_pipeline.py
─────────────────────────────────────────────────────────────────────────────
RAG pipeline — HR knowledge base for Employee360 AI.
Stores HR policies, career paths, promotion criteria, training catalog.
Backends: ChromaDB (local/dev) or Databricks Vector Search (production).
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import logging

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore

import config as cfg

logger = logging.getLogger(__name__)


KNOWLEDGE_BASE = [
    {
        "id": "promo_policy_1",
        "category": "Promotion Policy",
        "content": """
Promotion Eligibility Criteria at Bilvantis:
1. Tenure: Minimum 2 years in current role for ICs, 3 years for leads/architects.
2. Performance: Weighted KRA score of 3.5+ in last two consecutive cycles.
3. Attendance: Minimum 85% attendance in the past 12 months.
4. Training: Completion of all mandatory role-specific trainings (min 70% completion).
5. Manager Recommendation: Direct manager must nominate with justification.
6. Promotion Committee Review: Final approval held quarterly.
Promotion bands: Junior → Mid → Senior → Lead → Architect/Manager.
        """,
    },
    {
        "id": "promo_scoring",
        "category": "Promotion Policy",
        "content": """
Promotion Readiness Scoring (TalentPulse):
- Composite Talent Score (0–100): Attendance 25% + Training 25% + Performance 50%.
- Promotion Readiness Score (0–100):
    Not Ready: 0–40 | Development Needed: 40–60 | Nearly Ready: 60–80 | Promotion Ready: 80–100
- Employees scoring 80+ are presented to the Promotion Committee.
- Estimated months to promotion calculated from current gap closure rates.
        """,
    },
    {
        "id": "career_path_aiml",
        "category": "Career Path",
        "content": """
AI/ML Career Path:
Junior ML Engineer → ML Engineer → Senior ML Engineer → Lead ML Engineer → AI Architect → Senior AI Architect

Skills by level:
- Junior: Python, Scikit-learn, basic statistics, SQL
- Mid: PyTorch/TensorFlow, MLflow, feature engineering, cloud
- Senior: LLMs, MLOps, distributed training, system design
- Lead/Architect: GenAI, LangChain, Databricks, team leadership
        """,
    },
    {
        "id": "career_path_de",
        "category": "Career Path",
        "content": """
Data Engineering (DE) Career Path:
Junior Data Engineer → Data Engineer → Senior Data Engineer → DE Lead → Data Architect → Senior Data Architect

Skills by level:
- Junior: SQL, Python, basic ETL, Git
- Mid: PySpark, Apache Spark, Airflow, dbt, Delta Lake
- Senior: Databricks, Unity Catalog, Kafka, cloud platforms
- Lead/Architect: Medallion Architecture, DataOps, team mentoring

CDE Path: Junior CDE → CDE → Senior CDE → CDE Lead → Cloud Architect
Required: BigQuery, Snowflake, AWS Glue, Azure Data Factory, Terraform
        """,
    },
    {
        "id": "career_path_devops",
        "category": "Career Path",
        "content": """
DevOps Career Path:
Junior DevOps → DevOps Engineer → Senior DevOps → Platform Engineer → DevOps Lead → Infrastructure Architect
SRE Track: SRE Engineer → Senior SRE → SRE Lead

Skills:
- Junior: CI/CD (Jenkins, GitLab CI), Docker, Kubernetes basics, shell
- Mid: Kubernetes, Helm, Terraform, Prometheus, Grafana
- Senior: ArgoCD, multi-cloud, platform engineering, observability
        """,
    },
    {
        "id": "training_catalog",
        "category": "Training Catalog",
        "content": """
Bilvantis Approved Courses:
Foundation: Python Basics (8h), SQL Advanced (10h), Data Engineering Basics (12h), GenAI Essentials (6h)
Technical: Machine Learning Basics (10h), Spark Programming (8h), Databricks Fundamentals (14h),
           MLOps Fundamentals (10h), Azure Data Factory (12h), Power BI Fundamentals (8h)
Advanced: Databricks Data Engineer Professional (40h), Databricks ML Professional (40h),
          AWS Solutions Architect (20h), Azure Data Engineer (20h)
Completion of mandatory courses required for promotion eligibility.
        """,
    },
    {
        "id": "attendance_policy",
        "category": "HR Policy",
        "content": """
Attendance Policy:
- Minimum expected: 85% per month
- WFH allowance: Up to 3 days/week for eligible roles
- Leave: Casual (12/yr), Sick (12/yr), Earned (15/yr)
- Attendance risk flag: attendance < 80%
- Chronic absenteeism (<70% for 2 consecutive months) triggers formal HR review
- Effective hours target: 8 hrs/day; below 6 hrs flags productivity review
        """,
    },
    {
        "id": "kra_framework",
        "category": "Performance Framework",
        "content": """
KRA Framework — 6 KRAs per quarter:
1. Delivery Excellence — on-time quality delivery
2. Process Excellence — adherence to processes, documentation
3. AI Adoption — use of AI tools and GenAI
4. CSAT — client satisfaction, appreciation/escalation management
5. Learning & Development — training completion, certifications
6. Team Collaboration — cross-team contributions, mentoring

Rating: 1=Below Average | 2=Average | 3=Good | 4=Excellent | 5=Outstanding
Bands: 4.5-5.0 Exceptional | 3.5-4.4 Exceeds | 2.5-3.4 Meets | 1.5-2.4 Below | <1.5 Needs Improvement
Manager rating: 60% weight | Self-rating: 40% weight
        """,
    },
    {
        "id": "databricks_transition",
        "category": "Role Transition",
        "content": """
Transitioning to Databricks Data Engineer:
Required: PySpark (proficient), Delta Lake, Unity Catalog, Medallion Architecture,
          dbt, Airflow/Databricks Workflows, SQL (Advanced), Python
Certifications: Databricks Certified Data Engineer Associate (prerequisite),
                Databricks Certified Data Engineer Professional (preferred)
Timeline: From Data Engineer: 6-12 months | From CDE: 3-6 months | From ETL: 9-12 months
Training needed: Databricks Fundamentals, Spark Programming, Azure Data Factory
        """,
    },
]


class RAGPipeline:
    """HR Knowledge Base RAG pipeline."""

    def __init__(self):
        self._vectorstore: VectorStore | None = None
        self._retriever = None

    def build(self, documents: list[dict] | None = None) -> "RAGPipeline":
        docs = documents or KNOWLEDGE_BASE
        langchain_docs = [
            Document(
                page_content=d["content"].strip(),
                metadata={"id": d["id"], "category": d["category"]},
            )
            for d in docs
        ]
        if cfg.rag.use_databricks_vs:
            self._vectorstore = self._build_databricks_vs(langchain_docs)
        else:
            self._vectorstore = self._build_chroma(langchain_docs)

        self._retriever = self._vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": cfg.rag.top_k},
        )
        logger.info("RAG pipeline built with %d documents.", len(langchain_docs))
        return self

    def _build_chroma(self, docs: list[Document]) -> VectorStore:
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import HuggingFaceEmbeddings
        embeddings = HuggingFaceEmbeddings(model_name=cfg.rag.embedding_model)
        return Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            collection_name=cfg.rag.collection_name,
            persist_directory=cfg.rag.chroma_persist_dir,
        )

    def _build_databricks_vs(self, docs: list[Document]) -> VectorStore:
        try:
            from langchain_community.vectorstores import DatabricksVectorSearch
            from langchain_community.embeddings import HuggingFaceEmbeddings
            from databricks.vector_search.client import VectorSearchClient
            embeddings = HuggingFaceEmbeddings(model_name=cfg.rag.embedding_model)
            vs_client  = VectorSearchClient(
                workspace_url=cfg.databricks.host,
                personal_access_token=cfg.databricks.token,
            )
            return DatabricksVectorSearch(
                vs_client,
                endpoint=cfg.rag.vs_endpoint,
                index_name=f"gold.talentpulse.{cfg.rag.vs_index_name}",
                embedding=embeddings,
            )
        except Exception as e:
            logger.warning("Databricks VS failed (%s), falling back to ChromaDB.", e)
            return self._build_chroma(docs)

    def retrieve(self, query: str) -> str:
        if self._retriever is None:
            return ""
        try:
            docs: list[Document] = self._retriever.invoke(query)
            if not docs:
                return ""
            parts = ["[HR KNOWLEDGE BASE]"]
            for doc in docs:
                cat = doc.metadata.get("category", "General")
                parts.append(f"\n--- {cat} ---\n{doc.page_content.strip()}")
            return "\n".join(parts)
        except Exception as e:
            logger.warning("RAG retrieval failed: %s", e)
            return ""

    def add_documents(self, new_docs: list[dict]) -> None:
        if self._vectorstore is None:
            return
        langchain_docs = [
            Document(page_content=d["content"].strip(),
                     metadata={"id": d["id"], "category": d["category"]})
            for d in new_docs
        ]
        self._vectorstore.add_documents(langchain_docs)
