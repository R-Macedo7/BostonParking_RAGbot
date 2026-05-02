"""
Embeds all chunks and loads them into ChromaDB for dense retrieval.
Uses OpenAI text-embedding-3-small.
"""

import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import (
    DATA_CHUNKS, CHROMA_DIR, CHROMA_COLLECTION,
    EMBEDDING_MODEL, OPENAI_API_KEY, SOURCES
)


def truncate_text(text: str, max_chars: int = 30000) -> str:
    """Truncate text to avoid exceeding embedding token limit (8192 tokens ≈ 30000 chars)."""
    return text[:max_chars] if len(text) > max_chars else text


def load_all_chunks() -> list[dict]:
    all_chunks = []
    for source_key, source in SOURCES.items():
        chunks_file = DATA_CHUNKS / source["chunks_file"]
        if not chunks_file.exists():
            print(f"[vector] Warning: {chunks_file} not found, skipping")
            continue
        chunks = json.loads(chunks_file.read_text(encoding="utf-8"))
        all_chunks.extend(chunks)
        print(f"[vector] Loaded {len(chunks)} chunks from {source_key}")
    return all_chunks


def get_embeddings(texts: list[str], client) -> list[list[float]]:
    """Batch embed texts using OpenAI API."""
    BATCH_SIZE = 100
    all_embeddings = []

    # Truncate any oversized chunks before embedding
    texts = [truncate_text(t) for t in texts]

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        print(f"[vector] Embedding batch {i // BATCH_SIZE + 1}/{(len(texts) - 1) // BATCH_SIZE + 1}...")
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch
        )
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


def build_vector_index() -> None:
    try:
        import chromadb
        from openai import OpenAI
    except ImportError as e:
        raise ImportError(f"Missing dependency: {e}. Run: pip install chromadb openai")

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    chunks = load_all_chunks()
    if not chunks:
        raise ValueError("No chunks found. Run ingestion and chunking first.")

    print(f"[vector] Building vector index over {len(chunks)} chunks...")

    # Initialize clients
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # Delete existing collection if rebuilding
    try:
        chroma_client.delete_collection(CHROMA_COLLECTION)
        print(f"[vector] Deleted existing collection '{CHROMA_COLLECTION}'")
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name=CHROMA_COLLECTION,
        metadata={"hnsw:space": "cosine"}
    )

    # Embed all chunk texts
    texts = [chunk["text"] for chunk in chunks]
    embeddings = get_embeddings(texts, openai_client)

    # Load into ChromaDB in batches
    BATCH_SIZE = 100
    for i in range(0, len(chunks), BATCH_SIZE):
        batch_chunks = chunks[i:i + BATCH_SIZE]
        batch_embeddings = embeddings[i:i + BATCH_SIZE]

        collection.add(
            ids=[c["id"] for c in batch_chunks],
            embeddings=batch_embeddings,
            documents=[c["text"] for c in batch_chunks],
            metadatas=[c["metadata"] for c in batch_chunks],
        )

    print(f"[vector] ChromaDB collection '{CHROMA_COLLECTION}' built → {CHROMA_DIR}")
    print(f"[vector] Total vectors indexed: {collection.count()}")


if __name__ == "__main__":
    build_vector_index()