"""
Hybrid retriever — combines BM25 (sparse) + ChromaDB cosine (dense)
using Reciprocal Rank Fusion (RRF) for final ranking.

Delegates to bm25_retriever.py and dense_retriever.py — this module
is responsible only for the merge logic.
"""

import sys
from pathlib import Path
from typing import Optional

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import TOP_K_BM25, TOP_K_DENSE, TOP_K_FINAL, RRF_K
from retrieval.bm25_retriever import bm25_search
from retrieval.dense_retriever import dense_search


def rrf_merge(
    bm25_results: list[dict],
    dense_results: list[dict],
    k: int = RRF_K,
    top_n: int = TOP_K_FINAL,
) -> list[dict]:
    """
    Reciprocal Rank Fusion.
    RRF score = 1/(k + rank) summed across both retrievers.
    Higher score = appears higher in both lists = better result.
    """
    scores: dict[str, float] = {}
    chunk_map: dict[str, dict] = {}

    for rank, chunk in enumerate(bm25_results):
        cid = chunk["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        chunk_map[cid] = chunk

    for rank, chunk in enumerate(dense_results):
        cid = chunk["id"]
        scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
        chunk_map[cid] = chunk

    sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)

    results = []
    for cid in sorted_ids[:top_n]:
        chunk = chunk_map[cid].copy()
        chunk["rrf_score"] = round(scores[cid], 6)
        results.append(chunk)

    return results


def hybrid_search(
    query: str,
    domain_filter: Optional[str] = None,
    top_k: int = TOP_K_FINAL,
) -> list[dict]:
    """
    Main hybrid retrieval function.
    Runs BM25 + dense search, merges with RRF.

    Args:
        query: The search query string
        domain_filter: Optional domain to filter results
        top_k: Final number of chunks to return after RRF

    Returns:
        Top-k chunks ranked by RRF score
    """
    bm25_results = bm25_search(query, top_k=TOP_K_BM25, domain_filter=domain_filter)
    dense_results = dense_search(query, top_k=TOP_K_DENSE, domain_filter=domain_filter)
    return rrf_merge(bm25_results, dense_results, top_n=top_k)