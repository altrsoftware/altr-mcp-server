"""Unit tests for tokenization tool helpers.

Tests _encode_values and _decode_response from both vault and critical
tokenization tool modules (identical implementations).
"""
import pytest

from altr_mcp.tools.vault_tokenization import (
    _decode_response,
    _encode_values,
)


# ── _encode_values ───────────────────────────────────────────────────────────

def test_encode_values_single():
    encoded, key_map = _encode_values({"ssn": "123-45-6789"})
    assert encoded == {"field000": "123-45-6789"}
    assert key_map == {"field000": "ssn"}


def test_encode_values_multiple():
    encoded, key_map = _encode_values({
        "ssn": "123-45-6789",
        "email": "user@example.com",
        "name": "Alice",
    })
    assert encoded == {
        "field000": "123-45-6789",
        "field001": "user@example.com",
        "field002": "Alice",
    }
    assert key_map == {
        "field000": "ssn",
        "field001": "email",
        "field002": "name",
    }


def test_encode_values_preserves_order():
    keys = [f"k{i}" for i in range(15)]
    values = {k: f"v{i}" for i, k in enumerate(keys)}
    encoded, key_map = _encode_values(values)
    for i, k in enumerate(keys):
        field = f"field{i:03d}"
        assert encoded[field] == f"v{i}"
        assert key_map[field] == k


def test_encode_values_empty():
    encoded, key_map = _encode_values({})
    assert encoded == {}
    assert key_map == {}


# ── _decode_response ─────────────────────────────────────────────────────────

def test_decode_response_single():
    key_map = {"field000": "ssn"}
    result = _decode_response({"field000": "token_abc"}, key_map)
    assert result == {"ssn": "token_abc"}


def test_decode_response_multiple():
    key_map = {"field000": "ssn", "field001": "email"}
    api_resp = {"field000": "token_abc", "field001": "token_xyz"}
    result = _decode_response(api_resp, key_map)
    assert result == {"ssn": "token_abc", "email": "token_xyz"}


def test_decode_response_unknown_keys_pass_through():
    key_map = {"field000": "ssn"}
    api_resp = {"field000": "token_abc", "error_message": "partial failure"}
    result = _decode_response(api_resp, key_map)
    assert result["ssn"] == "token_abc"
    assert result["error_message"] == "partial failure"


def test_encode_then_decode_roundtrip():
    original = {"ssn": "tok1", "email": "tok2", "phone": "tok3"}
    encoded, key_map = _encode_values(original)
    decoded = _decode_response(encoded, key_map)
    assert decoded == original
