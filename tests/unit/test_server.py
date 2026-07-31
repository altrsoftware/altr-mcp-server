"""Unit tests for the server entrypoint (altr_mcp/server.py).

Exercises the missing-env error path, the transport branch in main(), and
the version reported to clients, without actually starting an MCP server.
"""
import asyncio

import fastmcp
import pytest

import altr_mcp
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
        server.main([])
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

    server.main([])

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

    server.main([])

    assert captured_kwargs == {
        "transport": "streamable-http",
        "host": "127.0.0.1",
        "port": 9000,
    }


def test_server_info_version_is_ours_not_fastmcps():
    """The MCP handshake reports our version, not the framework's.

    FastMCP falls back to its own version when the server is constructed
    without version=, which is what clients saw before: serverInfo.version
    was fastmcp's 3.2.4 while the package was 0.5.4.
    """
    from altr_mcp import server

    async def _handshake():
        from fastmcp import Client

        async with Client(server.mcp) as client:
            return client.initialize_result.serverInfo.version

    reported = asyncio.run(_handshake())
    assert reported == altr_mcp.__version__, (
        f"clients are told {reported!r}; the package is "
        f"{altr_mcp.__version__!r} (fastmcp is {fastmcp.__version__!r})"
    )


def test_version_flag_prints_package_version(capsys):
    """--version prints the package version and exits 0."""
    from altr_mcp import server

    with pytest.raises(SystemExit) as exc:
        server.main(["--version"])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f"altr-mcp {altr_mcp.__version__}"


def test_version_flag_needs_no_credentials(monkeypatch, capsys):
    """--version works with no ORG_ID/MAPI_* set.

    Asking a program its version must not require credentials, so the flag
    is handled before any settings are loaded.
    """
    monkeypatch.delenv("ORG_ID", raising=False)
    monkeypatch.delenv("MAPI_KEY", raising=False)
    monkeypatch.delenv("MAPI_SECRET", raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)

    from altr_mcp import server

    with pytest.raises(SystemExit) as exc:
        server.main(["--version"])
    assert exc.value.code == 0
    assert altr_mcp.__version__ in capsys.readouterr().out


def test_unknown_flag_is_rejected(capsys):
    """An unrecognized flag errors instead of silently starting the server."""
    from altr_mcp import server

    with pytest.raises(SystemExit) as exc:
        server.main(["--nope"])
    assert exc.value.code == 2
    assert "unrecognized arguments" in capsys.readouterr().err
