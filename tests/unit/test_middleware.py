"""Unit tests for ToolRestrictionMiddleware."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastmcp.exceptions import ToolError

from altr_mcp.middleware import ToolRestrictionMiddleware


# ── Constructor parsing ─────────────────────────────────────────────────

def test_parses_comma_separated_tools():
    m = ToolRestrictionMiddleware("get_tags,delete_tag")
    assert m.restricted_tools == {"get_tags", "delete_tag"}


def test_strips_whitespace_around_commas():
    m = ToolRestrictionMiddleware("get_tags , delete_tag , get_policies")
    assert m.restricted_tools == {"get_tags", "delete_tag", "get_policies"}


def test_empty_string_means_no_restrictions():
    m = ToolRestrictionMiddleware("")
    assert m.restricted_tools == set()


def test_none_means_no_restrictions():
    m = ToolRestrictionMiddleware(None)
    assert m.restricted_tools == set()


def test_ignores_empty_segments():
    m = ToolRestrictionMiddleware("get_tags,,delete_tag,")
    assert m.restricted_tools == {"get_tags", "delete_tag"}


# ── on_list_tools ───────────────────────────────────────────────────────

async def test_on_list_tools_filters_restricted():
    m = ToolRestrictionMiddleware("get_tags,delete_tag")
    tool_a = MagicMock(name="get_tags")
    tool_a.name = "get_tags"
    tool_b = MagicMock(name="get_policies")
    tool_b.name = "get_policies"
    tool_c = MagicMock(name="delete_tag")
    tool_c.name = "delete_tag"

    call_next = AsyncMock(return_value=[tool_a, tool_b, tool_c])
    context = MagicMock()

    result = await m.on_list_tools(context, call_next)
    assert len(result) == 1
    assert result[0].name == "get_policies"


async def test_on_list_tools_returns_all_when_no_restrictions():
    m = ToolRestrictionMiddleware(None)
    tool_a = MagicMock()
    tool_a.name = "get_tags"
    call_next = AsyncMock(return_value=[tool_a])
    context = MagicMock()

    result = await m.on_list_tools(context, call_next)
    assert len(result) == 1


# ── on_call_tool ────────────────────────────────────────────────────────

async def test_on_call_tool_raises_for_restricted():
    m = ToolRestrictionMiddleware("get_tags")
    context = MagicMock()
    context.message.name = "get_tags"
    call_next = AsyncMock()

    with pytest.raises(ToolError, match="not available due to access restrictions"):
        await m.on_call_tool(context, call_next)
    call_next.assert_not_called()


async def test_on_call_tool_allows_unrestricted():
    m = ToolRestrictionMiddleware("get_tags")
    context = MagicMock()
    context.message.name = "get_policies"
    call_next = AsyncMock(return_value="result")

    result = await m.on_call_tool(context, call_next)
    assert result == "result"
    call_next.assert_called_once_with(context)
