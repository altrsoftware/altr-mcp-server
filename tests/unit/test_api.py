"""Canonical tests for utils/api.py response-shape handling.

All MCP tools wrap a single helper, ``api.request``, which is the only place
that turns an HTTP response into the ``{success, data/raw, ...}`` dict every
tool returns. These tests pin that shared behavior in ONE place so the
per-tool integration suites don't each re-test it. Retry/backoff mechanics
live in test_retry.py; this file covers body decoding and error shaping.
"""
import pytest
from pytest_httpx import HTTPXMock

from altr_mcp.utils.api import request


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("ORG_ID", "test-org")
    monkeypatch.setenv("MAPI_KEY", "test-key")
    monkeypatch.setenv("MAPI_SECRET", "test-secret")
    monkeypatch.setenv("DISABLE_RETRY", "true")


async def test_dict_json_returned_as_is(httpx_mock: HTTPXMock, env):
    """A JSON object body is returned verbatim."""
    httpx_mock.add_response(json={"success": True, "data": {"k": "v"}})
    result = await request("GET", "https://api.example.com/x", None, {})
    assert result == {"success": True, "data": {"k": "v"}}


async def test_non_dict_json_is_wrapped(httpx_mock: HTTPXMock, env):
    """A JSON array (non-dict) body is wrapped under a data key."""
    httpx_mock.add_response(json=[{"id": 1}, {"id": 2}])
    result = await request("GET", "https://api.example.com/x", None, {})
    assert result["success"] is True
    assert result["data"] == [{"id": 1}, {"id": 2}]


async def test_invalid_json_falls_back_to_raw_text(httpx_mock: HTTPXMock, env):
    """A non-JSON body (e.g. an HTML error page) surfaces as raw text."""
    httpx_mock.add_response(
        content=b"<html>Bad Gateway</html>",
        headers={"Content-Type": "text/html"},
    )
    result = await request("GET", "https://api.example.com/x", None, {})
    assert result["success"] is True
    assert result["raw"] == "<html>Bad Gateway</html>"


async def test_empty_body_returns_raw_none(httpx_mock: HTTPXMock, env):
    """A 204/empty body returns success with raw=None."""
    httpx_mock.add_response(status_code=204, content=b"")
    result = await request("DELETE", "https://api.example.com/x", None, {})
    assert result["success"] is True
    assert result["raw"] is None


async def test_4xx_returns_success_false_dict(httpx_mock: HTTPXMock, env):
    """A non-retryable 4xx returns a {success: False} dict (never raises)."""
    httpx_mock.add_response(status_code=404)
    result = await request("GET", "https://api.example.com/x", None, {})
    assert result["success"] is False
    assert result["status_code"] == 404
