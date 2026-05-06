"""
Chunks towing data from all three towing sources.
Strategy: section-based chunks + key fact chunks for high-frequency questions.
"""

import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import SOURCES, DATA_PROCESSED, DATA_CHUNKS


def load_sections(source_key: str) -> list[dict]:
    source = SOURCES[source_key]
    path = DATA_PROCESSED / source["processed_file"]
    if not path.exists():
        print(f"[chunking/towing] Warning: {path} not found, skipping")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("sections", [])


def chunk_towing() -> list[dict]:
    chunks = []

    # ── Key fact chunks (always included, high-frequency queries) ──

    chunks.append({
        "id": "towing_city_lot",
        "text": (
            "The City of Boston Tow Lot is located at 200 Frontage Road, South Boston, MA 02118. "
            "All vehicles towed by the city are taken to this single location regardless of "
            "where in Boston the vehicle was towed from. "
            "Phone: 617-635-3900. Email: btd@boston.gov. "
            "Hours: Monday through Friday, 7:00 a.m. to 10:30 p.m. "
            "Automated kiosks are available 24 hours a day, 7 days a week for vehicle releases."
        ),
        "metadata": {
            "domain": "towing",
            "section_title": "City Tow Lot Location and Hours",
            "source": SOURCES["towing_guide"]["url"],
            "source_name": "Boston Towing Guide",
        },
    })

    chunks.append({
        "id": "towing_fees_payment",
        "text": (
            "Boston city tow fees and accepted payment: "
            "The City of Boston charges a $90 tow fee plus a storage fee of $3 per hour, "
            "up to a maximum of $15 per day. "
            "At the tow lot office, accepted payment methods are cash, money order, "
            "cashier's check, or debit/credit card. "
            "At the automated kiosk, accepted payment is cash, VISA, Mastercard, or Discover card. "
            "Credit and debit cards at the kiosk are subject to a 2.5 percent fee. "
            "For private company tows, the maximum involuntary tow rate is $132. "
            "Private storage rates are $35 per 24-hour period."
        ),
        "metadata": {
            "domain": "towing",
            "section_title": "Towing Fees and Payment",
            "source": SOURCES["towing_guide"]["url"],
            "source_name": "Boston Towing Guide",
        },
    })

    chunks.append({
        "id": "towing_find_car",
        "text": (
            "How to find your towed car in Boston: "
            "If you know your license plate number, search the online towed cars database at boston.gov — "
            "it has information for the past 15 days. "
            "You can also call the Boston Police Tow Line at 617-343-4629 to find out "
            "which company towed your car. "
            "If you don't know your plate number, call Boston Police at 617-343-4629 and "
            "provide the make, model, color, and address where the car was towed from. "
            "For cars towed to the City Tow Lot, call 617-635-3900. "
            "You can sign up for towing alerts at boston.gov to receive notification "
            "within 10 minutes of your car being towed."
        ),
        "metadata": {
            "domain": "towing",
            "section_title": "How to Find Your Towed Car",
            "source": SOURCES["towing_guide"]["url"],
            "source_name": "Boston Towing Guide",
        },
    })

    chunks.append({
        "id": "towing_reasons",
        "text": (
            "Common reasons for getting towed in Boston and appeal rights: "
            "Street cleaning or sweeping violations are the most common reason for towing. "
            "Other common reasons include illegal parking, and having five or more overdue parking tickets. "
            "If your vehicle was towed for five or more unpaid tickets, you must pay all overdue "
            "tickets and fees before retrieving your car — you are not eligible for a hearing. "
            "If towed for illegal parking, you CAN appeal — you can request a walk-in hearing "
            "within five days of the tow at the Parking Clerk office, or schedule a hearing "
            "by calling 617-635-4410. "
            "Cars towed on state roads like Storrow Drive or the Jamaicaway fall under "
            "Massachusetts State Police jurisdiction — the City of Boston does not have access "
            "to that data."
        ),
        "metadata": {
            "domain": "towing",
            "section_title": "Reasons for Towing and Appeals",
            "source": SOURCES["towing_guide"]["url"],
            "source_name": "Boston Towing Guide",
        },
    })

    chunks.append({
        "id": "towing_private_vs_city",
        "text": (
            "City tow lot vs private tow company in Boston: "
            "If your car was towed by the city, it will be at the City of Boston Tow Lot "
            "at 200 Frontage Road, South Boston. Call 617-635-3900. "
            "If your car was towed by a private company (common for street sweeping violations), "
            "it could be at any private lot. Call Boston Police at 617-343-4629 to find out "
            "which company has it, then contact that company directly. "
            "If the Boston Police requested the tow, you must go to the police station "
            "before picking up your vehicle from the private company. "
            "The city publishes a list of private towing companies at boston.gov/towing-companies."
        ),
        "metadata": {
            "domain": "towing",
            "section_title": "City vs Private Tow Companies",
            "source": SOURCES["towing_guide"]["url"],
            "source_name": "Boston Towing Guide",
        },
    })

    chunks.append({
        "id": "towing_alerts",
        "text": (
            "Boston towing alerts system: "
            "You can sign up for free towing alerts at boston.gov to receive phone, email, "
            "or text notifications when your car is towed. "
            "Alerts are sent within 10 minutes of a tow being reported to the Boston Police database. "
            "The system covers cars towed to the city lot and private lots, "
            "but does NOT cover cars towed by the Massachusetts State Police. "
            "You can register up to 10 license plates per email address. "
            "Note: towing companies that repossess vehicles may also use this alert system, "
            "which could result in repossession at the tow lot before the owner arrives."
        ),
        "metadata": {
            "domain": "towing",
            "section_title": "Towing Alert System",
            "source": SOURCES["towing_alerts"]["url"],
            "source_name": "Boston Towing Alerts",
        },
    })

    chunks.append({
        "id": "towing_abandoned_vehicles",
        "text": (
            "Abandoned vehicles in Boston: "
            "If an abandoned car is not removed from a public way, the city tows it to "
            "the Boston Transportation Department Tow Lot at 200 Frontage Road. "
            "Once towed, an abandoned car may be disposed of at any time. "
            "If the car has value it may be stored and auctioned after 30 days. "
            "The fine for abandoning a vehicle is $250 for a first offense and $500 for each offense after. "
            "To recover an abandoned vehicle you need a valid driver's license, proof of registration, "
            "insurance, and payment of all tow and storage fees. "
            "Report abandoned vehicles through BOS:311."
        ),
        "metadata": {
            "domain": "towing",
            "section_title": "Abandoned Vehicles",
            "source": SOURCES["towing_guide"]["url"],
            "source_name": "Boston Towing Guide",
        },
    })

    # ── Section-based chunks from scraped pages ────────────────────

    for source_key, source_name in [
        ("towing_guide", "Boston Towing Guide"),
        ("towing_companies", "Boston Towing Companies"),
        ("towing_alerts", "Boston Towing Alerts"),
    ]:
        sections = load_sections(source_key)
        for i, section in enumerate(sections):
            title = section.get("section_title", "")
            content = section.get("content", "")

            skip = [
                "related content", "feedback", "step 1", "step 2", "step 3",
                "back to top", "share", "contact", "sign up"
            ]
            if any(kw in title.lower() for kw in skip):
                continue
            if len(content) < 80:
                continue

            chunk_text = f"{title}\n\n{content}"
            chunks.append({
                "id": f"towing_{source_key}_{i:03d}",
                "text": chunk_text,
                "metadata": {
                    "domain": "towing",
                    "section_title": title,
                    "source": SOURCES[source_key]["url"],
                    "source_name": source_name,
                },
            })

    # Write combined chunks to a single file
    source = SOURCES["towing_guide"]
    chunks_path = DATA_CHUNKS / "towing_chunks.json"
    chunks_path.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    print(f"[chunking/towing] {len(chunks)} chunks → {chunks_path}")
    return chunks


if __name__ == "__main__":
    chunk_towing()