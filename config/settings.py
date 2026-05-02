"""
Central configuration for Boston Parking RAG pipeline.
All tunable parameters live here — change once, applies everywhere.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent.parent
DATA_RAW        = BASE_DIR / "data" / "raw"
DATA_PROCESSED  = BASE_DIR / "data" / "processed"
DATA_CHUNKS     = BASE_DIR / "data" / "chunks"
CHROMA_DIR      = BASE_DIR / "data" / "chroma_db"
BM25_INDEX_PATH = BASE_DIR / "data" / "bm25_index.pkl"

# ── API Keys ───────────────────────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# ── Models ─────────────────────────────────────────────────────────────────
# Nano  → query decomposition, simple lookups (fast + cheap)
# Mini  → regulatory synthesis, multi-rule queries (precision)
MODEL_NANO          = "gpt-5.4-nano-2026-03-17"
MODEL_MINI          = "gpt-5.4-mini-2026-03-17"
EMBEDDING_MODEL     = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

# ── Retrieval ──────────────────────────────────────────────────────────────
TOP_K_BM25      = 10    # candidates from BM25 before RRF merge
TOP_K_DENSE     = 10    # candidates from ChromaDB before RRF merge
TOP_K_FINAL     = 5     # chunks passed to generation after RRF
RRF_K           = 60    # RRF constant (standard default)

# ── Chunking ───────────────────────────────────────────────────────────────
CHUNK_OVERLAP   = 50    # token overlap between adjacent chunks (PDF only)

# ── Generation ─────────────────────────────────────────────────────────────
MAX_TOKENS_NANO = 512
MAX_TOKENS_MINI = 1024
TEMPERATURE     = 0.0   # deterministic — regulatory answers must be consistent

# ── ChromaDB ───────────────────────────────────────────────────────────────
CHROMA_COLLECTION = "boston_parking"

# ── Sources ────────────────────────────────────────────────────────────────
SOURCES = {
    "violation_fines": {
        "url": "https://www.boston.gov/departments/parking-clerk/parking-ticket-fines-and-codes",
        "raw_file": "violation_fines.html",
        "processed_file": "violation_fines.json",
        "chunks_file": "violation_fines_chunks.json",
        "domain": "violations",
        "refresh_days": 90,
    },
    "permit_eligibility": {
        "url": "https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit",
        "raw_file": "permit_eligibility.html",
        "processed_file": "permit_eligibility.json",
        "chunks_file": "permit_eligibility_chunks.json",
        "domain": "permits",
        "refresh_days": 90,
    },
    "street_cleaning": {
        "url": "https://data.boston.gov/dataset/00c015a1-2b62-4072-a71e-79b292ce9670/resource/9fdbdcad-67c8-4b23-b6ec-861e77d56227/download/tmp_iit9wye.csv",
        "raw_file": "street_cleaning.csv",
        "processed_file": "street_cleaning.json",
        "chunks_file": "street_cleaning_chunks.json",
        "domain": "street_cleaning",
        "refresh_days": 30,
    },
    "traffic_rules": {
        "url": "https://www.boston.gov/sites/default/files/file/2025/03/City%20of%20Boston%20Traffic%20Rules%20and%20Regulations_03.01.2025.pdf",
        "raw_file": "traffic_rules.pdf",
        "processed_file": "traffic_rules.json",
        "chunks_file": "traffic_rules_chunks.json",
        "domain": "regulations",
        "refresh_days": 365,
    },
}