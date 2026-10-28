"""Authentication for the HTTP transports.

stdio needs none: the client starts the server as its own subprocess. Over
SSE or streamable-http the server is a network service, and every tool call
runs with the org's API key, so a caller must prove who it is before it can
list or call tools.
"""

import hmac
import ipaddress
from urllib.parse import urlsplit

import structlog
from fastmcp.server.auth import AccessToken, TokenVerifier
from starlette.datastructures import Headers
from starlette.responses import PlainTextResponse

logger = structlog.get_logger(__name__)


class SharedTokenVerifier(TokenVerifier):
    """Accept one bearer token, MCP_AUTH_TOKEN, compared in constant time."""

    def __init__(self, token: str) -> None:
        super().__init__()
        self._expected = token.encode()

    async def verify_token(self, token: str) -> AccessToken | None:
        if hmac.compare_digest(token.encode(), self._expected):
            # The request context keeps this object, so it holds a label
            # rather than the secret itself.
            return AccessToken(
                token="mcp-auth-token", client_id="altr-mcp", scopes=[])
        return None


def is_loopback(host: str) -> bool:
    """True when only this machine can reach the address."""
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def _names_loopback(url: str) -> bool:
    hostname = urlsplit(url).hostname
    return hostname is not None and is_loopback(hostname)


class LoopbackOriginGuard:
    """Reject a request whose Host or Origin header names another site.

    A browser on the same machine can reach a loopback server, and with no
    token nothing else tells its requests apart from a local client's.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http":
            headers = Headers(scope=scope)
            if not _names_loopback("//" + headers.get("host", "")):
                response = PlainTextResponse("Misdirected Request", 421)
                await response(scope, receive, send)
                return
            origin = headers.get("origin")
            if origin is not None and not _names_loopback(origin):
                response = PlainTextResponse("Forbidden Origin", 403)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def http_auth(settings) -> TokenVerifier | None:
    """The auth provider for an HTTP transport, or None where none is needed.

    Raises ValueError when the server would accept connections from other
    machines with nothing checking who they are.
    """
    if settings.mcp_auth_token is not None:
        return SharedTokenVerifier(settings.mcp_auth_token.get_secret_value())
    if is_loopback(settings.mcp_host):
        return None
    if settings.mcp_allow_unauthenticated:
        logger.warning(
            "http_auth.disabled",
            host=settings.mcp_host,
            reason="MCP_ALLOW_UNAUTHENTICATED",
        )
        return None
    raise ValueError(
        f"MCP_HOST={settings.mcp_host} accepts connections from other "
        "machines, so set MCP_AUTH_TOKEN. If a gateway in front of the server "
        "authenticates every request, set MCP_ALLOW_UNAUTHENTICATED=true."
    )
