"""
Chunks permit eligibility data.
Strategy: 1 chunk per section/step — preserves procedural flow.
"""

import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import SOURCES, DATA_PROCESSED, DATA_CHUNKS


def chunk_permits() -> list[dict]:
    source = SOURCES["permit_eligibility"]
    processed_path = DATA_PROCESSED / source["processed_file"]
    chunks_path = DATA_CHUNKS / source["chunks_file"]

    data = json.loads(processed_path.read_text(encoding="utf-8"))
    chunks = []

    for i, section in enumerate(data["sections"]):
        title = section["section_title"]
        content = section["content"]

        # Skip nav/footer junk that got scraped
        skip_keywords = ["skip to", "main menu", "footer", "feedback", "newsletter", "back to top"]
        if any(kw in title.lower() for kw in skip_keywords):
            continue
        if len(content) < 80:
            continue

        text = f"{title}\n\n{content}"

        chunks.append({
            "id": f"permit_{i:03d}",
            "text": text,
            "metadata": {
                "domain": "permits",
                "section_title": title,
                "source": source["url"],
                "source_name": "Boston Resident Parking Permit Guide",
            },
        })

    # Add key fact chunks that are high-frequency questions
    key_facts = [
        {
            "id": "permit_key_registration",
            "text": (
                "To get a Boston resident parking permit, your vehicle registration must show "
                "the car is registered and principally garaged in your name at your current Boston address. "
                "You must provide valid proof of Boston residency."
            ),
        },
        {
            "id": "permit_key_online",
            "text": (
                "Boston residents can apply for a parking permit online at boston.gov/parkingpermits. "
                "New residents should apply within 10 days of their move-in date. "
                "Online approvals take approximately 10 business days to receive the permit by mail."
            ),
        },
        {
            "id": "permit_key_renewal",
            "text": (
                "Boston resident parking permits must be renewed four to six weeks before expiration. "
                "You cannot renew online if your permit has already expired. "
                "You must pay any overdue parking tickets before renewing your permit."
            ),
        },
        {
            "id": "permit_key_inperson",
            "text": (
                "Boston residents can apply for a parking permit in person at Boston City Hall, "
                "1 City Hall Square, Room 224, Monday through Friday, 9 a.m. to 4:30 p.m. "
                "In-person applicants with all required documents receive their permit the same day."
            ),
        },
    ]

    for fact in key_facts:
        chunks.append({
            "id": fact["id"],
            "text": fact["text"],
            "metadata": {
                "domain": "permits",
                "section_title": "Key Facts",
                "source": source["url"],
                "source_name": "Boston Resident Parking Permit Guide",
            },
        })

    chunks_path.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    print(f"[chunking/permits] {len(chunks)} chunks → {chunks_path}")
    return chunks


if __name__ == "__main__":
    chunk_permits()