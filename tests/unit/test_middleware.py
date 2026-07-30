"""Unit tests for ToolRestrictionMiddleware."""
import pytest
import structlog
from unittest.mock import AsyncMock, MagicMock
from fastmcp.exceptions import ToolError
from structlog.testing import capture_logs

from altr_mcp.middleware import ToolRestrictionMiddleware


@pytest.fixture(autouse=True)
def _reset_structlog():
    """Pin structlog's config for the log-capture assertions below.

    capture_logs swaps the processor list but leaves wrapper_class alone, so a
    filtering bound logger configured by another test module would drop events
    before LogCapture ever sees them.
    """
    structlog.reset_defaults()
    yield
    structlog.reset_defaults()


# ── Constructor parsing ─────────────────────────────────────────────────

def test_parses_comma_separated_tools():
    m = ToolRestrictionMiddleware("get_tags,disconnect_tag")
    assert m.restricted_tools == {"get_tags", "disconnect_tag"}


def test_strips_whitespace_around_commas():
    m = ToolRestrictionMiddleware("get_tags , disconnect_tag , get_policies")
    assert m.restricted_tools == {"get_tags", "disconnect_tag", "get_policies"}


def test_empty_string_means_no_restrictions():
    m = ToolRestrictionMiddleware("")
    assert m.restricted_tools == set()


def test_none_means_no_restrictions():
    m = ToolRestrictionMiddleware(None)
    assert m.restricted_tools == set()


def test_ignores_empty_segments():
    m = ToolRestrictionMiddleware("get_tags,,disconnect_tag,")
    assert m.restricted_tools == {"get_tags", "disconnect_tag"}


# ── on_list_tools ───────────────────────────────────────────────────────

async def test_on_list_tools_filters_restricted():
    m = ToolRestrictionMiddleware("get_tags,disconnect_tag")
    tool_a = MagicMock(name="get_tags")
    tool_a.name = "get_tags"
    tool_b = MagicMock(name="get_policies")
    tool_b.name = "get_policies"
    tool_c = MagicMock(name="disconnect_tag")
    tool_c.name = "disconnect_tag"

    call_next = AsyncMock(return_value=[tool_a, tool_b, tool_c])
    context = MagicMock()

    result = await m.on_list_tools(context, call_next)
    assert len(result) == 1
    assert result[0].name == "get_policies"


def _unknown_events(logs):
    return [e for e in logs
            if e["event"] == "tool_restriction_middleware.unknown_tools"]


async def test_on_list_tools_warns_once_for_unknown_names():
    """A stale name restricts nothing, so it must not fail silently."""
    m = ToolRestrictionMiddleware("delete_database,get_policies")
    tool = MagicMock()
    tool.name = "get_policies"
    call_next = AsyncMock(return_value=[tool])
    context = MagicMock()

    with capture_logs() as logs:
        await m.on_list_tools(context, call_next)
    events = _unknown_events(logs)
    assert len(events) == 1
    assert events[0]["log_level"] == "warning"
    assert events[0]["unknown_tools"] == ["delete_database"]

    # Only once — tools/list is called repeatedly per session.
    with capture_logs() as logs:
        await m.on_list_tools(context, call_next)
    assert _unknown_events(logs) == []


async def test_on_list_tools_silent_when_all_names_known():
    m = ToolRestrictionMiddleware("disconnect_database")
    tool = MagicMock()
    tool.name = "disconnect_database"
    call_next = AsyncMock(return_value=[tool])
    context = MagicMock()

    with capture_logs() as logs:
        result = await m.on_list_tools(context, call_next)
    assert result == []
    assert _unknown_events(logs) == []


async def test_warns_per_instance_not_per_process():
    """The once-only flag is instance state, not shared across servers."""
    tool = MagicMock()
    tool.name = "get_policies"
    for _ in range(2):
        m = ToolRestrictionMiddleware("delete_database,get_policies")
        with capture_logs() as logs:
            await m.on_list_tools(MagicMock(), AsyncMock(return_value=[tool]))
        assert len(_unknown_events(logs)) == 1


async def test_unknown_names_still_filter_known_ones():
    """An unknown entry must not stop the valid entries from applying."""
    m = ToolRestrictionMiddleware("delete_tag,disconnect_tag")
    stale = MagicMock()
    stale.name = "disconnect_tag"
    kept = MagicMock()
    kept.name = "get_tags"
    call_next = AsyncMock(return_value=[stale, kept])
    context = MagicMock()

    with capture_logs() as logs:
        result = await m.on_list_tools(context, call_next)
    assert [t.name for t in result] == ["get_tags"]
    assert _unknown_events(logs)[0]["unknown_tools"] == ["delete_tag"]


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
