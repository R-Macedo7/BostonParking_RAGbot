"""
Metadata pre-filter and query router.
Detects query intent to apply domain filters before retrieval,
reducing noise and improving precision.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class QueryIntent:
    domain_filter: Optional[str]   # chromadb 'where' filter if applicable
    is_multi_part: bool             # should query decomposer run?
    detected_street: Optional[str]  # street name if found in query
    query_type: str                 # "violation" | "permit" | "street_cleaning" | "regulation" | "general"


# Keywords that strongly signal a domain
VIOLATION_KEYWORDS = {
    "ticket", "fine", "violation", "citation", "towed", "boot",
    "hydrant", "crosswalk", "sidewalk", "double park", "meter",
    "handicap", "fire lane", "bus stop", "bike lane", "loading zone",
    "penalty", "unpaid", "overdue", "late fee", "appeal",
}

PERMIT_KEYWORDS = {
    "permit", "sticker", "resident", "apply", "application",
    "renew", "renewal", "replace", "rpp",
    "how do i get", "how to get", "eligible", "eligibility",
}

STREET_CLEANING_KEYWORDS = {
    "street cleaning", "street sweeping", "sweeper", "sweep",
    "cleaning schedule", "sweeping schedule", "move my car",
    "when is", "what day", "what time", "no parking sign",
    "cleaning hours", "sweeping hours", "holiday", "holidays",
}

REGULATION_KEYWORDS = {
    "rule", "regulation", "allowed", "prohibited", "legal", "illegal",
    "overnight commercial", "commercial vehicle", "heavy vehicle",
    "angle parking", "one-way", "intersection", "curb", "loading",
    "valet", "snow emergency", "weather emergency", "residential area",
    "ban", "restrict", "restriction",
}


def detect_street_name(query: str) -> Optional[str]:
    """
    Heuristic: look for 'on X St/Ave/Rd/Blvd/Pl/Way/Dr' patterns.
    Returns normalized street name or None.
    """
    pattern = re.compile(
        r'\bon\s+([A-Z][a-zA-Z\s]+(?:St|Ave|Rd|Blvd|Pl|Way|Dr|Ln|Ct|Ter|Circle|Square)\.?)\b',
        re.IGNORECASE
    )
    match = pattern.search(query)
    if match:
        return match.group(1).strip()
    return None


def classify_query(query: str) -> QueryIntent:
    q_lower = query.lower()

    # Score each domain by keyword overlap
    violation_score = sum(1 for kw in VIOLATION_KEYWORDS if kw in q_lower)
    permit_score = sum(1 for kw in PERMIT_KEYWORDS if kw in q_lower)
    cleaning_score = sum(1 for kw in STREET_CLEANING_KEYWORDS if kw in q_lower)
    regulation_score = sum(1 for kw in REGULATION_KEYWORDS if kw in q_lower)

    # Boost regulation score for commercial vehicle + overnight combos
    if "commercial" in q_lower and "overnight" in q_lower:
        regulation_score += 2
    if "commercial" in q_lower and ("residential" in q_lower or "area" in q_lower):
        regulation_score += 2

    scores = {
        "violations": violation_score,
        "permits": permit_score,
        "street_cleaning": cleaning_score,
        "regulations": regulation_score,
    }

    max_score = max(scores.values())
    detected_street = detect_street_name(query)

    # If street name detected + cleaning keywords → force street_cleaning domain
    if detected_street and cleaning_score > 0:
        domain_filter = "street_cleaning"
        query_type = "street_cleaning"
    elif max_score == 0:
        domain_filter = None
        query_type = "general"
    elif max_score <= 1:
        # Ambiguous — don't filter, let full hybrid search run
        domain_filter = None
        query_type = "general"
    else:
        best_domain = max(scores, key=scores.get)
        domain_map = {
            "violations": "violations",
            "permits": "permits",
            "street_cleaning": "street_cleaning",
            "regulations": "regulations",
        }
        domain_filter = domain_map[best_domain]
        query_type = best_domain

    # Multi-part detection: conjunction words + multiple question marks
    multi_part_signals = ["and", "also", "additionally", "as well as", "plus"]
    is_multi_part = (
        sum(1 for sig in multi_part_signals if sig in q_lower) >= 2
        or query.count("?") > 1
        or len(query.split()) > 30
    )

    return QueryIntent(
        domain_filter=domain_filter,
        is_multi_part=is_multi_part,
        detected_street=detected_street,
        query_type=query_type,
    )