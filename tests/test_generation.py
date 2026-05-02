"""
Tests for the generation layer.
Verifies prompt building, model routing, and response formatting.
"""

import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from generation.prompt_builder import build_context_block, build_user_message, build_messages
from generation.response_formatter import clean_answer, extract_sources, format_no_results_response
from config.settings import MODEL_NANO, MODEL_MINI


# Sample chunks for testing without hitting the API
SAMPLE_CHUNKS = [
    {
        "id": "violation_001",
        "text": "Boston parking violation: Parking within 10 feet of a fire hydrant. The fine is $100.",
        "metadata": {
            "domain": "violations",
            "source": "https://boston.gov/parking",
            "source_name": "Boston Parking Ticket Fines and Codes",
        },
    },
    {
        "id": "violation_002",
        "text": "Boston parking violation: Double parking in Zone A. The fine is $55.",
        "metadata": {
            "domain": "violations",
            "source": "https://boston.gov/parking",
            "source_name": "Boston Parking Ticket Fines and Codes",
        },
    },
]


class TestPromptBuilder:
    def test_context_block_contains_source(self):
        context = build_context_block(SAMPLE_CHUNKS)
        assert "Boston Parking Ticket Fines and Codes" in context

    def test_context_block_contains_chunk_text(self):
        context = build_context_block(SAMPLE_CHUNKS)
        assert "fire hydrant" in context

    def test_user_message_contains_query(self):
        message = build_user_message("What is the hydrant fine?", SAMPLE_CHUNKS)
        assert "What is the hydrant fine?" in message

    def test_user_message_contains_context(self):
        message = build_user_message("test query", SAMPLE_CHUNKS)
        assert "fire hydrant" in message

    def test_build_messages_has_system_prompt(self):
        messages = build_messages("test", SAMPLE_CHUNKS)
        assert messages[0]["role"] == "system"
        assert len(messages[0]["content"]) > 50

    def test_build_messages_history_included(self):
        history = [
            {"role": "user", "content": "previous question"},
            {"role": "assistant", "content": "previous answer"},
        ]
        messages = build_messages("new question", SAMPLE_CHUNKS, conversation_history=history)
        roles = [m["role"] for m in messages]
        assert "user" in roles
        assert "assistant" in roles

    def test_build_messages_history_capped(self):
        # History should be capped at 6 messages (3 turns)
        history = [{"role": "user", "content": f"q{i}"} for i in range(20)]
        messages = build_messages("new", SAMPLE_CHUNKS, conversation_history=history)
        # System + up to 6 history + 1 user = max 8
        assert len(messages) <= 8


class TestResponseFormatter:
    def test_clean_answer_strips_whitespace(self):
        answer = "  This is an answer.  "
        assert clean_answer(answer) == "This is an answer."

    def test_clean_answer_removes_headers(self):
        answer = "## Header\nSome content"
        cleaned = clean_answer(answer)
        assert "##" not in cleaned

    def test_clean_answer_normalizes_blank_lines(self):
        answer = "Para 1\n\n\n\nPara 2"
        cleaned = clean_answer(answer)
        assert "\n\n\n" not in cleaned

    def test_extract_sources_unique(self):
        sources = extract_sources(SAMPLE_CHUNKS)
        names = [s["name"] for s in sources]
        assert len(names) == len(set(names))

    def test_extract_sources_correct_name(self):
        sources = extract_sources(SAMPLE_CHUNKS)
        assert any("Boston Parking Ticket" in s["name"] for s in sources)

    def test_no_results_response_structure(self):
        response = format_no_results_response("general", ["test query"])
        assert "answer" in response
        assert "sources" in response
        assert response["chunks_used"] == 0
        assert "617-635-4410" in response["answer"]


class TestModelRouting:
    def test_simple_query_routes_to_nano(self):
        from generation.generator import classify_complexity
        simple_chunks = [SAMPLE_CHUNKS[0]]  # Single domain chunk
        model = classify_complexity("What is the fire hydrant fine?", simple_chunks)
        assert model == MODEL_NANO

    def test_complex_query_routes_to_mini(self):
        from generation.generator import classify_complexity
        multi_domain_chunks = [
            {**SAMPLE_CHUNKS[0], "metadata": {**SAMPLE_CHUNKS[0]["metadata"], "domain": "violations"}},
            {**SAMPLE_CHUNKS[1], "metadata": {**SAMPLE_CHUNKS[1]["metadata"], "domain": "street_cleaning"}},
        ]
        model = classify_complexity(
            "I have a permit but do I still need to move for street cleaning?",
            multi_domain_chunks
        )
        assert model == MODEL_MINI