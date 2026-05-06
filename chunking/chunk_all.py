"""
Orchestrates the full chunking pipeline.
Run this after ingestion/run_all.py completes.

Usage:
    python chunking/chunk_all.py
    python chunking/chunk_all.py --source violations
    python chunking/chunk_all.py --source towing
"""

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import DATA_CHUNKS


def run_all(source_filter: str = None):
    DATA_CHUNKS.mkdir(parents=True, exist_ok=True)

    from chunking.chunk_violations import chunk_violations
    from chunking.chunk_permits import chunk_permits
    from chunking.chunk_street_cleaning import chunk_street_cleaning
    from chunking.chunk_traffic_rules import chunk_traffic_rules
    from chunking.chunk_towing import chunk_towing

    sources = {
        "violations": chunk_violations,
        "permits": chunk_permits,
        "street_cleaning": chunk_street_cleaning,
        "traffic_rules": chunk_traffic_rules,
        "towing": chunk_towing,
    }

    if source_filter:
        if source_filter not in sources:
            print(f"Unknown source: {source_filter}. Options: {list(sources.keys())}")
            sys.exit(1)
        sources = {source_filter: sources[source_filter]}

    print(f"\n{'='*50}")
    print(f"  Boston Parking RAG — Chunking Pipeline")
    print(f"{'='*50}\n")

    results = {}
    for name, fn in sources.items():
        print(f"\n── Chunking: {name} ──")
        try:
            fn()
            results[name] = "✓ success"
        except Exception as e:
            results[name] = f"✗ failed: {e}"
            print(f"[ERROR] {name}: {e}")

    print(f"\n{'='*50}")
    print("  Chunking Summary")
    print(f"{'='*50}")
    for name, result in results.items():
        print(f"  {name:<20} {result}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Boston Parking chunking pipeline")
    parser.add_argument("--source", type=str, help="Chunk a single source only", default=None)
    args = parser.parse_args()
    run_all(args.source)