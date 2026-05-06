"""
Scrapes all three towing-related pages from boston.gov:
  - How to get your towed car back (main guide + fees + payment)
  - Towing companies list (private companies)
  - Towing alerts FAQ (alert system, database lookup)

Outputs: data/raw/towing_*.html
         data/processed/towing_*.json
"""

import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import SOURCES, DATA_RAW, DATA_PROCESSED


SKIP_TITLES = [
    "related content", "feedback", "footer", "menu",
    "navigation", "contact us", "back to top", "share",
]


def scrape_html_source(source_key: str) -> None:
    source = SOURCES[source_key]
    raw_path = DATA_RAW / source["raw_file"]
    processed_path = DATA_PROCESSED / source["processed_file"]

    print(f"[{source_key}] Fetching {source['url']}...")
    response = requests.get(source["url"], timeout=30)
    response.raise_for_status()

    raw_path.write_text(response.text, encoding="utf-8")
    print(f"[{source_key}] Raw HTML saved → {raw_path}")

    soup = BeautifulSoup(response.text, "html.parser")
    sections = []

    headers = soup.find_all(["h2", "h3", "h4"])
    for header in headers:
        title = header.get_text(strip=True)
        if not title or len(title) < 3:
            continue
        if any(kw in title.lower() for kw in SKIP_TITLES):
            continue

        content_parts = []
        for sibling in header.find_next_siblings():
            if sibling.name in ["h2", "h3", "h4"]:
                break
            text = sibling.get_text(separator=" ", strip=True)
            if text and len(text) > 10:
                content_parts.append(text)

        content_text = " ".join(content_parts)
        if len(content_text) > 60:
            sections.append({
                "section_title": title,
                "content": content_text,
                "domain": source["domain"],
                "source": source["url"],
            })

    # Also grab standalone paragraphs not under a header
    notes = []
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text and len(text) > 80:
            notes.append(text)

    output = {
        "sections": sections,
        "notes": notes,
        "source": source["url"],
        "domain": source["domain"],
    }

    processed_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"[{source_key}] Processed → {processed_path} ({len(sections)} sections)")


def scrape_towing() -> None:
    scrape_html_source("towing_guide")
    scrape_html_source("towing_companies")
    scrape_html_source("towing_alerts")


if __name__ == "__main__":
    scrape_towing()