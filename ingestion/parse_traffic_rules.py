"""
Downloads and parses the BTD Traffic Rules and Regulations PDF.
Uses section-aware extraction — splits on Article/Section headers
rather than arbitrary token boundaries.

Outputs: data/raw/traffic_rules.pdf
         data/processed/traffic_rules.json
"""

import json
import re
import requests
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import SOURCES, DATA_RAW, DATA_PROCESSED


def download_pdf(url: str, path: Path) -> None:
    print(f"[traffic_rules] Downloading PDF...")
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    path.write_bytes(response.content)
    print(f"[traffic_rules] PDF saved → {path} ({len(response.content) / 1024:.1f} KB)")


def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()
        return full_text
    except ImportError:
        raise ImportError("PyMuPDF not installed. Run: pip install pymupdf")


def parse_sections(text: str) -> list[dict]:
    """
    Split the traffic rules text on Article and Section headers.
    Each resulting chunk preserves its Article + Section context.
    """
    sections = []

    # Patterns for Article and Section headers in BTD PDF
    article_pattern = re.compile(r"^(ARTICLE\s+[IVXLCDM]+\..*?)$", re.MULTILINE | re.IGNORECASE)
    section_pattern = re.compile(r"^(Section\s+\d+[\.\d]*\.?\s+.{5,80})$", re.MULTILINE)

    # Split text into article blocks first
    article_splits = list(article_pattern.finditer(text))

    if not article_splits:
        # Fallback: treat entire doc as one section if no articles found
        sections.append({
            "article": "General",
            "section": "Full Document",
            "content": text.strip(),
        })
        return sections

    for i, match in enumerate(article_splits):
        article_title = match.group(1).strip()
        start = match.start()
        end = article_splits[i + 1].start() if i + 1 < len(article_splits) else len(text)
        article_text = text[start:end]

        # Further split article by Section headers
        section_splits = list(section_pattern.finditer(article_text))

        if not section_splits:
            sections.append({
                "article": article_title,
                "section": article_title,
                "content": article_text.strip(),
            })
            continue

        for j, sec_match in enumerate(section_splits):
            section_title = sec_match.group(1).strip()
            sec_start = sec_match.start()
            sec_end = section_splits[j + 1].start() if j + 1 < len(section_splits) else len(article_text)
            section_content = article_text[sec_start:sec_end].strip()

            if len(section_content) > 50:  # skip empty sections
                sections.append({
                    "article": article_title,
                    "section": section_title,
                    "content": section_content,
                })

    return sections


def parse_traffic_rules() -> None:
    source = SOURCES["traffic_rules"]
    raw_path = DATA_RAW / source["raw_file"]
    processed_path = DATA_PROCESSED / source["processed_file"]

    # Download PDF if not already present
    if not raw_path.exists():
        download_pdf(source["url"], raw_path)
    else:
        print(f"[traffic_rules] PDF already exists at {raw_path}, skipping download")

    # Extract text
    print(f"[traffic_rules] Extracting text from PDF...")
    text = extract_text_from_pdf(raw_path)
    print(f"[traffic_rules] Extracted {len(text):,} characters")

    # Parse into sections
    sections = parse_sections(text)
    print(f"[traffic_rules] Parsed {len(sections)} sections")

    output = {
        "sections": [
            {
                **sec,
                "domain": source["domain"],
                "source": source["url"],
            }
            for sec in sections
        ],
        "total_sections": len(sections),
        "source": source["url"],
        "domain": source["domain"],
    }

    processed_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"[traffic_rules] Processed → {processed_path}")


if __name__ == "__main__":
    parse_traffic_rules()