"""
Source registry with refresh tracking.
Tracks when each source was last ingested and whether it needs refreshing.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent
REFRESH_LOG = BASE_DIR / "data" / "refresh_log.json"


def load_refresh_log() -> dict:
    if REFRESH_LOG.exists():
        return json.loads(REFRESH_LOG.read_text(encoding="utf-8"))
    return {}


def save_refresh_log(log: dict) -> None:
    REFRESH_LOG.parent.mkdir(parents=True, exist_ok=True)
    REFRESH_LOG.write_text(json.dumps(log, indent=2, default=str), encoding="utf-8")


def mark_refreshed(source_key: str) -> None:
    """Call this after successfully ingesting a source."""
    log = load_refresh_log()
    log[source_key] = datetime.now().isoformat()
    save_refresh_log(log)


def needs_refresh(source_key: str, refresh_days: int) -> bool:
    """Returns True if source hasn't been ingested within its refresh window."""
    log = load_refresh_log()
    if source_key not in log:
        return True
    last_refreshed = datetime.fromisoformat(log[source_key])
    return datetime.now() - last_refreshed > timedelta(days=refresh_days)


def get_stale_sources(sources: dict) -> list[str]:
    """Returns list of source keys that are past their refresh window."""
    stale = []
    for key, config in sources.items():
        if needs_refresh(key, config["refresh_days"]):
            stale.append(key)
    return stale


def get_source_status(sources: dict) -> list[dict]:
    """Returns status report for all sources."""
    log = load_refresh_log()
    status = []
    for key, config in sources.items():
        last_refreshed = log.get(key)
        stale = needs_refresh(key, config["refresh_days"])
        status.append({
            "source": key,
            "domain": config["domain"],
            "last_refreshed": last_refreshed or "never",
            "refresh_days": config["refresh_days"],
            "stale": stale,
        })
    return status