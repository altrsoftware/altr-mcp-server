"""Shared fixtures for integration tests."""
import pytest
from fastmcp import FastMCP


@pytest.fixture
def test_mcp():
    """Create a fresh FastMCP instance for each test."""
    return FastMCP("test")


async def get_tool(mcp: FastMCP, tool_name: str):
    """Retrieve a registered tool's function by name."""
    tool = await mcp.get_tool(tool_name)
    if tool is None:
        tools = await mcp.get_tools()
        raise KeyError(
            f"Tool '{tool_name}' not found. "
            f"Available tools: {list(tools.keys())}"
        )
    return tool.fn
