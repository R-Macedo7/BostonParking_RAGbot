"""
Orchestrates the full ingestion pipeline.
Run this to (re)ingest all sources.

Usage:
    python ingestion/run_all.py
    python ingestion/run_all.py --source violations
    python ingestion/run_all.py --source street_cleaning
    python ingestion/run_all.py --source towing
"""

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import DATA_RAW, DATA_PROCESSED, DATA_CHUNKS


def run_all(source_filter: str = None):
    # Ensure directories exist
    for d in [DATA_RAW, DATA_PROCESSED, DATA_CHUNKS]:
        d.mkdir(parents=True, exist_ok=True)

    from ingestion.scrape_violations import scrape_violations
    from ingestion.scrape_permits import scrape_permits
    from ingestion.download_street_cleaning import download_street_cleaning
    from ingestion.parse_traffic_rules import parse_traffic_rules
    from ingestion.scrape_towing import scrape_towing

    sources = {
        "violations": scrape_violations,
        "permits": scrape_permits,
        "street_cleaning": download_street_cleaning,
        "traffic_rules": parse_traffic_rules,
        "towing": scrape_towing,
    }

    if source_filter:
        if source_filter not in sources:
            print(f"Unknown source: {source_filter}. Options: {list(sources.keys())}")
            sys.exit(1)
        sources = {source_filter: sources[source_filter]}

    print(f"\n{'='*50}")
    print(f"  Boston Parking RAG — Ingestion Pipeline")
    print(f"{'='*50}\n")

    results = {}
    for name, fn in sources.items():
        print(f"\n── Running: {name} ──")
        try:
            fn()
            results[name] = "✓ success"
        except Exception as e:
            results[name] = f"✗ failed: {e}"
            print(f"[ERROR] {name}: {e}")

    print(f"\n{'='*50}")
    print("  Ingestion Summary")
    print(f"{'='*50}")
    for name, result in results.items():
        print(f"  {name:<20} {result}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Boston Parking ingestion pipeline")
    parser.add_argument("--source", type=str, help="Run a single source only", default=None)
    args = parser.parse_args()
    run_all(args.source)