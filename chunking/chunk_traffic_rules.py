"""
Chunks traffic rules PDF sections.
Strategy: section-aware — each Article/Section becomes a chunk.
Filters out hollow header-only chunks (under 150 chars) which are
artifacts of the PDF parser splitting headers from body text.
"""

import json
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import SOURCES, DATA_PROCESSED, DATA_CHUNKS

MAX_CHUNK_CHARS = 2000
MIN_CHUNK_CHARS = 150  # filters out hollow header-only chunks


def split_long_section(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split oversized sections at paragraph boundaries."""
    if len(text) <= max_chars:
        return [text]

    parts = []
    paragraphs = text.split("\n\n")
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_chars:
            current = current + "\n\n" + para if current else para
        else:
            if current:
                parts.append(current.strip())
            current = para

    if current:
        parts.append(current.strip())

    return parts if parts else [text[:max_chars]]


def chunk_traffic_rules() -> list[dict]:
    source = SOURCES["traffic_rules"]
    processed_path = DATA_PROCESSED / source["processed_file"]
    chunks_path = DATA_CHUNKS / source["chunks_file"]

    data = json.loads(processed_path.read_text(encoding="utf-8"))
    chunks = []
    chunk_idx = 0
    skipped = 0

    for section in data["sections"]:
        article = section.get("article", "")
        section_title = section.get("section", "")
        content = section.get("content", "").strip()

        if not content or len(content) < MIN_CHUNK_CHARS:
            skipped += 1
            continue

        header = f"[{article}] {section_title}\n\n"
        full_text = header + content

        sub_chunks = split_long_section(full_text)

        for j, sub_text in enumerate(sub_chunks):
            # Skip sub-chunks that are too short after splitting
            if len(sub_text.strip()) < MIN_CHUNK_CHARS:
                skipped += 1
                continue

            chunk_id = f"traffic_{chunk_idx:04d}"
            if len(sub_chunks) > 1:
                chunk_id += f"_{j}"

            chunks.append({
                "id": chunk_id,
                "text": sub_text,
                "metadata": {
                    "domain": "regulations",
                    "article": article,
                    "section": section_title,
                    "source": source["url"],
                    "source_name": "City of Boston Traffic Rules and Regulations (March 2025)",
                },
            })
            chunk_idx += 1

    chunks_path.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    print(f"[chunking/traffic_rules] {len(chunks)} chunks → {chunks_path}")
    print(f"[chunking/traffic_rules] Skipped {skipped} hollow/short chunks")
    return chunks


if __name__ == "__main__":
    chunk_traffic_rules()