"""
Downloads the street cleaning schedule CSV from Analyze Boston open data portal.
Outputs: data/raw/street_cleaning.csv
         data/processed/street_cleaning.json

Note: The CSV is row-per-street-segment. We normalize it here into
per-street records grouping odd/even sides together.
"""

import csv
import json
import requests
from pathlib import Path
from collections import defaultdict
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import SOURCES, DATA_RAW, DATA_PROCESSED


def download_street_cleaning() -> None:
    source = SOURCES["street_cleaning"]
    raw_path = DATA_RAW / source["raw_file"]
    processed_path = DATA_PROCESSED / source["processed_file"]

    print(f"[street_cleaning] Fetching CSV...")
    response = requests.get(source["url"], timeout=60)
    response.raise_for_status()

    raw_path.write_bytes(response.content)
    print(f"[street_cleaning] Raw CSV saved → {raw_path}")

    # Parse CSV
    rows = []
    content = response.content.decode("utf-8", errors="replace")
    reader = csv.DictReader(content.splitlines())
    for row in reader:
        rows.append(row)

    print(f"[street_cleaning] Parsed {len(rows)} raw rows")

    # Normalize: group by street name + neighborhood + from/to range
    # A street can have multiple rows (odd side, even side, different hours)
    streets = defaultdict(list)
    for row in rows:
        key = (
            row.get("st_name", "").strip().upper(),
            row.get("dist_name", "").strip(),
        )
        streets[key].append({
            "street_name": row.get("st_name", "").strip(),
            "neighborhood": row.get("dist_name", "").strip(),
            "district": row.get("dist", "").strip(),
            "start_time": row.get("start_time", "").strip(),
            "end_time": row.get("end_time", "").strip(),
            "side": row.get("side", "Both").strip(),
            "from_street": row.get("from", "").strip(),
            "to_street": row.get("to", "").strip(),
            "week_1": row.get("week_1", "f").strip() == "t",
            "week_2": row.get("week_2", "f").strip() == "t",
            "week_3": row.get("week_3", "f").strip() == "t",
            "week_4": row.get("week_4", "f").strip() == "t",
            "week_5": row.get("week_5", "f").strip() == "t",
            "monday": row.get("monday", "f").strip() == "t",
            "tuesday": row.get("tuesday", "f").strip() == "t",
            "wednesday": row.get("wednesday", "f").strip() == "t",
            "thursday": row.get("thursday", "f").strip() == "t",
            "friday": row.get("friday", "f").strip() == "t",
            "saturday": row.get("saturday", "f").strip() == "t",
            "sunday": row.get("sunday", "f").strip() == "t",
            "year_round": row.get("year_round", "f").strip() == "t",
        })

    # Convert to list of street records
    street_records = []
    for (street_name, neighborhood), segments in streets.items():
        street_records.append({
            "street_name": street_name,
            "neighborhood": neighborhood,
            "segments": segments,
            "domain": source["domain"],
            "source": source["url"],
        })

    output = {
        "streets": street_records,
        "total_streets": len(street_records),
        "total_segments": len(rows),
        "source": source["url"],
        "domain": source["domain"],
    }

    processed_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"[street_cleaning] Processed → {processed_path} ({len(street_records)} streets, {len(rows)} segments)")


if __name__ == "__main__":
    download_street_cleaning()