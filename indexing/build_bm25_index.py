"""
Builds and persists the BM25 sparse index from all chunk files.
"""

import json
import pickle
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import DATA_CHUNKS, BM25_INDEX_PATH, SOURCES


def load_all_chunks() -> list[dict]:
    all_chunks = []
    seen_files = set()
    for source_key, source in SOURCES.items():
        if not source.get("chunks_file"):
            continue
        chunks_file = DATA_CHUNKS / source["chunks_file"]
        if chunks_file in seen_files:
            continue
        seen_files.add(chunks_file)
        if not chunks_file.exists():
            print(f"[bm25] Warning: {chunks_file} not found, skipping")
            continue
        chunks = json.loads(chunks_file.read_text(encoding="utf-8"))
        all_chunks.extend(chunks)
        print(f"[bm25] Loaded {len(chunks)} chunks from {source_key}")
    return all_chunks


def tokenize(text: str) -> list[str]:
    """Simple whitespace + lowercase tokenizer."""
    return text.lower().split()


def build_bm25_index() -> None:
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        raise ImportError("rank-bm25 not installed. Run: pip install rank-bm25")

    BM25_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    chunks = load_all_chunks()
    if not chunks:
        raise ValueError("No chunks found. Run ingestion and chunking first.")

    print(f"[bm25] Building index over {len(chunks)} total chunks...")

    corpus = [tokenize(chunk["text"]) for chunk in chunks]
    bm25 = BM25Okapi(corpus)

    payload = {
        "bm25": bm25,
        "chunks": chunks,
    }

    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump(payload, f)

    print(f"[bm25] Index saved → {BM25_INDEX_PATH}")
    print(f"[bm25] Total documents indexed: {len(chunks)}")


if __name__ == "__main__":
    build_bm25_index()