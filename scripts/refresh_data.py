"""
Scheduled data refresh script.
Checks which sources are stale and re-ingests + re-chunks + re-indexes them.

Usage:
    python scripts/refresh_data.py           # refresh all stale sources
    python scripts/refresh_data.py --force   # force refresh all sources
    python scripts/refresh_data.py --check   # just report status, no refresh
"""

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import SOURCES
from config.sources import get_source_status, needs_refresh, mark_refreshed


INGEST_MAP = {
    "violation_fines": "ingestion.scrape_violations.scrape_violations",
    "permit_eligibility": "ingestion.scrape_permits.scrape_permits",
    "street_cleaning": "ingestion.download_street_cleaning.download_street_cleaning",
    "traffic_rules": "ingestion.parse_traffic_rules.parse_traffic_rules",
}

CHUNK_MAP = {
    "violation_fines": "chunking.chunk_violations.chunk_violations",
    "permit_eligibility": "chunking.chunk_permits.chunk_permits",
    "street_cleaning": "chunking.chunk_street_cleaning.chunk_street_cleaning",
    "traffic_rules": "chunking.chunk_traffic_rules.chunk_traffic_rules",
}


def import_fn(dotted_path: str):
    """Dynamically import a function by dotted path."""
    module_path, fn_name = dotted_path.rsplit(".", 1)
    import importlib
    module = importlib.import_module(module_path)
    return getattr(module, fn_name)


def refresh_source(source_key: str) -> bool:
    """Ingest + chunk a single source. Returns True on success."""
    print(f"\n── Refreshing: {source_key} ──")
    try:
        ingest_fn = import_fn(INGEST_MAP[source_key])
        chunk_fn = import_fn(CHUNK_MAP[source_key])

        ingest_fn()
        chunk_fn()
        mark_refreshed(source_key)
        print(f"[refresh] ✓ {source_key} refreshed successfully")
        return True
    except Exception as e:
        print(f"[refresh] ✗ {source_key} failed: {e}")
        return False


def rebuild_indexes() -> None:
    """Rebuild both BM25 and vector indexes after refresh."""
    print("\n── Rebuilding indexes ──")
    from indexing.build_bm25_index import build_bm25_index
    from indexing.build_vector_index import build_vector_index
    build_bm25_index()
    build_vector_index()


def main():
    parser = argparse.ArgumentParser(description="Refresh stale Boston Parking data sources")
    parser.add_argument("--force", action="store_true", help="Force refresh all sources")
    parser.add_argument("--check", action="store_true", help="Report status only, no refresh")
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"  Boston Parking RAG — Data Refresh")
    print(f"{'='*50}")

    status = get_source_status(SOURCES)

    print("\nSource status:")
    for s in status:
        staleness = "STALE" if s["stale"] else "fresh"
        print(f"  {s['source']:<25} {staleness:<8} last: {s['last_refreshed']}")

    if args.check:
        return

    stale_sources = (
        list(SOURCES.keys()) if args.force
        else [s["source"] for s in status if s["stale"]]
    )

    if not stale_sources:
        print("\nAll sources are fresh — nothing to refresh.")
        return

    print(f"\nRefreshing {len(stale_sources)} source(s): {stale_sources}")

    successes = []
    for source_key in stale_sources:
        if refresh_source(source_key):
            successes.append(source_key)

    if successes:
        print(f"\nSuccessfully refreshed: {successes}")
        rebuild_indexes()
    else:
        print("\nNo sources refreshed successfully.")


if __name__ == "__main__":
    main()