"""Shared fixtures for integration tests."""
import pytest
from fastmcp import FastMCP

from altr_mcp.utils import api


@pytest.fixture
def test_mcp():
    """Create a fresh FastMCP instance for each test."""
    return FastMCP("test")


@pytest.fixture
def retry_env(test_env, monkeypatch):
    """test_env + retry enabled (2 max attempts) with backoff patched out.

    Patches api's async seam, not tenacity.nap.sleep -- the latter is no
    longer what api.request waits on.
    """
    monkeypatch.setenv("MAX_RETRIES", "2")
    monkeypatch.setenv("DISABLE_RETRY", "false")

    async def _no_wait(seconds):
        pass

    monkeypatch.setattr(api, "_async_sleep", _no_wait)


async def get_tool(mcp: FastMCP, tool_name: str):
    """Retrieve a registered tool's function by name."""
    tool = await mcp.get_tool(tool_name)
    if tool is None:
        tools = await mcp.list_tools()
        raise KeyError(
            f"Tool '{tool_name}' not found. "
            f"Available tools: {[t.name for t in tools]}"
        )
    return tool.fn
