"""
Dense retriever — ChromaDB cosine similarity search via OpenAI embeddings.
Standalone module wrapping ChromaDB via IndexManager.
"""

import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import TOP_K_DENSE
from indexing.index_manager import get_index_manager


def dense_search(
    query: str,
    top_k: int = TOP_K_DENSE,
    domain_filter: Optional[str] = None,
) -> list[dict]:
    """
    Searches the ChromaDB vector index using cosine similarity.

    Args:
        query: The search query string
        top_k: Number of results to return
        domain_filter: Optional ChromaDB 'where' filter by domain

    Returns:
        List of chunk dicts with cosine_score added
    """
    manager = get_index_manager()

    # Embed the query
    query_embedding = manager.embed_query(query)

    # Build optional metadata filter for ChromaDB
    where = {"domain": {"$eq": domain_filter}} if domain_filter else None

    results = manager.chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for i, doc_id in enumerate(results["ids"][0]):
        # ChromaDB returns L2 distance for cosine space — convert to similarity
        cosine_similarity = float(1 - results["distances"][0][i])
        chunks.append({
            "id": doc_id,
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "cosine_score": cosine_similarity,
        })

    return chunks