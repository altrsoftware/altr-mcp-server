"""Integration tests for vault tokenization tools
(altr_mcp/tools/vault_tokenization.py).

Tests all 4 vault tokenization tools using pytest-httpx to mock HTTP responses.
Verifies key translation (field000/field001 ↔ user-supplied key names) and
the {success, data, error} response shape.
"""
import pytest
from fastmcp import FastMCP
from pytest_httpx import HTTPXMock

from altr_mcp.tools.vault_tokenization import register
from tests.integration.conftest import get_tool


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


def _ok(fields: dict) -> dict:
    """Wrap field dict in the API's {"data": {...}, "success": True} envelope."""
    return {"data": fields, "success": True}


# ── vault_tokenize ───────────────────────────────────────────────────────────

async def test_vault_tokenize_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "vaultd_tok1"}))
    fn = await get_tool(mcp, "vault_tokenize")
    result = await fn(values={"ssn": "123-45-6789"})
    assert result["success"] is True
    assert result["error"] is None
    assert result["data"] == {"ssn": "vaultd_tok1"}


async def test_vault_tokenize_multiple_values(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({
        "field000": "vaultd_tok1",
        "field001": "vaultd_tok2",
    }))
    fn = await get_tool(mcp, "vault_tokenize")
    result = await fn(values={"ssn": "123-45-6789", "email": "a@b.com"})
    assert result["success"] is True
    assert result["data"] == {"ssn": "vaultd_tok1", "email": "vaultd_tok2"}


async def test_vault_tokenize_deterministic_header(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "vaultd_det1"}))
    fn = await get_tool(mcp, "vault_tokenize")
    result = await fn(values={"ssn": "123-45-6789"}, deterministic=True)
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert request.headers.get("x-altr-determinism") == "true"


async def test_vault_tokenize_non_deterministic_header(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "vaultd_rnd1"}))
    fn = await get_tool(mcp, "vault_tokenize")
    await fn(values={"ssn": "123-45-6789"}, deterministic=False)
    request = httpx_mock.get_request()
    assert request.headers.get("x-altr-determinism") == "false"


async def test_vault_tokenize_uses_post(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "vaultd_tok1"}))
    fn = await get_tool(mcp, "vault_tokenize")
    await fn(values={"k": "v"})
    assert httpx_mock.get_request().method == "POST"


# ── vault_detokenize ─────────────────────────────────────────────────────────

async def test_vault_detokenize_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "123-45-6789"}))
    fn = await get_tool(mcp, "vault_detokenize")
    result = await fn(tokens={"ssn": "vaultd_tok1"})
    assert result["success"] is True
    assert result["data"] == {"ssn": "123-45-6789"}


async def test_vault_detokenize_multiple(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({
        "field000": "123-45-6789",
        "field001": "alice@example.com",
    }))
    fn = await get_tool(mcp, "vault_detokenize")
    result = await fn(tokens={"ssn": "vaultd_tok1", "email": "vaultd_tok2"})
    assert result["data"] == {
        "ssn": "123-45-6789", "email": "alice@example.com"
    }


async def test_vault_detokenize_uses_put(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "plaintext"}))
    fn = await get_tool(mcp, "vault_detokenize")
    await fn(tokens={"k": "vaultd_tok"})
    assert httpx_mock.get_request().method == "PUT"


# ── vault_partial_detokenize ─────────────────────────────────────────────────

async def test_vault_partial_detokenize_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({
        "field000": "123-45-6789",
        "field001": "already-plain",
    }))
    fn = await get_tool(mcp, "vault_partial_detokenize")
    result = await fn(values={"ssn": "vaultd_tok1", "name": "already-plain"})
    assert result["success"] is True
    assert result["data"]["ssn"] == "123-45-6789"
    assert result["data"]["name"] == "already-plain"


async def test_vault_partial_detokenize_url_contains_partial(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "plain"}))
    fn = await get_tool(mcp, "vault_partial_detokenize")
    await fn(values={"k": "vaultd_tok"})
    assert "partial" in str(httpx_mock.get_request().url)


# ── vault_delete_tokens ──────────────────────────────────────────────────────

async def test_vault_delete_tokens_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "deleted"}))
    fn = await get_tool(mcp, "vault_delete_tokens")
    result = await fn(tokens={"ssn": "vaultd_tok1"})
    assert result["success"] is True
    assert result["data"] == {"ssn": "deleted"}


async def test_vault_delete_tokens_url_contains_delete(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "deleted"}))
    fn = await get_tool(mcp, "vault_delete_tokens")
    await fn(tokens={"k": "vaultd_tok"})
    assert "delete" in str(httpx_mock.get_request().url)


# ── error path ───────────────────────────────────────────────────────────────

async def test_vault_tokenize_error_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=404)
    fn = await get_tool(mcp, "vault_tokenize")
    result = await fn(values={"ssn": "123-45-6789"})
    assert result["success"] is True
    assert result["data"].get("success") is False


async def test_vault_invalid_json_response(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(
        content=b"<html>Bad Gateway</html>",
        headers={"Content-Type": "text/html"},
    )
    fn = await get_tool(mcp, "vault_tokenize")
    result = await fn(values={"ssn": "123-45-6789"})
    assert result["success"] is True
    assert "raw" in result["data"]


async def test_vault_5xx_retry_exhaustion(
        httpx_mock: HTTPXMock, retry_env, mcp):
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    fn = await get_tool(mcp, "vault_tokenize")
    result = await fn(values={"ssn": "123-45-6789"})
    assert result["success"] is True
    assert result["data"]["success"] is False
    assert "Retry exhausted" in result["data"]["message"]
