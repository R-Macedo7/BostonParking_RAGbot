"""
Chunks violation fines data.
Strategy: 1 chunk per violation — they are discrete, self-contained facts.
Each chunk is a natural language sentence for better embedding quality.
"""

import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import SOURCES, DATA_PROCESSED, DATA_CHUNKS


def chunk_violations() -> list[dict]:
    source = SOURCES["violation_fines"]
    processed_path = DATA_PROCESSED / source["processed_file"]
    chunks_path = DATA_CHUNKS / source["chunks_file"]

    data = json.loads(processed_path.read_text(encoding="utf-8"))
    chunks = []

    for i, v in enumerate(data["violations"]):
        violation = v["violation"]
        fine = v["fine_amount"]
        penalty = v["late_penalty"]

        # Natural language format — better for semantic embedding than raw table row
        text = (
            f"Boston parking violation: {violation}. "
            f"The fine is {fine}. "
            f"If unpaid after 21 days, a late penalty of {penalty} is added."
        )

        chunks.append({
            "id": f"violation_{i:03d}",
            "text": text,
            "metadata": {
                "domain": "violations",
                "violation_type": violation,
                "fine_amount": fine,
                "late_penalty": penalty,
                "source": source["url"],
                "source_name": "Boston Parking Ticket Fines and Codes",
            },
        })

    # Summary chunk for general fine structure questions
    chunks.append({
        "id": "violation_summary",
        "text": (
            "Boston parking tickets become overdue 21 days after issuance. "
            "If unpaid within 21 days, a late penalty fee is added to the original fine. "
            "Violations range from $15 (minor infractions) to $120 (handicap-only spaces). "
            "The most expensive violations include parking in handicap-designated spaces ($120), "
            "bike or bus lanes ($100), bus stops ($100), near fire hydrants ($100), "
            "and within fire lanes ($100). Street cleaning violations are $40 daytime or $90 overnight."
        ),
        "metadata": {
            "domain": "violations",
            "violation_type": "summary",
            "source": source["url"],
            "source_name": "Boston Parking Ticket Fines and Codes",
        },
    })

    # Pedestrian zone chunk — co-locates rule and fine in one place
    chunks.append({
        "id": "violation_pedestrian_zone",
        "text": (
            "Boston parking violation: Parking in a Pedestrian Zone. "
            "The fine is $100. If unpaid after 21 days, a late penalty of $33 is added. "
            "Pedestrian zones are designated areas where vehicle parking is prohibited "
            "to protect pedestrian safety and access."
        ),
        "metadata": {
            "domain": "violations",
            "violation_type": "Pedestrian Zone",
            "fine_amount": "$100",
            "late_penalty": "$33",
            "source": source["url"],
            "source_name": "Boston Parking Ticket Fines and Codes",
        },
    })

    # Zone A vs Zone B comparison chunk — surfaces for comparison queries
    chunks.append({
        "id": "violation_zone_comparison",
        "text": (
            "Boston parking Zone A vs Zone B fine comparison: "
            "Zone A is the downtown core of Boston bounded by the Charles River, "
            "Boston University Bridge, Commonwealth Avenue, St. Mary's Street, and Huntington Avenue. "
            "Zone B covers the rest of the city outside Zone A. "
            "Zone A fines are generally higher than Zone B fines. "
            "No Parking Zone A: $90 fine, $18 late penalty. "
            "No Parking Zone B: $55 fine, $8 late penalty. "
            "Double Parking Zone A: $55 fine, $15 late penalty. "
            "Double Parking Zone B: $35 fine, $10 late penalty. "
            "Resident Permit Only: $60 fine, $13 late penalty."
        ),
        "metadata": {
            "domain": "violations",
            "violation_type": "zone_comparison",
            "source": source["url"],
            "source_name": "Boston Parking Ticket Fines and Codes",
        },
    })

    chunks_path.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    print(f"[chunking/violations] {len(chunks)} chunks → {chunks_path}")
    return chunks


if __name__ == "__main__":
    chunk_violations()