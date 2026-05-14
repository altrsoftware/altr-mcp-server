"""Canary tests — prove the test harness works before real tests arrive in Phase 2."""
import asyncio

from altr_mcp.settings import get_settings


def test_settings_load_from_env(test_env):
    """Settings class loads required fields from environment variables."""
    settings = get_settings()
    assert settings.org_id == "test-org"
    assert settings.mapi_key.get_secret_value() == "test-key"
    assert settings.mapi_secret.get_secret_value() == "test-secret"


def test_settings_defaults(test_env):
    """New settings fields have correct default values."""
    settings = get_settings()
    assert settings.log_format == "console"
    assert settings.max_retries == 3
    assert settings.disable_retry is False


async def test_async_harness_executes():
    """Canary: proves async tests actually run (not silently skipped by pytest-asyncio)."""
    result = []

    async def _inner():
        await asyncio.sleep(0)
        result.append(True)

    await _inner()
    assert result == [
        True], "Async test body did not execute — check asyncio_mode=auto in pyproject.toml"
