"""
Evaluates retrieval quality — measures whether the right chunks
are being retrieved for each test query.

Metrics:
- Recall@K: does the relevant chunk appear in top-K results?
- MRR (Mean Reciprocal Rank): how high does the relevant chunk rank?
"""

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from retrieval.hybrid_retriever import hybrid_search
from retrieval.metadata_filter import classify_query


# Domain-to-expected-source mapping for eval
DOMAIN_SOURCE_MAP = {
    "violations": "Boston Parking Ticket Fines and Codes",
    "permits": "Boston Resident Parking Permit Guide",
    "street_cleaning": "Analyze Boston Street Sweeping Schedules",
    "regulations": "City of Boston Traffic Rules and Regulations (March 2025)",
}


def eval_retrieval(top_k: int = 5) -> dict:
    test_path = Path(__file__).parent / "test_queries.json"
    test_queries = json.loads(test_path.read_text(encoding="utf-8"))

    print(f"\n{'='*60}")
    print(f"  Retrieval Evaluation (top_k={top_k})")
    print(f"{'='*60}\n")

    recall_hits = 0
    reciprocal_ranks = []
    results = []

    for test in test_queries:
        qid = test["id"]
        query = test["query"]
        expected_domain = test["domain"]
        expected_keywords = [kw.lower() for kw in test.get("expected_contains", [])]

        intent = classify_query(query)
        chunks = hybrid_search(query, domain_filter=intent.domain_filter, top_k=top_k)

        # Check if any retrieved chunk contains expected keywords
        hit_rank = None
        for rank, chunk in enumerate(chunks):
            chunk_text = chunk["text"].lower()
            keyword_hits = sum(1 for kw in expected_keywords if kw in chunk_text)
            # Consider a hit if chunk contains at least half the expected keywords
            if expected_keywords and keyword_hits >= len(expected_keywords) * 0.5:
                hit_rank = rank + 1
                break

        recall_hit = hit_rank is not None
        rr = 1.0 / hit_rank if hit_rank else 0.0

        if recall_hit:
            recall_hits += 1
        reciprocal_ranks.append(rr)

        status = "✓" if recall_hit else "✗"
        print(f"{status} [{qid}] rank={hit_rank or 'miss'} | {query[:60]}...")
        print(f"   Domain detected: {intent.query_type} | chunks retrieved: {len(chunks)}")

        results.append({
            "id": qid,
            "query": query,
            "recall_hit": recall_hit,
            "hit_rank": hit_rank,
            "reciprocal_rank": rr,
            "domain_detected": intent.query_type,
            "chunks_retrieved": len(chunks),
        })

    recall_at_k = recall_hits / len(test_queries)
    mrr = sum(reciprocal_ranks) / len(reciprocal_ranks)

    print(f"\n{'='*60}")
    print(f"  Recall@{top_k}: {recall_at_k:.0%} ({recall_hits}/{len(test_queries)})")
    print(f"  MRR:      {mrr:.3f}")
    print(f"{'='*60}\n")

    output = {
        "recall_at_k": recall_at_k,
        "mrr": mrr,
        "top_k": top_k,
        "total_queries": len(test_queries),
        "results": results,
    }

    out_path = Path(__file__).parent / "eval_retrieval_results.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Results saved → {out_path}")
    return output


if __name__ == "__main__":
    eval_retrieval()