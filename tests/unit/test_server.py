"""Unit tests for the server entrypoint (altr_mcp/server.py).

Exercises the missing-env error path and the transport branch in main(),
without actually starting an MCP server.
"""
import pytest

from altr_mcp.settings import get_settings


@pytest.fixture(autouse=True)
def _clear_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_main_exits_on_missing_env(monkeypatch, capsys):
    """main() exits 1 with a helpful message if ORG_ID/MAPI_* are unset."""
    monkeypatch.delenv("ORG_ID", raising=False)
    monkeypatch.delenv("MAPI_KEY", raising=False)
    monkeypatch.delenv("MAPI_SECRET", raising=False)
    # Force dotenv not to repopulate from a .env file
    monkeypatch.setattr(
        "dotenv.load_dotenv", lambda *a, **k: False
    )

    from altr_mcp import server

    with pytest.raises(SystemExit) as exc:
        server.main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Missing required environment variables" in captured.err
    assert "ORG_ID" in captured.err
    assert "MAPI_KEY" in captured.err
    assert "MAPI_SECRET" in captured.err


def test_main_stdio_transport_default(monkeypatch):
    """main() with valid env starts the server on stdio by default."""
    monkeypatch.setenv("ORG_ID", "org")
    monkeypatch.setenv("MAPI_KEY", "key")
    monkeypatch.setenv("MAPI_SECRET", "secret")
    monkeypatch.delenv("MCP_TRANSPORT", raising=False)

    from altr_mcp import server

    captured_kwargs = {}

    def _fake_run(**kwargs):
        captured_kwargs.update(kwargs)

    monkeypatch.setattr(server.mcp, "run", _fake_run)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)

    server.main()

    assert captured_kwargs == {"transport": "stdio"}


def test_main_http_transport_passes_host_and_port(monkeypatch):
    """main() with streamable-http transport passes host/port to run()."""
    monkeypatch.setenv("ORG_ID", "org")
    monkeypatch.setenv("MAPI_KEY", "key")
    monkeypatch.setenv("MAPI_SECRET", "secret")
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    monkeypatch.setenv("MCP_HOST", "127.0.0.1")
    monkeypatch.setenv("MCP_PORT", "9000")

    from altr_mcp import server

    captured_kwargs = {}
    monkeypatch.setattr(
        server.mcp, "run",
        lambda **kw: captured_kwargs.update(kw),
    )
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)

    server.main()

    assert captured_kwargs == {
        "transport": "streamable-http",
        "host": "127.0.0.1",
        "port": 9000,
    }
