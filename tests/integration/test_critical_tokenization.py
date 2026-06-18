"""Integration tests for critical tokenization tools
(altr_mcp/tools/critical_tokenization.py).

Tests all 4 critical tokenization tools using pytest-httpx to mock HTTP
responses. Mirrors the vault tokenization test structure since both APIs
share the same field000/fieldNNN encoding and tool shape.
"""
import pytest
from fastmcp import FastMCP
from pytest_httpx import HTTPXMock

from altr_mcp.tools.critical_tokenization import register
from tests.integration.conftest import get_tool


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


def _ok(fields: dict) -> dict:
    """Wrap field dict in the API's {"data": {...}, "success": True} envelope."""
    return {"data": fields, "success": True}


# ── critical_tokenize ────────────────────────────────────────────────────────

async def test_critical_tokenize_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "token_abc123"}))
    fn = await get_tool(mcp, "critical_tokenize")
    result = await fn(values={"ssn": "123-45-6789"})
    assert result["success"] is True
    assert result["error"] is None
    assert result["data"] == {"ssn": "token_abc123"}


async def test_critical_tokenize_multiple_values(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({
        "field000": "token_t1",
        "field001": "token_t2",
    }))
    fn = await get_tool(mcp, "critical_tokenize")
    result = await fn(values={"ssn": "123-45-6789", "email": "a@b.com"})
    assert result["data"] == {"ssn": "token_t1", "email": "token_t2"}


async def test_critical_tokenize_deterministic_header(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "token_det1"}))
    fn = await get_tool(mcp, "critical_tokenize")
    await fn(values={"ssn": "123-45-6789"}, deterministic=True)
    assert httpx_mock.get_request().headers.get("x-altr-determinism") == "true"


async def test_critical_tokenize_non_deterministic_default(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "token_rnd1"}))
    fn = await get_tool(mcp, "critical_tokenize")
    await fn(values={"ssn": "123-45-6789"})
    assert httpx_mock.get_request().headers.get("x-altr-determinism") == "false"


async def test_critical_tokenize_uses_post(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "token_t1"}))
    fn = await get_tool(mcp, "critical_tokenize")
    await fn(values={"k": "v"})
    assert httpx_mock.get_request().method == "POST"


# ── critical_detokenize ──────────────────────────────────────────────────────

async def test_critical_detokenize_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "123-45-6789"}))
    fn = await get_tool(mcp, "critical_detokenize")
    result = await fn(tokens={"ssn": "token_abc123"})
    assert result["success"] is True
    assert result["data"] == {"ssn": "123-45-6789"}


async def test_critical_detokenize_uses_put(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "plaintext"}))
    fn = await get_tool(mcp, "critical_detokenize")
    await fn(tokens={"k": "token_t"})
    assert httpx_mock.get_request().method == "PUT"


# ── critical_partial_detokenize ──────────────────────────────────────────────

async def test_critical_partial_detokenize_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({
        "field000": "123-45-6789",
        "field001": "already-plain",
    }))
    fn = await get_tool(mcp, "critical_partial_detokenize")
    result = await fn(values={"ssn": "token_t1", "name": "already-plain"})
    assert result["success"] is True
    assert result["data"]["ssn"] == "123-45-6789"
    assert result["data"]["name"] == "already-plain"


async def test_critical_partial_detokenize_url_contains_partial(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "plain"}))
    fn = await get_tool(mcp, "critical_partial_detokenize")
    await fn(values={"k": "token_t"})
    assert "partial" in str(httpx_mock.get_request().url)


# ── critical_delete_tokens ───────────────────────────────────────────────────

async def test_critical_delete_tokens_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "deleted"}))
    fn = await get_tool(mcp, "critical_delete_tokens")
    result = await fn(tokens={"ssn": "token_t1"})
    assert result["success"] is True
    assert result["data"] == {"ssn": "deleted"}


async def test_critical_delete_tokens_url_contains_delete(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json=_ok({"field000": "deleted"}))
    fn = await get_tool(mcp, "critical_delete_tokens")
    await fn(tokens={"k": "token_t"})
    assert "delete" in str(httpx_mock.get_request().url)


# ── error path ───────────────────────────────────────────────────────────────

async def test_critical_tokenize_error_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=400)
    fn = await get_tool(mcp, "critical_tokenize")
    result = await fn(values={"ssn": "123-45-6789"})
    assert result["success"] is True
    assert result["data"].get("success") is False


async def test_critical_invalid_json_response(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(
        content=b"<html>Bad Gateway</html>",
        headers={"Content-Type": "text/html"},
    )
    fn = await get_tool(mcp, "critical_tokenize")
    result = await fn(values={"ssn": "123-45-6789"})
    assert result["success"] is True
    assert "raw" in result["data"]


async def test_critical_5xx_retry_exhaustion(
        httpx_mock: HTTPXMock, retry_env, mcp):
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    fn = await get_tool(mcp, "critical_tokenize")
    result = await fn(values={"ssn": "123-45-6789"})
    assert result["success"] is True
    assert result["data"]["success"] is False
    assert "Retry exhausted" in result["data"]["message"]
