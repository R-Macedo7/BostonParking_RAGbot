"""
Response formatter — post-processes raw LLM output into a
structured, citation-enriched response before returning to the API.
"""

import re


def extract_sources(chunks: list[dict]) -> list[dict]:
    """Extracts unique sources from retrieved chunks with metadata."""
    seen = set()
    sources = []
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        source_name = meta.get("source_name", "Boston Parking Regulations")
        source_url = meta.get("source", "")
        domain = meta.get("domain", "")

        key = source_name
        if key not in seen:
            seen.add(key)
            sources.append({
                "name": source_name,
                "url": source_url,
                "domain": domain,
            })
    return sources


def clean_answer(answer: str) -> str:
    """
    Light cleanup of raw LLM output:
    - Strip leading/trailing whitespace
    - Remove any accidental markdown headers (##, ###)
    - Normalize multiple blank lines
    """
    # Remove markdown headers
    answer = re.sub(r"^#{1,3}\s+", "", answer, flags=re.MULTILINE)
    # Normalize multiple blank lines to single
    answer = re.sub(r"\n{3,}", "\n\n", answer)
    return answer.strip()


def format_response(
    answer: str,
    chunks: list[dict],
    model_used: str,
    sub_queries: list[str],
    query_type: str,
    usage: dict,
) -> dict:
    """
    Assembles the final structured response dict.
    This is what gets returned to the API and ultimately the user.
    """
    cleaned = clean_answer(answer)
    sources = extract_sources(chunks)
    source_names = [s["name"] for s in sources]

    return {
        "answer": cleaned,
        "model_used": model_used,
        "sources": source_names,
        "source_details": sources,
        "chunks_used": len(chunks),
        "sub_queries": sub_queries,
        "query_type": query_type,
        "usage": usage,
    }


def format_no_results_response(query_type: str, sub_queries: list[str]) -> dict:
    """Standard response when retrieval returns no relevant chunks."""
    return {
        "answer": (
            "I couldn't find relevant information for your question in the "
            "Boston parking regulations database. You can contact the Boston "
            "Parking Clerk directly at 617-635-4410 or visit boston.gov/parking."
        ),
        "model_used": "none",
        "sources": [],
        "source_details": [],
        "chunks_used": 0,
        "sub_queries": sub_queries,
        "query_type": query_type,
        "usage": {},
    }