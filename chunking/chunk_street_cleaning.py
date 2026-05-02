"""
Chunks street cleaning data.
Strategy: 1 chunk per street (assembling all segments/sides into a
human-readable natural language description).

This is the most important chunking file — raw CSV rows are not
directly queryable. We assemble them into readable descriptions.
"""

import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import SOURCES, DATA_PROCESSED, DATA_CHUNKS

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
WEEKS = ["week_1", "week_2", "week_3", "week_4", "week_5"]


def format_days(segment: dict) -> str:
    active_days = [day.capitalize() for day in DAYS if segment.get(day)]
    return ", ".join(active_days) if active_days else "unknown days"


def format_weeks(segment: dict) -> str:
    active_weeks = []
    week_names = ["1st", "2nd", "3rd", "4th", "5th"]
    for i, week_key in enumerate(WEEKS):
        if segment.get(week_key):
            active_weeks.append(week_names[i])
    if not active_weeks:
        return "every week"
    if len(active_weeks) == 5:
        return "every week"
    return f"the {', '.join(active_weeks)} week(s) of the month"


def format_time(start: str, end: str) -> str:
    def fmt(t):
        if not t:
            return "unknown"
        h, m = t.split(":")[:2]
        h = int(h)
        period = "AM" if h < 12 else "PM"
        if h > 12:
            h -= 12
        if h == 0:
            h = 12
        return f"{h}:{m} {period}"
    return f"{fmt(start)} to {fmt(end)}"


def segment_to_text(segment: dict, street_name: str, neighborhood: str) -> str:
    side = segment.get("side", "Both sides")
    time_range = format_time(segment.get("start_time", ""), segment.get("end_time", ""))
    days = format_days(segment)
    weeks = format_weeks(segment)
    from_st = segment.get("from_street", "")
    to_st = segment.get("to_street", "")
    year_round = segment.get("year_round", False)

    location = f"{street_name}"
    if from_st and to_st:
        location += f" between {from_st} and {to_st}"
    if side and side.lower() not in ["both", ""]:
        location += f" ({side} side)"

    season = "year-round" if year_round else "April 1 to November 30"

    return (
        f"Street cleaning for {location} in {neighborhood}: "
        f"No parking on {days} {weeks}, from {time_range}. "
        f"Program runs {season}."
    )


def chunk_street_cleaning() -> list[dict]:
    source = SOURCES["street_cleaning"]
    processed_path = DATA_PROCESSED / source["processed_file"]
    chunks_path = DATA_CHUNKS / source["chunks_file"]

    data = json.loads(processed_path.read_text(encoding="utf-8"))
    chunks = []

    for street_record in data["streets"]:
        street_name = street_record["street_name"]
        neighborhood = street_record["neighborhood"]
        segments = street_record["segments"]

        if not segments:
            continue

        segment_texts = []
        for seg in segments:
            segment_texts.append(segment_to_text(seg, street_name, neighborhood))

        combined_text = " | ".join(segment_texts)

        first_seg = segments[0]
        summary = (
            f"{street_name} in {neighborhood}: "
            f"Street cleaning on {format_days(first_seg)}, "
            f"{format_time(first_seg.get('start_time', ''), first_seg.get('end_time', ''))}, "
            f"{format_weeks(first_seg)}."
        )

        chunk_text = f"{summary}\n\nFull schedule details: {combined_text}"

        chunks.append({
            "id": f"street_{street_name.replace(' ', '_').lower()}_{neighborhood.replace(' ', '_').lower()}",
            "text": chunk_text,
            "metadata": {
                "domain": "street_cleaning",
                "street_name": street_name,
                "neighborhood": neighborhood,
                "source": source["url"],
                "source_name": "Analyze Boston Street Sweeping Schedules",
            },
        })

    # General rules chunk
    chunks.append({
        "id": "street_cleaning_general_rules",
        "text": (
            "Boston street cleaning general rules: "
            "The Daytime Street Cleaning Program runs April 1 to November 30 in most neighborhoods. "
            "The North End, South End, and Beacon Hill programs run March 1 to December 31. "
            "Daytime street cleaning tickets cost $40. "
            "Overnight street cleaning tickets (12:01 AM to 7:00 AM) cost $90. "
            "Charlestown daytime street cleaning tickets cost $90. "
            "Street cleaning is NOT canceled for light rain. "
            "On city holidays, daytime sweeping is suspended but overnight sweeping continues. "
            "If your street is cleaned every week, it is also cleaned on the 5th week of the month. "
            "If cleaned every other week, the 5th week is NOT enforced. "
            "Always obey the posted street sign — it overrides online schedules if there is a conflict."
        ),
        "metadata": {
            "domain": "street_cleaning",
            "street_name": "general",
            "neighborhood": "all",
            "source": source["url"],
            "source_name": "Boston Street Cleaning Rules",
        },
    })

    # Dedicated holiday chunk
    chunks.append({
        "id": "street_cleaning_holidays",
        "text": (
            "Boston street cleaning on holidays: "
            "On official city holidays, daytime street cleaning is suspended — you do not need to move "
            "your car for daytime sweeping on those days. "
            "However, overnight street cleaning (12:01 AM to 7:00 AM) is NOT suspended on holidays "
            "and continues as normal. "
            "Always check the posted street sign, as it is the authoritative source. "
            "Boston city holidays include New Year's Day, Martin Luther King Jr. Day, Presidents Day, "
            "Patriots Day, Memorial Day, Juneteenth, Independence Day, Labor Day, Columbus Day, "
            "Veterans Day, Thanksgiving, and Christmas."
        ),
        "metadata": {
            "domain": "street_cleaning",
            "street_name": "general",
            "neighborhood": "all",
            "source": source["url"],
            "source_name": "Boston Street Cleaning Rules",
        },
    })

    # Dedicated neighborhood seasons chunk — North End, South End, Beacon Hill
    chunks.append({
        "id": "street_cleaning_neighborhood_seasons",
        "text": (
            "Boston street cleaning season by neighborhood: "
            "Most Boston neighborhoods run the Daytime Street Cleaning Program from April 1 to November 30. "
            "However, three neighborhoods have an extended season running from March 1 to December 31: "
            "the North End, the South End, and Beacon Hill. "
            "This means residents in the North End, South End, and Beacon Hill must comply with "
            "street cleaning rules one month earlier in spring (March 1 instead of April 1) "
            "and one month later in fall (December 31 instead of November 30). "
            "Charlestown also has a special rule — daytime street cleaning tickets in Charlestown "
            "cost $90 instead of the standard $40. "
            "All other neighborhoods follow the standard April 1 to November 30 seasonal schedule."
        ),
        "metadata": {
            "domain": "street_cleaning",
            "street_name": "general",
            "neighborhood": "all",
            "source": source["url"],
            "source_name": "Boston Street Cleaning Rules",
        },
    })

    chunks_path.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    print(f"[chunking/street_cleaning] {len(chunks)} chunks → {chunks_path}")
    return chunks


if __name__ == "__main__":
    chunk_street_cleaning()