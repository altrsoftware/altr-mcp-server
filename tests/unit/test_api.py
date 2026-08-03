"""Canonical tests for utils/api.py response-shape handling.

All MCP tools wrap a single helper, ``api.request``, which is the only place
that turns an HTTP response into the ``{success, data/raw, ...}`` dict every
tool returns. These tests pin that shared behavior in ONE place so the
per-tool integration suites don't each re-test it. Retry/backoff mechanics
live in test_retry.py; this file covers body decoding and error shaping.
"""
import httpx
import pytest
import tenacity
from pytest_httpx import HTTPXMock

from altr_mcp.utils.api import request


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("ORG_ID", "test-org")
    monkeypatch.setenv("MAPI_KEY", "test-key")
    monkeypatch.setenv("MAPI_SECRET", "test-secret")
    monkeypatch.setenv("DISABLE_RETRY", "true")


@pytest.fixture
def retry_env(env, monkeypatch):
    """env, but with retry enabled and sleeping patched out."""
    monkeypatch.setenv("DISABLE_RETRY", "false")
    monkeypatch.setenv("MAX_RETRIES", "2")
    monkeypatch.setattr(tenacity.nap, "sleep", lambda s: None)


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


async def test_transport_error_is_shaped_not_raised(
        httpx_mock: HTTPXMock, env):
    """A transport failure returns {success: False} rather than propagating.

    Covers the generic `except Exception` arm: httpx raises ConnectError
    before any response exists, so the HTTPStatusError handling above it
    never sees it. Tools rely on request() never raising.
    """
    httpx_mock.add_exception(httpx.ConnectError("name resolution failed"))
    result = await request("GET", "https://api.example.com/x", None, {})
    assert result["success"] is False
    assert result["message"].startswith("ConnectError:")


async def test_transport_error_on_the_retry_path(
        httpx_mock: HTTPXMock, retry_env):
    """The retry path has its own generic handler; it shapes errors too."""
    httpx_mock.add_exception(httpx.ConnectError("boom"), is_reusable=True)
    result = await request("GET", "https://api.example.com/x", None, {})
    assert result["success"] is False
    assert "ConnectError" in result["message"]


async def test_non_numeric_retry_after_falls_back_to_backoff(
        httpx_mock: HTTPXMock, retry_env):
    """A Retry-After that is not a number must not break the retry.

    The header is parsed with float(); an HTTP-date value raises ValueError,
    which is swallowed so exponential backoff still applies.
    """
    httpx_mock.add_response(
        status_code=429,
        headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"},
        is_reusable=True,
    )
    result = await request("GET", "https://api.example.com/x", None, {})
    assert result["success"] is False
    assert result["status_code"] == 429
