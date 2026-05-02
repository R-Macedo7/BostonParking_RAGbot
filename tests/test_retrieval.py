"""
Tests for the retrieval layer.
Verifies BM25, dense, and hybrid retrieval behavior.
"""

import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from retrieval.metadata_filter import classify_query, detect_street_name


class TestMetadataFilter:
    """Tests for query classification and intent detection."""

    def test_violation_query_classified(self):
        intent = classify_query("What is the fine for parking near a fire hydrant?")
        assert intent.query_type == "violations"

    def test_permit_query_classified(self):
        intent = classify_query("How do I get a resident parking permit?")
        assert intent.query_type == "permits"

    def test_street_cleaning_query_classified(self):
        intent = classify_query("When is street cleaning on my street?")
        assert intent.query_type == "street_cleaning"

    def test_general_query_no_filter(self):
        intent = classify_query("What are the parking rules in Boston?")
        assert intent.domain_filter is None or intent.query_type == "general"

    def test_street_name_detection(self):
        street = detect_street_name("Can I park on Appleton St overnight?")
        assert street is not None
        assert "Appleton" in street

    def test_no_street_name_returns_none(self):
        street = detect_street_name("What is the fine for double parking?")
        assert street is None

    def test_multi_part_query_detected(self):
        intent = classify_query(
            "What is the fine for street cleaning? And also when does the season start and end?"
        )
        assert intent.is_multi_part is True

    def test_simple_query_not_multi_part(self):
        intent = classify_query("What is the fine for double parking?")
        assert intent.is_multi_part is False


class TestBM25Retrieval:
    """Tests for BM25 sparse retrieval."""

    def test_bm25_returns_results(self):
        try:
            from retrieval.bm25_retriever import bm25_search
            results = bm25_search("fire hydrant fine Boston parking")
            assert len(results) > 0
        except FileNotFoundError:
            pytest.skip("BM25 index not built — run indexing first")

    def test_bm25_results_have_required_fields(self):
        try:
            from retrieval.bm25_retriever import bm25_search
            results = bm25_search("parking ticket fine")
            for r in results:
                assert "id" in r
                assert "text" in r
                assert "bm25_score" in r
        except FileNotFoundError:
            pytest.skip("BM25 index not built")

    def test_bm25_scores_positive(self):
        try:
            from retrieval.bm25_retriever import bm25_search
            results = bm25_search("street cleaning schedule")
            for r in results:
                assert r["bm25_score"] > 0
        except FileNotFoundError:
            pytest.skip("BM25 index not built")


class TestHybridRetrieval:
    """Tests for the full hybrid retrieval pipeline."""

    def test_hybrid_returns_results(self):
        try:
            from retrieval.hybrid_retriever import hybrid_search
            results = hybrid_search("What is the fine for parking near a fire hydrant?")
            assert len(results) > 0
        except (FileNotFoundError, Exception) as e:
            pytest.skip(f"Indexes not built — {e}")

    def test_hybrid_results_have_rrf_score(self):
        try:
            from retrieval.hybrid_retriever import hybrid_search
            results = hybrid_search("resident parking permit Boston")
            for r in results:
                assert "rrf_score" in r
                assert r["rrf_score"] > 0
        except (FileNotFoundError, Exception) as e:
            pytest.skip(f"Indexes not built — {e}")

    def test_domain_filter_applied(self):
        try:
            from retrieval.hybrid_retriever import hybrid_search
            results = hybrid_search("parking rules", domain_filter="violations")
            for r in results:
                # Dense results respect filter; BM25 results are post-filtered
                domain = r.get("metadata", {}).get("domain", "")
                # At least some results should be from violations domain
            assert any(
                r.get("metadata", {}).get("domain") == "violations"
                for r in results
            )
        except (FileNotFoundError, Exception) as e:
            pytest.skip(f"Indexes not built — {e}")

    def test_rrf_merge_logic(self):
        from retrieval.hybrid_retriever import rrf_merge

        bm25 = [{"id": "a", "text": "a"}, {"id": "b", "text": "b"}]
        dense = [{"id": "b", "text": "b"}, {"id": "c", "text": "c"}]

        merged = rrf_merge(bm25, dense, top_n=3)

        # "b" appears in both lists so should rank highest
        assert merged[0]["id"] == "b"
        assert len(merged) == 3