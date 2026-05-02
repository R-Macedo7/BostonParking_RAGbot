"""
Scrapes the parking violation fines table from boston.gov.
Outputs: data/raw/violation_fines.html
         data/processed/violation_fines.json
"""

import json
import requests
from bs4 import BeautifulSoup
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import SOURCES, DATA_RAW, DATA_PROCESSED


def scrape_violations() -> None:
    source = SOURCES["violation_fines"]
    raw_path = DATA_RAW / source["raw_file"]
    processed_path = DATA_PROCESSED / source["processed_file"]

    print(f"[violations] Fetching {source['url']}...")
    response = requests.get(source["url"], timeout=30)
    response.raise_for_status()

    # Save raw HTML
    raw_path.write_text(response.text, encoding="utf-8")
    print(f"[violations] Raw HTML saved → {raw_path}")

    # Parse fines table
    soup = BeautifulSoup(response.text, "html.parser")
    tables = soup.find_all("table")

    violations = []
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            # Skip header rows and empty rows
            if len(cells) >= 2 and cells[0] and not cells[0].upper().startswith("VIOLATION"):
                entry = {
                    "violation": cells[0],
                    "fine_amount": cells[1] if len(cells) > 1 else "",
                    "late_penalty": cells[2] if len(cells) > 2 else "",
                    "domain": source["domain"],
                    "source": source["url"],
                }
                violations.append(entry)

    # Parse vehicle type codes
    vehicle_codes = []
    code_tables = soup.find_all("table")
    for table in code_tables[1:]:  # skip fines table
        rows = table.find_all("tr")
        for row in rows:
            cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if len(cells) >= 2 and cells[0] and not cells[0].upper() in ["CODE", "COLOR"]:
                vehicle_codes.append({"code": cells[0], "description": cells[1]})

    output = {
        "violations": violations,
        "vehicle_codes": vehicle_codes,
        "source": source["url"],
        "domain": source["domain"],
    }

    processed_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"[violations] Processed → {processed_path} ({len(violations)} violations)")


if __name__ == "__main__":
    scrape_violations()