import pytest
from altr_mcp.settings import get_settings
from altr_mcp.utils import api


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear lru_cache before/after every test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


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


@pytest.fixture
def test_env(monkeypatch):
    """Set minimum required env vars for Settings to load."""
    monkeypatch.setenv("ORG_ID", "test-org")
    monkeypatch.setenv("MAPI_KEY", "test-key")
    monkeypatch.setenv("MAPI_SECRET", "test-secret")
