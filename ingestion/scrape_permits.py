"""
Scrapes the resident parking permit eligibility page from boston.gov.
Outputs: data/raw/permit_eligibility.html
         data/processed/permit_eligibility.json
"""

import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import SOURCES, DATA_RAW, DATA_PROCESSED


def scrape_permits() -> None:
    source = SOURCES["permit_eligibility"]
    raw_path = DATA_RAW / source["raw_file"]
    processed_path = DATA_PROCESSED / source["processed_file"]

    print(f"[permits] Fetching {source['url']}...")
    response = requests.get(source["url"], timeout=30)
    response.raise_for_status()

    raw_path.write_text(response.text, encoding="utf-8")
    print(f"[permits] Raw HTML saved → {raw_path}")

    soup = BeautifulSoup(response.text, "html.parser")

    sections = []

    # Extract step-based sections (new resident, renew, replace)
    # Boston.gov uses h2/h3 headers with step content below
    headers = soup.find_all(["h2", "h3"])
    for header in headers:
        title = header.get_text(strip=True)
        if not title or len(title) < 3:
            continue

        # Gather sibling content until next header
        content_parts = []
        for sibling in header.find_next_siblings():
            if sibling.name in ["h2", "h3"]:
                break
            text = sibling.get_text(separator=" ", strip=True)
            if text:
                content_parts.append(text)

        content_text = " ".join(content_parts)
        skip_titles = ["related content", "feedback", "footer", "menu", "navigation", "contact us"]
        is_junk = any(kw in title.lower() for kw in skip_titles)

        if content_parts and len(content_text) > 50 and not is_junk:
            sections.append({
                "section_title": title,
                "content": content_text,
                "domain": source["domain"],
                "source": source["url"],
            })

    # Also capture any standalone paragraphs with important notes
    notes = []
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text and len(text) > 50:
            notes.append(text)

    output = {
        "sections": sections,
        "notes": notes,
        "source": source["url"],
        "domain": source["domain"],
    }

    processed_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"[permits] Processed → {processed_path} ({len(sections)} sections)")


if __name__ == "__main__":
    scrape_permits()