# Databricks Notebook — RAG Document Ingestion + Vector Index Setup
# ─────────────────────────────────────────────────────────────────────────────
# CELL 1: Install
# %pip install databricks-vectorsearch pypdf langchain
# dbutils.library.restartPython()

# ─────────────────────────────────────────────────────────────────────────────
# CELL 2: Define document sources and chunking
# ─────────────────────────────────────────────────────────────────────────────
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, LongType, StringType
import hashlib

CATALOG = "gold"
SCHEMA  = "talentpulse"

# Document source configs
DOCUMENT_SOURCES = [
    {
        "name": "hr_policy_documents",
        "volume_path": f"/Volumes/{CATALOG}/{SCHEMA}/hr_docs/policies/",
        "category": "hr_policy",
    },
    {
        "name": "career_path_documents",
        "volume_path": f"/Volumes/{CATALOG}/{SCHEMA}/hr_docs/career_paths/",
        "category": "career_path",
    },
    {
        "name": "skill_framework_documents",
        "volume_path": f"/Volumes/{CATALOG}/{SCHEMA}/hr_docs/skill_frameworks/",
        "category": "skill_framework",
    },
    {
        "name": "training_catalog_documents",
        "volume_path": f"/Volumes/{CATALOG}/{SCHEMA}/hr_docs/training_catalog/",
        "category": "training_catalog",
    },
]

CHUNK_SIZE    = 512
CHUNK_OVERLAP = 64

# ─────────────────────────────────────────────────────────────────────────────
# CELL 3: PDF → chunks ingestion function
# ─────────────────────────────────────────────────────────────────────────────
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pypdf, os

splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
)

def pdf_to_chunks(path: str, category: str) -> list[dict]:
    """Extract text from a PDF and split into overlapping chunks."""
    chunks = []
    with open(path, "rb") as f:
        reader = pypdf.PdfReader(f)
        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            if not text.strip():
                continue
            parts = splitter.split_text(text)
            for i, chunk in enumerate(parts):
                chunk_id = int(hashlib.md5(
                    f"{path}{page_num}{i}".encode()
                ).hexdigest(), 16) % (2**31)
                chunks.append({
                    "id":              chunk_id,
                    "chunk_text":      chunk,
                    "source_document": os.path.basename(path),
                    "title":           os.path.basename(path).replace(".pdf",""),
                    "page_number":     page_num,
                    "category":        category,
                })
    return chunks

# ─────────────────────────────────────────────────────────────────────────────
# CELL 4: Ingest all documents into Delta tables
# ─────────────────────────────────────────────────────────────────────────────
schema = StructType([
    StructField("id",              LongType(),   False),
    StructField("chunk_text",      StringType(), True),
    StructField("source_document", StringType(), True),
    StructField("title",           StringType(), True),
    StructField("page_number",     LongType(),   True),
    StructField("category",        StringType(), True),
])

for source in DOCUMENT_SOURCES:
    all_chunks = []
    vol_path = source["volume_path"]

    # Walk the volume directory
    try:
        files = dbutils.fs.ls(vol_path)
        for file_info in files:
            if file_info.name.endswith(".pdf"):
                local_path = file_info.path.replace("dbfs:", "/dbfs")
                chunks = pdf_to_chunks(local_path, source["category"])
                all_chunks.extend(chunks)
                print(f"  ✓ {file_info.name} → {len(chunks)} chunks")
    except Exception as e:
        print(f"  ⚠ Could not read {vol_path}: {e}")
        continue

    if not all_chunks:
        print(f"  ⚠ No chunks found for {source['name']}")
        continue

    df = spark.createDataFrame(all_chunks, schema=schema)
    table_name = f"{CATALOG}.{SCHEMA}.{source['name']}"
    (
        df.write
          .format("delta")
          .mode("overwrite")
          .option("mergeSchema", "true")
          .saveAsTable(table_name)
    )

    # Enable Change Data Feed for Vector Search sync
    spark.sql(f"ALTER TABLE {table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")
    print(f"✓ {table_name}: {len(all_chunks)} chunks saved")

# ─────────────────────────────────────────────────────────────────────────────
# CELL 5: Create Vector Search endpoint + indexes
# ─────────────────────────────────────────────────────────────────────────────
from databricks.vector_search.client import VectorSearchClient

VS_ENDPOINT  = "talentpulse-vs-endpoint"
EMBED_MODEL  = "databricks-bge-large-en"

vsc = VectorSearchClient()

# Create endpoint (idempotent)
try:
    vsc.create_endpoint(name=VS_ENDPOINT, endpoint_type="STANDARD")
    print(f"✓ Vector Search endpoint '{VS_ENDPOINT}' created")
except Exception as e:
    if "already exists" in str(e).lower():
        print(f"  Endpoint '{VS_ENDPOINT}' already exists")
    else:
        raise

# Create delta-sync index for each document table
for source in DOCUMENT_SOURCES:
    table_name = f"{CATALOG}.{SCHEMA}.{source['name']}"
    index_name = f"{CATALOG}.{SCHEMA}.{source['name'].replace('_documents','_index')}"

    try:
        vsc.create_delta_sync_index(
            endpoint_name=VS_ENDPOINT,
            source_table_name=table_name,
            index_name=index_name,
            pipeline_type="TRIGGERED",
            primary_key="id",
            embedding_source_column="chunk_text",
            embedding_model_endpoint_name=EMBED_MODEL,
        )
        print(f"✓ Index created: {index_name}")
    except Exception as e:
        if "already exists" in str(e).lower():
            print(f"  Index already exists: {index_name} — syncing...")
            vsc.get_index(
                endpoint_name=VS_ENDPOINT, index_name=index_name
            ).sync()
        else:
            print(f"  ⚠ Error creating {index_name}: {e}")

print("\n✅ All RAG indexes set up!")

# ─────────────────────────────────────────────────────────────────────────────
# CELL 6: Test similarity search
# ─────────────────────────────────────────────────────────────────────────────
idx = vsc.get_index(
    endpoint_name=VS_ENDPOINT,
    index_name=f"{CATALOG}.{SCHEMA}.hr_policy_index",
)
results = idx.similarity_search(
    query_text="How many casual leaves can an employee take?",
    columns=["chunk_text", "source_document"],
    num_results=3,
)
print("Sample RAG results:")
for row in results.get("result", {}).get("data_array", []):
    print(f"  [{row[-1]:.3f}] {str(row[0])[:150]}...")
