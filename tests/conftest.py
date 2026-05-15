import pytest
from altr_mcp.settings import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear lru_cache before/after every test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_env(monkeypatch):
    """Set minimum required env vars for Settings to load."""
    monkeypatch.setenv("ORG_ID", "test-org")
    monkeypatch.setenv("MAPI_KEY", "test-key")
    monkeypatch.setenv("MAPI_SECRET", "test-secret")
