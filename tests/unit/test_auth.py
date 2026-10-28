"""HTTP transport authentication: the verifier, the startup policy, and the
401 a request gets without the token."""
import httpx
import pytest
import structlog
from fastmcp import FastMCP
from starlette.middleware import Middleware

from altr_mcp.auth import (
    LoopbackOriginGuard, SharedTokenVerifier, http_auth, is_loopback)
from altr_mcp.settings import Settings

TOKEN = "t" * 40


def _settings(**overrides):
    return Settings(org_id="x", mapi_key="k", mapi_secret="s", **overrides)


@pytest.mark.parametrize("host,expected", [
    ("127.0.0.1", True), ("127.1.2.3", True), ("::1", True), ("[::1]", True),
    ("localhost", True), ("LOCALHOST", True), ("::ffff:127.0.0.1", True),
    ("0.0.0.0", False), ("::", False), ("10.0.0.5", False),
    ("mcp.example.com", False), ("", False), ("0", False),
])
def test_is_loopback(host, expected):
    assert is_loopback(host) is expected


async def test_verifier_accepts_only_the_token():
    verifier = SharedTokenVerifier(TOKEN)
    accepted = await verifier.verify_token(TOKEN)
    assert accepted.client_id == "altr-mcp"
    # The request context keeps the AccessToken, so it must not hold the secret.
    assert TOKEN not in repr(accepted)
    assert await verifier.verify_token("x" * 40) is None
    assert await verifier.verify_token(TOKEN[:-1]) is None
    assert await verifier.verify_token("") is None


def test_a_token_is_always_required_once_set():
    """Even on loopback: setting the token is a request to check it."""
    assert isinstance(http_auth(_settings(mcp_auth_token=TOKEN)),
                      SharedTokenVerifier)
    assert isinstance(
        http_auth(_settings(mcp_auth_token=TOKEN, mcp_host="0.0.0.0")),
        SharedTokenVerifier)


def test_loopback_needs_no_token():
    assert http_auth(_settings()) is None


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "10.0.0.5"])
def test_listening_beyond_loopback_without_a_token_is_refused(host):
    with pytest.raises(ValueError, match="set MCP_AUTH_TOKEN"):
        http_auth(_settings(mcp_host=host))


def test_allow_unauthenticated_is_an_explicit_choice(monkeypatch):
    monkeypatch.setenv("MCP_ALLOW_UNAUTHENTICATED", "true")
    with structlog.testing.capture_logs() as logs:
        assert http_auth(_settings(mcp_host="0.0.0.0")) is None
    # The warning is the operator's only sign that nothing checks callers.
    assert [e["event"] for e in logs if e["log_level"] == "warning"] == [
        "http_auth.disabled"]


def _server():
    server = FastMCP("t")

    @server.tool
    def ping() -> str:
        return "pong"

    server.auth = SharedTokenVerifier(TOKEN)
    return server


INITIALIZE = {
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
               "clientInfo": {"name": "c", "version": "1"}},
}
HEADERS = {"accept": "application/json, text/event-stream",
           "content-type": "application/json"}


async def _send(app, method, path, **kwargs):
    # The streamable-http session manager starts in the app's lifespan.
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
                transport=transport, base_url="http://127.0.0.1:8000") as c:
            return await c.request(method, path, **kwargs)


@pytest.mark.parametrize("authorization,status", [
    (None, 401),
    ("Bearer " + "x" * 40, 401),
    (TOKEN, 401),  # no scheme
    ("Bearer " + TOKEN, 200),
    ("bearer " + TOKEN, 200),  # the scheme is case-insensitive
])
async def test_streamable_http_requires_the_bearer_token(
        authorization, status):
    headers = dict(HEADERS)
    if authorization is not None:
        headers["authorization"] = authorization
    app = _server().http_app(transport="streamable-http")
    response = await _send(app, "POST", "/mcp", json=INITIALIZE,
                           headers=headers)
    assert response.status_code == status


async def test_sse_requires_the_bearer_token():
    app = _server().http_app(transport="sse")
    response = await _send(app, "GET", "/sse")
    assert response.status_code == 401


async def test_sse_messages_require_the_bearer_token():
    """Tool calls travel on the /messages/ endpoint, not on the stream."""
    app = _server().http_app(transport="sse")
    response = await _send(app, "POST", "/messages/?session_id=0",
                           json=INITIALIZE)
    assert response.status_code == 401


def _guarded():
    server = FastMCP("t")

    @server.tool
    def ping() -> str:
        return "pong"

    return server.http_app(
        transport="streamable-http",
        middleware=[Middleware(LoopbackOriginGuard)])


@pytest.mark.parametrize("host,origin,status", [
    ("127.0.0.1:8000", None, 200),
    ("localhost:8000", "http://localhost:8000", 200),
    ("[::1]:8000", "http://[::1]:8000", 200),
    ("attacker.example:8000", None, 421),
    ("", None, 421),
    ("127.0.0.1:8000", "http://attacker.example:8000", 403),
    ("127.0.0.1:8000", "null", 403),
])
async def test_loopback_guard_checks_host_and_origin(host, origin, status):
    headers = dict(HEADERS, host=host)
    if origin is not None:
        headers["origin"] = origin
    response = await _send(_guarded(), "POST", "/mcp", json=INITIALIZE,
                           headers=headers)
    assert response.status_code == status
