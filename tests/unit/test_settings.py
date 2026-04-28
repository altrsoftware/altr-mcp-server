"""Unit tests for new transport and restriction settings fields."""
from altr_mcp.settings import Settings


def test_mcp_transport_defaults_to_stdio():
    s = Settings(org_id="x", mapi_key="k", mapi_secret="s")
    assert s.mcp_transport == "stdio"


def test_mcp_host_defaults_to_all_interfaces():
    s = Settings(org_id="x", mapi_key="k", mapi_secret="s")
    assert s.mcp_host == "0.0.0.0"


def test_mcp_port_defaults_to_8000():
    s = Settings(org_id="x", mapi_key="k", mapi_secret="s")
    assert s.mcp_port == 8000


def test_restricted_tools_defaults_to_none():
    s = Settings(org_id="x", mapi_key="k", mapi_secret="s")
    assert s.restricted_tools is None


def test_mcp_transport_reads_from_env(monkeypatch):
    monkeypatch.setenv("ORG_ID", "x")
    monkeypatch.setenv("MAPI_KEY", "k")
    monkeypatch.setenv("MAPI_SECRET", "s")
    monkeypatch.setenv("MCP_TRANSPORT", "sse")
    s = Settings()
    assert s.mcp_transport == "sse"


def test_restricted_tools_reads_from_env(monkeypatch):
    monkeypatch.setenv("ORG_ID", "x")
    monkeypatch.setenv("MAPI_KEY", "k")
    monkeypatch.setenv("MAPI_SECRET", "s")
    monkeypatch.setenv("RESTRICTED_TOOLS", "get_tags,delete_tag")
    s = Settings()
    assert s.restricted_tools == "get_tags,delete_tag"
