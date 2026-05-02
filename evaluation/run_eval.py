"""
Runs evaluation over test_queries.json and reports retrieval + generation quality.

Usage:
    python evaluation/run_eval.py
"""

import json
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from api.main import run_rag_pipeline


def run_eval():
    test_path = Path(__file__).parent / "test_queries.json"
    test_queries = json.loads(test_path.read_text(encoding="utf-8"))

    print(f"\n{'='*60}")
    print(f"  Boston Parking RAG — Evaluation")
    print(f"  {len(test_queries)} test queries")
    print(f"{'='*60}\n")

    results = []
    passed = 0

    for test in test_queries:
        qid = test["id"]
        query = test["query"]
        expected = test.get("expected_contains", [])

        try:
            start = time.time()
            result = run_rag_pipeline(query)
            elapsed = time.time() - start

            answer = result["answer"].lower()
            hits = [kw for kw in expected if kw.lower() in answer]
            misses = [kw for kw in expected if kw.lower() not in answer]
            score = len(hits) / len(expected) if expected else 1.0

            status = "✓" if score >= 0.8 else "✗"
            if score >= 0.8:
                passed += 1

            print(f"{status} [{qid}] ({elapsed:.1f}s) model={result['model_used'].split('-')[0]+'-'+result['model_used'].split('-')[1]}")
            print(f"   Q: {query[:70]}...")
            print(f"   Score: {score:.0%} | Hits: {hits} | Misses: {misses}")
            print(f"   Chunks: {result['chunks_used']} | Type: {result['query_type']}")
            print()

            results.append({
                "id": qid,
                "query": query,
                "score": score,
                "passed": score >= 0.8,
                "elapsed": elapsed,
                "model": result["model_used"],
                "answer_preview": result["answer"][:200],
            })

        except Exception as e:
            print(f"✗ [{qid}] ERROR: {e}\n")
            results.append({"id": qid, "query": query, "score": 0, "passed": False, "error": str(e)})

    print(f"{'='*60}")
    print(f"  Results: {passed}/{len(test_queries)} passed ({passed/len(test_queries):.0%})")
    avg_score = sum(r["score"] for r in results) / len(results)
    print(f"  Average score: {avg_score:.0%}")
    print(f"{'='*60}\n")

    # Save results
    output_path = Path(__file__).parent / "eval_results.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Full results saved → {output_path}")


if __name__ == "__main__":
    run_eval()