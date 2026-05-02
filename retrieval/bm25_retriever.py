"""
BM25 sparse retriever.
Standalone module — wraps the BM25 index via IndexManager.
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import TOP_K_BM25
from indexing.index_manager import get_index_manager


def tokenize(text: str) -> list[str]:
    return text.lower().split()


def bm25_search(
    query: str,
    top_k: int = TOP_K_BM25,
    domain_filter: str = None,
) -> list[dict]:
    """
    Searches the BM25 index for the given query.
    Optionally filters results by domain metadata after retrieval.

    Args:
        query: The search query string
        top_k: Number of results to return
        domain_filter: Optional domain to filter results (post-retrieval)

    Returns:
        List of chunk dicts with bm25_score added
    """
    manager = get_index_manager()
    tokens = tokenize(query)
    scores = manager.bm25.get_scores(tokens)

    # Rank all documents by score
    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )

    results = []
    for idx in top_indices:
        if len(results) >= top_k:
            break
        if scores[idx] <= 0:
            continue

        chunk = manager.bm25_chunks[idx].copy()

        # Apply domain filter if specified
        if domain_filter:
            chunk_domain = chunk.get("metadata", {}).get("domain", "")
            if chunk_domain != domain_filter:
                continue

        chunk["bm25_score"] = float(scores[idx])
        results.append(chunk)

    return results