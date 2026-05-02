"""
Tests for the ingestion layer.
Verifies that scrapers and parsers produce valid output.
"""

import json
import pytest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config.settings import DATA_PROCESSED, SOURCES


class TestViolationsIngestion:
    def test_processed_file_exists(self):
        path = DATA_PROCESSED / SOURCES["violation_fines"]["processed_file"]
        assert path.exists(), "Run: python ingestion/run_all.py first"

    def test_violations_not_empty(self):
        path = DATA_PROCESSED / SOURCES["violation_fines"]["processed_file"]
        if not path.exists():
            pytest.skip("Processed file not found — run ingestion first")
        data = json.loads(path.read_text())
        assert len(data["violations"]) > 0, "No violations found"

    def test_violations_have_required_fields(self):
        path = DATA_PROCESSED / SOURCES["violation_fines"]["processed_file"]
        if not path.exists():
            pytest.skip("Processed file not found")
        data = json.loads(path.read_text())
        for v in data["violations"]:
            assert "violation" in v
            assert "fine_amount" in v
            assert "domain" in v

    def test_violations_minimum_count(self):
        path = DATA_PROCESSED / SOURCES["violation_fines"]["processed_file"]
        if not path.exists():
            pytest.skip("Processed file not found")
        data = json.loads(path.read_text())
        assert len(data["violations"]) >= 20, "Expected at least 20 violations"


class TestPermitsIngestion:
    def test_processed_file_exists(self):
        path = DATA_PROCESSED / SOURCES["permit_eligibility"]["processed_file"]
        assert path.exists(), "Run: python ingestion/run_all.py first"

    def test_sections_not_empty(self):
        path = DATA_PROCESSED / SOURCES["permit_eligibility"]["processed_file"]
        if not path.exists():
            pytest.skip("Processed file not found")
        data = json.loads(path.read_text())
        assert len(data["sections"]) > 0

    def test_sections_have_content(self):
        path = DATA_PROCESSED / SOURCES["permit_eligibility"]["processed_file"]
        if not path.exists():
            pytest.skip("Processed file not found")
        data = json.loads(path.read_text())
        for section in data["sections"]:
            assert len(section.get("content", "")) > 50


class TestStreetCleaningIngestion:
    def test_processed_file_exists(self):
        path = DATA_PROCESSED / SOURCES["street_cleaning"]["processed_file"]
        assert path.exists(), "Run: python ingestion/run_all.py first"

    def test_streets_not_empty(self):
        path = DATA_PROCESSED / SOURCES["street_cleaning"]["processed_file"]
        if not path.exists():
            pytest.skip("Processed file not found")
        data = json.loads(path.read_text())
        assert data["total_streets"] > 0

    def test_street_segments_have_days(self):
        path = DATA_PROCESSED / SOURCES["street_cleaning"]["processed_file"]
        if not path.exists():
            pytest.skip("Processed file not found")
        data = json.loads(path.read_text())
        # Check first 10 streets have at least one active day
        for street in data["streets"][:10]:
            for seg in street["segments"]:
                days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
                has_day = any(seg.get(d) for d in days)
                assert has_day, f"No active days for {street['street_name']}"


class TestTrafficRulesIngestion:
    def test_processed_file_exists(self):
        path = DATA_PROCESSED / SOURCES["traffic_rules"]["processed_file"]
        assert path.exists(), "Run: python ingestion/run_all.py first"

    def test_sections_not_empty(self):
        path = DATA_PROCESSED / SOURCES["traffic_rules"]["processed_file"]
        if not path.exists():
            pytest.skip("Processed file not found")
        data = json.loads(path.read_text())
        assert data["total_sections"] > 0

    def test_sections_minimum_count(self):
        path = DATA_PROCESSED / SOURCES["traffic_rules"]["processed_file"]
        if not path.exists():
            pytest.skip("Processed file not found")
        data = json.loads(path.read_text())
        assert data["total_sections"] >= 10, "Expected at least 10 sections from PDF"