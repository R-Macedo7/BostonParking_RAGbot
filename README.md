# Boston Parking RAG

An AI-powered chatbot for Boston parking regulations using a hybrid BM25 + cosine similarity RAG pipeline with Reciprocal Rank Fusion (RRF) retrieval and GPT-5.4 generation.

---

## Overview

Boston Parking RAG answers natural language questions about Boston parking rules, fines, street cleaning schedules, and resident permit programs. It retrieves answers strictly from official City of Boston sources — no hallucination, no invented rules.

**Live demo:** Start the API (`python3 api/main.py`) and open `frontend/index.html` in a browser.

---

## Architecture

```
Query
  │
  ├─► Query classifier      — detects domain (violations/permits/street_cleaning/regulations)
  │                           and street name entities
  ├─► Query decomposer       — GPT-5.4 nano splits multi-part queries into sub-queries
  │
  ├─► BM25 sparse retrieval  ┐
  │                           ├─► RRF merge → Top-K chunks
  └─► ChromaDB dense retrieval┘  (Reciprocal Rank Fusion)
                │
         Complexity router
                │
         ┌──────┴──────┐
    GPT-5.4 nano    GPT-5.4 mini
    (simple lookups) (regulatory synthesis)
                │
             Answer + citations
```

### Model routing
| Task | Model | Reason |
|---|---|---|
| Query decomposition | `gpt-5.4-nano` | Lightweight routing task |
| Simple fact lookups | `gpt-5.4-nano` | Fast, cheap, sufficient |
| Multi-rule synthesis | `gpt-5.4-mini` | Precision matters |
| Embeddings | `text-embedding-3-small` | Cost-efficient, 1536-dim |

### Vector store
- **ChromaDB** with HNSW index (cosine similarity space)
- **rank-bm25** for sparse BM25 retrieval
- **RRF** (k=60) merges both ranked lists without score calibration

---

## Data Sources

| Source | Format | Domain | Refresh |
|---|---|---|---|
| [Boston Parking Ticket Fines and Codes](https://www.boston.gov/departments/parking-clerk/parking-ticket-fines-and-codes) | HTML table | violations | 90 days |
| [Resident Parking Permit Guide](https://www.boston.gov/departments/parking-clerk/how-get-resident-parking-permit) | HTML | permits | 90 days |
| [Street Sweeping Schedules](https://data.boston.gov/dataset/street-sweeping-schedules) | CSV (Analyze Boston) | street_cleaning | 30 days |
| [BTD Traffic Rules & Regulations](https://www.boston.gov/departments/transportation/city-boston-traffic-rules-and-regulations) | PDF (March 2025, 80 pages) | regulations | 365 days |

### Corpus stats
| Source | Chunks | Strategy |
|---|---|---|
| Violation fines | ~66 | 1 chunk per violation + summary + zone comparison + pedestrian zone |
| Permit eligibility | ~20 | 1 chunk per section + key fact chunks |
| Street cleaning | ~1,682 | 1 chunk per street + general rules + holidays + neighborhood seasons |
| Traffic rules | ~113 | Section-aware PDF splitting (Article/Section headers), min 150 chars |
| **Total** | **~1,881** | |

---

## Evaluation Results

All evaluations run against 74 ground-truth queries spanning violations, permits, street cleaning, regulations, edge cases, out-of-scope, and multi-part queries.

### Retrieval (eval_retrieval.py)
| Metric | Score |
|---|---|
| Recall@5 | **100%** (15/15 original queries) |
| MRR | **0.967** |

Retrieval improved significantly after enabling full hybrid search:

| Phase | Recall@5 | MRR |
|---|---|---|
| BM25 only (ChromaDB empty) | 87% | 0.722 |
| Hybrid BM25 + dense | 93% | 0.900 |
| Hybrid + metadata filter fixes | **100%** | **0.967** |

### Generation (eval_generation.py)
| Metric | Score |
|---|---|
| Pass rate (≥80% keyword coverage) | **96%** (71/74) |
| Average keyword score | **98%** |
| Nano calls | 43/74 |
| Mini calls | 31/74 |
| Avg tokens per query | ~2,270 |

The 3 remaining misses:
- `r003` — test keyword mismatch ("violation" vs "prohibit"), answer is factually correct
- `r009` — pedestrian zone fine not co-located in PDF (genuine corpus limitation, model correctly declines to hallucinate)
- `edge001` — resolved after metadata filter fix (zone keywords removed from permit classifier)

---

## Project Structure

```
Boston_Parking/
├── api/
│   ├── main.py                  # FastAPI app — /chat, /health, /sources
│   ├── models.py                # Pydantic request/response schemas
│   └── middleware.py            # Logging, rate limiting, error handling
│
├── chunking/
│   ├── chunk_all.py             # Orchestrator — runs all chunkers
│   ├── chunk_violations.py      # 1 chunk per violation + special chunks
│   ├── chunk_permits.py         # 1 chunk per section + key facts
│   ├── chunk_street_cleaning.py # Per-street assembly + general rules
│   └── chunk_traffic_rules.py   # Section-aware PDF chunking (min 150 chars)
│
├── config/
│   ├── settings.py              # All tunable parameters (models, paths, K values)
│   └── sources.py               # Source registry + staleness tracking
│
├── data/
│   ├── raw/                     # Original source files (gitignored)
│   ├── processed/               # Cleaned, normalized JSON (gitignored)
│   ├── chunks/                  # Final chunks ready for indexing
│   ├── chroma_db/               # ChromaDB persistent store (gitignored)
│   └── bm25_index.pkl           # Serialized BM25 index (gitignored)
│
├── evaluation/
│   ├── test_queries.json        # 74 ground-truth Q&A pairs
│   ├── eval_retrieval.py        # Recall@K and MRR measurement
│   ├── eval_generation.py       # Keyword coverage + model routing stats
│   └── run_eval.py              # Full pipeline eval
│
├── frontend/
│   └── index.html               # Chat UI — Boston civic aesthetic, dark navy/gold
│
├── generation/
│   ├── generator.py             # Nano/mini router + OpenAI API calls
│   ├── prompt_builder.py        # System prompt + context assembly
│   └── response_formatter.py   # Answer cleanup + source extraction
│
├── indexing/
│   ├── build_bm25_index.py      # Builds rank_bm25 index, serializes to disk
│   ├── build_vector_index.py    # Embeds chunks, loads into ChromaDB
│   └── index_manager.py         # Unified lazy-loading singleton for both indexes
│
├── ingestion/
│   ├── run_all.py               # Orchestrator — runs all scrapers
│   ├── scrape_violations.py     # Scrapes boston.gov fines table
│   ├── scrape_permits.py        # Scrapes permit eligibility page
│   ├── download_street_cleaning.py  # Downloads Analyze Boston CSV
│   └── parse_traffic_rules.py   # Downloads + section-parses BTD PDF
│
├── retrieval/
│   ├── bm25_retriever.py        # Sparse BM25 search
│   ├── dense_retriever.py       # ChromaDB cosine similarity search
│   ├── hybrid_retriever.py      # RRF merge of both retrievers
│   ├── metadata_filter.py       # Domain classifier + street name detector
│   └── query_decomposer.py      # GPT-5.4 nano multi-part query splitter
│
├── scripts/
│   └── refresh_data.py          # Staleness-aware re-ingest + re-index
│
├── tests/
│   ├── test_ingestion.py        # 13 tests — processed file structure + content
│   ├── test_chunking.py         # 18 tests — chunk schema, IDs, text quality
│   ├── test_retrieval.py        # 12 tests — BM25, dense, hybrid, RRF logic
│   └── test_generation.py       # 14 tests — prompt building, routing, formatting
│
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## Setup

### Prerequisites
- Python 3.11+
- OpenAI API key

### 1. Create virtual environment
```bash
cd /path/to/Boston_Parking
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY
```

---

## Running the Pipeline

### Step 1 — Ingest all sources
```bash
python3 ingestion/run_all.py
```
Single source:
```bash
python3 ingestion/run_all.py --source violations
python3 ingestion/run_all.py --source permits
python3 ingestion/run_all.py --source street_cleaning
python3 ingestion/run_all.py --source traffic_rules
```

### Step 2 — Chunk all sources
```bash
python3 chunking/chunk_all.py
```
Single source:
```bash
python3 chunking/chunk_all.py --source violations
```

### Step 3 — Build indexes
```bash
python3 indexing/build_bm25_index.py
python3 indexing/build_vector_index.py
```

### Step 4 — Run tests
```bash
pip install pytest
pytest tests/ -v
```
Expected: **71/71 passing**

### Step 5 — Run evaluation
```bash
# Retrieval quality (free — no API calls)
python3 evaluation/eval_retrieval.py

# Generation quality (uses OpenAI API — ~$0.01)
python3 evaluation/eval_generation.py
```

### Step 6 — Start the API
```bash
python3 api/main.py
# API running at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### Step 7 — Open the frontend
```bash
cd frontend
python3 -m http.server 3000
# Open http://localhost:3000 in your browser
```

---

## API Reference

### POST /chat
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the fine for parking near a fire hydrant?"}'
```

**Request:**
```json
{
  "query": "string (required, max 1000 chars)",
  "conversation_history": "[{role, content}] (optional, last 3 turns)",
  "top_k": "integer (optional, default 5, max 20)"
}
```

**Response:**
```json
{
  "answer": "Parking near a fire hydrant in Boston has a base fine of $100...",
  "model_used": "gpt-5.4-nano-2026-03-17",
  "sources": ["Boston Parking Ticket Fines and Codes"],
  "chunks_used": 3,
  "sub_queries": ["What is the fine for parking near a fire hydrant?"],
  "query_type": "violations",
  "usage": {
    "prompt_tokens": 450,
    "completion_tokens": 60,
    "total_tokens": 510
  }
}
```

### GET /health
```bash
curl http://localhost:8000/health
# {"status": "ok", "service": "Boston Parking RAG"}
```

### GET /sources
```bash
curl http://localhost:8000/sources
# Returns all indexed source metadata
```

---

## Data Refresh

Sources have automatic staleness tracking. To refresh:
```bash
python3 scripts/refresh_data.py           # refresh stale sources only
python3 scripts/refresh_data.py --force   # force refresh all sources
python3 scripts/refresh_data.py --check   # status report, no refresh
```

Recommended refresh schedule:
- Street cleaning — every 30 days (seasonal changes)
- Violations + permits — every 90 days
- Traffic rules PDF — annually

---

## Configuration

All tunable parameters live in `config/settings.py`:

```python
# Models
MODEL_NANO = "gpt-5.4-nano-2026-03-17"    # decomposition + simple lookups
MODEL_MINI = "gpt-5.4-mini-2026-03-17"    # regulatory synthesis
EMBEDDING_MODEL = "text-embedding-3-small"

# Retrieval
TOP_K_BM25 = 10      # BM25 candidates before RRF
TOP_K_DENSE = 10     # ChromaDB candidates before RRF
TOP_K_FINAL = 5      # chunks passed to generation after RRF
RRF_K = 60           # RRF constant (standard default)

# Generation
TEMPERATURE = 0.0    # deterministic — regulatory answers must be consistent
```

---

## Known Limitations

- **Pedestrian zone fine** — the $100 fine exists in the violation table but the PDF's pedestrian zone rule section doesn't reference it. A dedicated chunk partially addresses this.
- **Legacy street cleaning dataset** — the Analyze Boston CSV is marked as a legacy dataset. The city's live lookup tool may have more current data for some streets.
- **PDF text extraction** — some sections of the BTD PDF parse as near-empty chunks due to PDF formatting. These are filtered out at chunking time (min 150 chars threshold).
- **Bulk queries** — "list all streets" type queries are not supported by design. The chatbot is built for specific questions, not database exports.

---

## Tech Stack

| Component | Library |
|---|---|
| Vector store | ChromaDB |
| Sparse retrieval | rank-bm25 |
| Embeddings | OpenAI text-embedding-3-small |
| Generation | OpenAI GPT-5.4 nano/mini |
| PDF parsing | PyMuPDF (fitz) |
| Web scraping | BeautifulSoup4 + requests |
| API | FastAPI + uvicorn |
| Testing | pytest |

---

## Contact

Boston Transportation Department: [boston.gov/departments/transportation](https://www.boston.gov/departments/transportation)  
Parking Clerk Office: 1 City Hall Square, Room 224, Boston MA 02201  
Phone: 617-635-4410  
Hours: Monday–Friday, 8:30 a.m. to 4:30 p.m.

---

## Using a Different Model Provider

By default this project uses the OpenAI API. Swapping to a different provider (Anthropic, Google, Ollama, etc.) requires changes in four files beyond `config/settings.py`.

### OpenAI model swap (easiest)
If you just want a different OpenAI model, update these two lines in `config/settings.py`:
```python
MODEL_NANO = "gpt-4o-mini"   # or any OpenAI chat model
MODEL_MINI = "gpt-4o"
EMBEDDING_MODEL = "text-embedding-3-large"  # or text-embedding-ada-002
```
No other changes needed.

### Switching to a different provider (Anthropic, Google, Ollama, etc.)
You need to update four files:

**1. `generation/generator.py`** — replace the OpenAI client and API call:
```python
# Current (OpenAI)
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)
response = client.chat.completions.create(
    model=model,
    messages=messages,
    max_completion_tokens=max_tokens,
    temperature=TEMPERATURE,
)
answer = response.choices[0].message.content.strip()

# Anthropic example
import anthropic
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
response = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=max_tokens,
    messages=messages,
)
answer = response.content[0].text.strip()
```

**2. `retrieval/query_decomposer.py`** — same client swap as above for the decomposition call.

**3. `indexing/build_vector_index.py`** — replace the embedding call:
```python
# Current (OpenAI)
response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
batch_embeddings = [item.embedding for item in response.data]

# Example using sentence-transformers (local, free)
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
batch_embeddings = model.encode(batch).tolist()
```

**4. `retrieval/dense_retriever.py`** — replace the query embedding call with the same approach used in step 3.

### Using a local model (Ollama)
If you want to run fully locally with no API costs:
1. Install [Ollama](https://ollama.ai) and pull a model: `ollama pull llama3`
2. Ollama exposes an OpenAI-compatible API at `http://localhost:11434/v1` — set `OPENAI_API_KEY=ollama` and point the base URL to localhost
3. For embeddings use `sentence-transformers` locally (see step 3 above)
4. Update `MODEL_NANO` and `MODEL_MINI` in `config/settings.py` to your Ollama model name

> **Note:** Local models will produce lower quality regulatory synthesis than GPT-5.4 mini. For a regulatory accuracy-critical use case, a hosted model is strongly recommended.