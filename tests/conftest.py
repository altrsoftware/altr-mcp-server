import pytest
from altr_mcp.settings import get_settings
from altr_mcp.utils import api, policy


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear lru_cache before/after every test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def clean_transport_env(monkeypatch):
    """Keep a developer's own MCP_* settings out of the transport tests."""
    for name in ("MCP_TRANSPORT", "MCP_HOST", "MCP_PORT", "MCP_AUTH_TOKEN",
                 "MCP_ALLOW_UNAUTHENTICATED"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def reset_http_client():
    """Drop api's cached httpx client between tests.

    api.get_client() caches one client per event loop, and pytest gives
    each test its own loop. get_client() would replace a stale one on its
    own, but clearing it here keeps a client built under a mocked
    transport from being visible to the next test at all.
    """
    api.forget_client()
    yield
    api.forget_client()


@pytest.fixture(autouse=True)
def reset_supported_masks():
    """Drop the per-process cache of supported masking levels."""
    policy.forget_supported_masks()
    yield
    policy.forget_supported_masks()


@pytest.fixture
def test_env(monkeypatch):
    """Set minimum required env vars for Settings to load."""
    monkeypatch.setenv("ORG_ID", "test-org")
    monkeypatch.setenv("MAPI_KEY", "test-key")
    monkeypatch.setenv("MAPI_SECRET", "test-secret")
