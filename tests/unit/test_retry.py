"""Tests for HTTP retry logic in utils/api.py."""
import pytest
from pytest_httpx import HTTPXMock

from altr_mcp.utils.api import request


@pytest.fixture
def retry_env(monkeypatch):
    """Settings with retry enabled, 3 attempts, fast for tests."""
    monkeypatch.setenv("ORG_ID", "test-org")
    monkeypatch.setenv("MAPI_KEY", "test-key")
    monkeypatch.setenv("MAPI_SECRET", "test-secret")
    monkeypatch.setenv("MAX_RETRIES", "3")
    monkeypatch.setenv("DISABLE_RETRY", "false")


@pytest.fixture
def no_retry_env(monkeypatch):
    """Settings with retry disabled."""
    monkeypatch.setenv("ORG_ID", "test-org")
    monkeypatch.setenv("MAPI_KEY", "test-key")
    monkeypatch.setenv("MAPI_SECRET", "test-secret")
    monkeypatch.setenv("DISABLE_RETRY", "true")


async def test_successful_request(httpx_mock: HTTPXMock, retry_env):
    """200 response returns normal dict without retry interference."""
    httpx_mock.add_response(json={"success": True, "data": "ok"})
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is True


async def test_retry_on_429(httpx_mock: HTTPXMock, retry_env, monkeypatch):
    """429 status code triggers retry; succeeds on second attempt."""
    monkeypatch.setenv("MAX_RETRIES", "3")
    # First call: 429, second call: 200
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(json={"success": True, "data": "ok"})
    # Patch tenacity wait to avoid actual sleep
    import tenacity
    monkeypatch.setattr(tenacity.nap, "sleep", lambda s: None)
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is True


async def test_retry_on_503(httpx_mock: HTTPXMock, retry_env, monkeypatch):
    """503 status code triggers retry."""
    httpx_mock.add_response(status_code=503)
    httpx_mock.add_response(json={"success": True, "data": "ok"})
    import tenacity
    monkeypatch.setattr(tenacity.nap, "sleep", lambda s: None)
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is True


async def test_no_retry_on_404(httpx_mock: HTTPXMock, retry_env):
    """404 status code fails immediately without retry."""
    httpx_mock.add_response(status_code=404)
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is False
    assert result["status_code"] == 404
    # Only 1 request made (no retry)
    assert len(httpx_mock.get_requests()) == 1


async def test_retry_exhausted_returns_error_dict(
        httpx_mock: HTTPXMock, retry_env, monkeypatch):
    """After max_retries exhausted, returns {success: False} dict."""
    monkeypatch.setenv("MAX_RETRIES", "2")
    httpx_mock.add_response(status_code=429)
    httpx_mock.add_response(status_code=429)
    import tenacity
    monkeypatch.setattr(tenacity.nap, "sleep", lambda s: None)
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is False
    assert result["status_code"] == 429
    assert "Retry exhausted" in result["message"]


async def test_retry_honors_retry_after_header(
        httpx_mock: HTTPXMock, retry_env, monkeypatch):
    """Retry-After header value is used as wait duration."""
    sleep_values = []
    import tenacity
    monkeypatch.setattr(
        tenacity.nap,
        "sleep",
        lambda s: sleep_values.append(s))
    httpx_mock.add_response(status_code=429, headers={"Retry-After": "5"})
    httpx_mock.add_response(json={"success": True, "data": "ok"})
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is True
    # The sleep value should be 5.0 (from Retry-After header)
    assert 5.0 in sleep_values


async def test_disable_retry_skips_retry(httpx_mock: HTTPXMock, no_retry_env):
    """DISABLE_RETRY=true returns error on first retryable status."""
    httpx_mock.add_response(status_code=429)
    result = await request("GET", "https://api.example.com/test", None, {})
    assert result["success"] is False
    assert result["status_code"] == 429
    assert "retry disabled" in result["message"]
    assert len(httpx_mock.get_requests()) == 1
