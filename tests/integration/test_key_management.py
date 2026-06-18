"""Integration tests for key management tools
(altr_mcp/tools/key_management.py).

Tests all 9 key management tools (4 tweak + 5 key) using pytest-httpx
to mock HTTP responses. Verifies URL construction, HTTP methods, and
the {success, data, error} response shape.
"""
import pytest
from fastmcp import FastMCP
from pytest_httpx import HTTPXMock

from altr_mcp.tools.key_management import register
from tests.integration.conftest import get_tool

TWEAK_NAME = "my-tweak"
TWEAK_SEQ = "seq-001"
KEY_NS = "fpe"
KEY_NAME = "my-key"
KEY_SEQ = "seq-002"


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


# ── list_tweaks ──────────────────────────────────────────────────────────────

async def test_list_tweaks_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"tweaks": [], "contiguous_id": None})
    fn = await get_tool(mcp, "list_tweaks")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "tweaks" in str(httpx_mock.get_request().url)


async def test_list_tweaks_with_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"tweaks": []})
    fn = await get_tool(mcp, "list_tweaks")
    result = await fn(limit=10, contain="ssn", status="active")
    assert result["success"] is True
    url_str = str(httpx_mock.get_request().url)
    assert "limit=10" in url_str
    assert "contain=ssn" in url_str
    assert "status=active" in url_str


async def test_list_tweaks_with_cursor(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"tweaks": []})
    fn = await get_tool(mcp, "list_tweaks")
    result = await fn(contiguous_id="cursor-token")
    assert result["success"] is True
    assert "contiguous_id=cursor-token" in str(httpx_mock.get_request().url)


# ── get_tweak ────────────────────────────────────────────────────────────────

async def test_get_tweak_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={
        "name": TWEAK_NAME, "sequence": TWEAK_SEQ, "status": "active"
    })
    fn = await get_tool(mcp, "get_tweak")
    result = await fn(name=TWEAK_NAME)
    assert result["success"] is True
    assert TWEAK_NAME in str(httpx_mock.get_request().url)


async def test_get_tweak_with_sequence(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"name": TWEAK_NAME})
    fn = await get_tool(mcp, "get_tweak")
    result = await fn(name=TWEAK_NAME, sequence=TWEAK_SEQ)
    assert result["success"] is True
    assert f"sequence={TWEAK_SEQ}" in str(httpx_mock.get_request().url)


# ── create_tweak ─────────────────────────────────────────────────────────────

async def test_create_tweak(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"name": TWEAK_NAME, "sequence": TWEAK_SEQ})
    fn = await get_tool(mcp, "create_tweak")
    result = await fn(name=TWEAK_NAME)
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert request.method == "POST"
    assert "tweaks" in str(request.url)


# ── deactivate_tweak ─────────────────────────────────────────────────────────

async def test_deactivate_tweak(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"status": "deactivated"})
    fn = await get_tool(mcp, "deactivate_tweak")
    result = await fn(name=TWEAK_NAME, sequence=TWEAK_SEQ)
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert request.method == "PATCH"
    url_str = str(request.url)
    assert TWEAK_NAME in url_str
    assert TWEAK_SEQ in url_str
    assert "deactivate" in url_str


# ── list_keys ────────────────────────────────────────────────────────────────

async def test_list_keys_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"keys": [], "contiguous_id": None})
    fn = await get_tool(mcp, "list_keys")
    result = await fn(namespace=KEY_NS)
    assert result["success"] is True
    assert KEY_NS in str(httpx_mock.get_request().url)


async def test_list_keys_with_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"keys": []})
    fn = await get_tool(mcp, "list_keys")
    result = await fn(namespace=KEY_NS, limit=5, contain="ssn",
                      status="deactivated")
    assert result["success"] is True
    url_str = str(httpx_mock.get_request().url)
    assert "limit=5" in url_str
    assert "contain=ssn" in url_str
    assert "status=deactivated" in url_str


# ── get_key ──────────────────────────────────────────────────────────────────

async def test_get_key_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={
        "namespace": KEY_NS, "name": KEY_NAME, "status": "active"
    })
    fn = await get_tool(mcp, "get_key")
    result = await fn(namespace=KEY_NS, name=KEY_NAME)
    assert result["success"] is True
    url_str = str(httpx_mock.get_request().url)
    assert KEY_NS in url_str
    assert KEY_NAME in url_str


async def test_get_key_with_sequence(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"name": KEY_NAME})
    fn = await get_tool(mcp, "get_key")
    result = await fn(namespace=KEY_NS, name=KEY_NAME, sequence=KEY_SEQ)
    assert result["success"] is True
    assert f"sequence={KEY_SEQ}" in str(httpx_mock.get_request().url)


# ── create_key ───────────────────────────────────────────────────────────────

async def test_create_key(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={
        "namespace": KEY_NS, "name": KEY_NAME, "sequence": KEY_SEQ
    })
    fn = await get_tool(mcp, "create_key")
    result = await fn(namespace=KEY_NS, name=KEY_NAME)
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert request.method == "POST"
    assert "keys" in str(request.url)


# ── deactivate_key ───────────────────────────────────────────────────────────

async def test_deactivate_key(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"status": "deactivated"})
    fn = await get_tool(mcp, "deactivate_key")
    result = await fn(namespace=KEY_NS, name=KEY_NAME, sequence=KEY_SEQ)
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert request.method == "PATCH"
    url_str = str(request.url)
    assert KEY_NS in url_str
    assert KEY_NAME in url_str
    assert KEY_SEQ in url_str
    assert "deactivate" in url_str


# ── rotate_key ───────────────────────────────────────────────────────────────

async def test_rotate_key(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"status": "active", "rotated": True})
    fn = await get_tool(mcp, "rotate_key")
    result = await fn(namespace=KEY_NS, name=KEY_NAME, sequence=KEY_SEQ)
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert request.method == "PATCH"
    url_str = str(request.url)
    assert KEY_NS in url_str
    assert KEY_NAME in url_str
    assert KEY_SEQ in url_str
    assert "rotate" in url_str


# ── error path ───────────────────────────────────────────────────────────────

async def test_key_management_error_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=404)
    fn = await get_tool(mcp, "get_tweak")
    result = await fn(name="nonexistent")
    assert result["success"] is True
    assert result["data"].get("success") is False
