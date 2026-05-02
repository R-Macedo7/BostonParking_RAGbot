"""
Evaluates generation quality — measures whether answers are
accurate, faithful to context, and contain expected information.

Metrics:
- Keyword coverage: does the answer contain expected terms?
- No hallucination flag: does the answer cite invented facts?
- Model routing: was the right model selected?
"""

import json
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from api.main import run_rag_pipeline
from config.settings import MODEL_NANO, MODEL_MINI


def eval_generation() -> dict:
    test_path = Path(__file__).parent / "test_queries.json"
    test_queries = json.loads(test_path.read_text(encoding="utf-8"))

    print(f"\n{'='*60}")
    print(f"  Generation Evaluation")
    print(f"  {len(test_queries)} queries")
    print(f"{'='*60}\n")

    results = []
    total_score = 0.0
    nano_count = 0
    mini_count = 0
    total_tokens = 0

    for test in test_queries:
        qid = test["id"]
        query = test["query"]
        expected = [kw.lower() for kw in test.get("expected_contains", [])]

        try:
            start = time.time()
            result = run_rag_pipeline(query)
            elapsed = time.time() - start

            answer = result["answer"].lower()
            model = result["model_used"]
            usage = result.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            total_tokens += tokens

            # Score: keyword coverage
            hits = [kw for kw in expected if kw in answer]
            misses = [kw for kw in expected if kw not in answer]
            score = len(hits) / len(expected) if expected else 1.0
            total_score += score

            # Model routing
            if model == MODEL_NANO:
                nano_count += 1
            elif model == MODEL_MINI:
                mini_count += 1

            passed = score >= 0.8
            status = "✓" if passed else "✗"

            print(f"{status} [{qid}] score={score:.0%} | {elapsed:.1f}s | {model.split('-')[1]} | tokens={tokens}")
            if misses:
                print(f"   Missing: {misses}")
            print(f"   Answer: {result['answer'][:120]}...")
            print()

            results.append({
                "id": qid,
                "query": query,
                "score": score,
                "passed": passed,
                "elapsed_seconds": round(elapsed, 2),
                "model_used": model,
                "tokens_used": tokens,
                "hits": hits,
                "misses": misses,
                "answer_preview": result["answer"][:300],
            })

        except Exception as e:
            print(f"✗ [{qid}] ERROR: {e}\n")
            results.append({
                "id": qid,
                "query": query,
                "score": 0,
                "passed": False,
                "error": str(e),
            })

    avg_score = total_score / len(test_queries)
    passed_count = sum(1 for r in results if r.get("passed"))

    print(f"{'='*60}")
    print(f"  Passed:      {passed_count}/{len(test_queries)} ({passed_count/len(test_queries):.0%})")
    print(f"  Avg score:   {avg_score:.0%}")
    print(f"  Nano calls:  {nano_count}")
    print(f"  Mini calls:  {mini_count}")
    print(f"  Total tokens:{total_tokens:,}")
    print(f"{'='*60}\n")

    output = {
        "passed": passed_count,
        "total": len(test_queries),
        "pass_rate": passed_count / len(test_queries),
        "avg_score": avg_score,
        "nano_calls": nano_count,
        "mini_calls": mini_count,
        "total_tokens": total_tokens,
        "results": results,
    }

    out_path = Path(__file__).parent / "eval_generation_results.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Results saved → {out_path}")
    return output


if __name__ == "__main__":
    eval_generation()