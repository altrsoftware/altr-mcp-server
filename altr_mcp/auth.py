"""Authentication for the HTTP transports.

stdio needs none: the client starts the server as its own subprocess. Over
SSE or streamable-http the server is a network service, and every tool call
runs with the org's API key, so a caller must prove who it is before it can
list or call tools.
"""

import hmac
import ipaddress

import structlog
from fastmcp.server.auth import AccessToken, TokenVerifier

logger = structlog.get_logger(__name__)


class SharedTokenVerifier(TokenVerifier):
    """Accept one bearer token, MCP_AUTH_TOKEN, compared in constant time."""

    def __init__(self, token: str) -> None:
        super().__init__()
        self._expected = token.encode()

    async def verify_token(self, token: str) -> AccessToken | None:
        if hmac.compare_digest(token.encode(), self._expected):
            return AccessToken(token=token, client_id="altr-mcp", scopes=[])
        return None


def is_loopback(host: str) -> bool:
    """True when only this machine can reach the address."""
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


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
