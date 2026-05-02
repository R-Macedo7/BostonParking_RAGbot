"""
Index manager — loads and manages both BM25 and ChromaDB indexes.
Exposes a unified interface so the retrieval layer never
directly touches index internals.
"""

import pickle
import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import (
    BM25_INDEX_PATH, CHROMA_DIR, CHROMA_COLLECTION,
    EMBEDDING_MODEL, OPENAI_API_KEY,
)


class IndexManager:
    """
    Singleton-friendly manager for both indexes.
    Lazy-loads on first access — no cost if index isn't used.
    """

    def __init__(self):
        self._bm25 = None
        self._bm25_chunks: Optional[list[dict]] = None
        self._chroma_collection = None
        self._openai_client = None
        self._loaded = {"bm25": False, "chroma": False}

    # ── BM25 ──────────────────────────────────────────────────────────────

    def load_bm25(self) -> None:
        if self._loaded["bm25"]:
            return
        if not BM25_INDEX_PATH.exists():
            raise FileNotFoundError(
                f"BM25 index not found at {BM25_INDEX_PATH}. "
                "Run: python indexing/build_bm25_index.py"
            )
        with open(BM25_INDEX_PATH, "rb") as f:
            payload = pickle.load(f)
        self._bm25 = payload["bm25"]
        self._bm25_chunks = payload["chunks"]
        self._loaded["bm25"] = True
        print(f"[IndexManager] BM25 loaded — {len(self._bm25_chunks)} documents")

    @property
    def bm25(self):
        self.load_bm25()
        return self._bm25

    @property
    def bm25_chunks(self) -> list[dict]:
        self.load_bm25()
        return self._bm25_chunks

    # ── ChromaDB ──────────────────────────────────────────────────────────

    def load_chroma(self) -> None:
        if self._loaded["chroma"]:
            return
        try:
            import chromadb
        except ImportError:
            raise ImportError("chromadb not installed. Run: pip install chromadb")

        if not CHROMA_DIR.exists():
            raise FileNotFoundError(
                f"ChromaDB not found at {CHROMA_DIR}. "
                "Run: python indexing/build_vector_index.py"
            )

        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self._chroma_collection = client.get_collection(CHROMA_COLLECTION)
        self._loaded["chroma"] = True
        print(f"[IndexManager] ChromaDB loaded — {self._chroma_collection.count()} vectors")

    @property
    def chroma_collection(self):
        self.load_chroma()
        return self._chroma_collection

    # ── OpenAI Embeddings ─────────────────────────────────────────────────

    def load_openai(self) -> None:
        if self._openai_client is not None:
            return
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai not installed. Run: pip install openai")
        self._openai_client = OpenAI(api_key=OPENAI_API_KEY)

    def embed_query(self, text: str) -> list[float]:
        self.load_openai()
        response = self._openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=[text],
        )
        return response.data[0].embedding

    # ── Status ────────────────────────────────────────────────────────────

    def status(self) -> dict:
        return {
            "bm25_loaded": self._loaded["bm25"],
            "bm25_documents": len(self._bm25_chunks) if self._bm25_chunks else 0,
            "chroma_loaded": self._loaded["chroma"],
            "chroma_vectors": self._chroma_collection.count() if self._chroma_collection else 0,
            "bm25_index_exists": BM25_INDEX_PATH.exists(),
            "chroma_index_exists": CHROMA_DIR.exists(),
        }


# Module-level singleton
_index_manager: Optional[IndexManager] = None


def get_index_manager() -> IndexManager:
    global _index_manager
    if _index_manager is None:
        _index_manager = IndexManager()
    return _index_manager