"""Tests for utility functions."""

from __future__ import annotations

import pytest

from protol._utils import (
    calculate_size_bytes,
    hash_data,
    truncate,
    validate_agent_id,
    validate_api_key,
)


class TestHashData:
    def test_hash_string(self):
        h = hash_data("hello world")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex digest

    def test_hash_bytes(self):
        h = hash_data(b"hello world")
        assert isinstance(h, str)
        assert len(h) == 64

    def test_hash_dict(self):
        h = hash_data({"key": "value", "number": 42})
        assert isinstance(h, str)
        assert len(h) == 64

    def test_hash_list(self):
        h = hash_data([1, 2, 3])
        assert isinstance(h, str)
        assert len(h) == 64

    def test_hash_none(self):
        h = hash_data(None)
        assert isinstance(h, str)
        assert len(h) == 64

    def test_hash_deterministic(self):
        h1 = hash_data({"a": 1, "b": 2})
        h2 = hash_data({"b": 2, "a": 1})
        assert h1 == h2  # Canonical JSON (sorted keys)

    def test_hash_different_data_differs(self):
        h1 = hash_data("hello")
        h2 = hash_data("world")
        assert h1 != h2

    def test_hash_pydantic_model(self):
        from protol.models import ActionRating

        rating = ActionRating(rating=5, feedback="great")
        h = hash_data(rating)
        assert isinstance(h, str)
        assert len(h) == 64


class TestValidateAgentId:
    def test_valid_id(self):
        assert validate_agent_id("agt_abc123") is True
        assert validate_agent_id("agt_AbCdEf1234") is True
        assert validate_agent_id("agt_123456") is True

    def test_invalid_prefix(self):
        assert validate_agent_id("agent_abc123") is False
        assert validate_agent_id("abc123") is False

    def test_too_short(self):
        assert validate_agent_id("agt_abc") is False  # Only 3 chars after prefix

    def test_too_long(self):
        assert validate_agent_id("agt_abcdefghijklm") is False  # 13 chars after prefix

    def test_invalid_chars(self):
        assert validate_agent_id("agt_abc-123") is False
        assert validate_agent_id("agt_abc_123") is False


class TestValidateApiKey:
    def test_valid_key(self):
        assert validate_api_key("aos_sk_12345678901234567890") is True
        assert validate_api_key("aos_sk_abcdefghijklmnopqrstuvwxyz") is True

    def test_invalid_prefix(self):
        assert validate_api_key("sk_12345678901234567890") is False
        assert validate_api_key("aos_12345678901234567890") is False

    def test_too_short(self):
        assert validate_api_key("aos_sk_short") is False  # Less than 20 chars after prefix


class TestCalculateSizeBytes:
    def test_string(self):
        size = calculate_size_bytes("hello")
        assert size == 5

    def test_bytes(self):
        size = calculate_size_bytes(b"hello")
        assert size == 5

    def test_dict(self):
        size = calculate_size_bytes({"key": "value"})
        assert size > 0

    def test_none(self):
        size = calculate_size_bytes(None)
        assert size == 0


class TestTruncate:
    def test_no_truncation(self):
        assert truncate("hello", 10) == "hello"

    def test_truncation(self):
        result = truncate("hello world", 8)
        assert result == "hello..."
        assert len(result) == 8

    def test_exact_length(self):
        assert truncate("hello", 5) == "hello"

    def test_very_short_max(self):
        assert truncate("hello", 3) == "hel"
