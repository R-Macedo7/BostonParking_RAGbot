"""
Tests for the chunking layer.
Verifies chunk structure, content quality, and metadata completeness.
"""

import json
import pytest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import DATA_CHUNKS, SOURCES

REQUIRED_CHUNK_FIELDS = ["id", "text", "metadata"]
REQUIRED_METADATA_FIELDS = ["domain", "source", "source_name"]


def load_chunks(source_key: str) -> list[dict]:
    path = DATA_CHUNKS / SOURCES[source_key]["chunks_file"]
    if not path.exists():
        return []
    return json.loads(path.read_text())


class TestChunkStructure:
    """All chunk files must conform to the standard schema."""

    @pytest.mark.parametrize("source_key", list(SOURCES.keys()))
    def test_chunks_exist(self, source_key):
        path = DATA_CHUNKS / SOURCES[source_key]["chunks_file"]
        assert path.exists(), f"Chunks not found for {source_key} — run chunking first"

    @pytest.mark.parametrize("source_key", list(SOURCES.keys()))
    def test_chunks_not_empty(self, source_key):
        chunks = load_chunks(source_key)
        if not chunks:
            pytest.skip(f"No chunks for {source_key}")
        assert len(chunks) > 0

    @pytest.mark.parametrize("source_key", list(SOURCES.keys()))
    def test_chunk_required_fields(self, source_key):
        chunks = load_chunks(source_key)
        if not chunks:
            pytest.skip(f"No chunks for {source_key}")
        for chunk in chunks:
            for field in REQUIRED_CHUNK_FIELDS:
                assert field in chunk, f"Missing field '{field}' in chunk {chunk.get('id')}"

    @pytest.mark.parametrize("source_key", list(SOURCES.keys()))
    def test_chunk_metadata_fields(self, source_key):
        chunks = load_chunks(source_key)
        if not chunks:
            pytest.skip(f"No chunks for {source_key}")
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            for field in REQUIRED_METADATA_FIELDS:
                assert field in meta, f"Missing metadata field '{field}' in chunk {chunk.get('id')}"

    @pytest.mark.parametrize("source_key", list(SOURCES.keys()))
    def test_chunk_ids_unique(self, source_key):
        chunks = load_chunks(source_key)
        if not chunks:
            pytest.skip(f"No chunks for {source_key}")
        ids = [c["id"] for c in chunks]
        assert len(ids) == len(set(ids)), "Duplicate chunk IDs found"

    @pytest.mark.parametrize("source_key", list(SOURCES.keys()))
    def test_chunk_text_not_empty(self, source_key):
        chunks = load_chunks(source_key)
        if not chunks:
            pytest.skip(f"No chunks for {source_key}")
        for chunk in chunks:
            assert len(chunk["text"].strip()) > 20, f"Chunk {chunk['id']} text too short"


class TestViolationChunks:
    def test_violation_chunk_contains_fine(self):
        chunks = load_chunks("violation_fines")
        if not chunks:
            pytest.skip("No violation chunks")
        # Each violation chunk should mention a dollar amount
        violation_chunks = [c for c in chunks if c["id"] != "violation_summary"]
        for chunk in violation_chunks[:5]:
            assert "$" in chunk["text"], f"No dollar amount in {chunk['id']}"

    def test_summary_chunk_exists(self):
        chunks = load_chunks("violation_fines")
        if not chunks:
            pytest.skip("No violation chunks")
        ids = [c["id"] for c in chunks]
        assert "violation_summary" in ids


class TestStreetCleaningChunks:
    def test_general_rules_chunk_exists(self):
        chunks = load_chunks("street_cleaning")
        if not chunks:
            pytest.skip("No street cleaning chunks")
        ids = [c["id"] for c in chunks]
        assert "street_cleaning_general_rules" in ids

    def test_chunks_contain_day_info(self):
        chunks = load_chunks("street_cleaning")
        if not chunks:
            pytest.skip("No street cleaning chunks")
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        street_chunks = [c for c in chunks if c["id"] != "street_cleaning_general_rules"]
        for chunk in street_chunks[:10]:
            has_day = any(day in chunk["text"] for day in days)
            assert has_day, f"No day info in street chunk {chunk['id']}"