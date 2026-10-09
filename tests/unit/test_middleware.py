"""Unit tests for ToolRestrictionMiddleware."""
import pytest
import structlog
from unittest.mock import AsyncMock, MagicMock
from fastmcp.exceptions import ToolError
from structlog.testing import capture_logs

from altr_mcp.middleware import ToolRestrictionMiddleware


@pytest.fixture(autouse=True)
def _reset_structlog():
    """Pin structlog's config so capture_logs sees every event.

    Another module's filtering wrapper or cached bound logger would bypass it.
    """
    import altr_mcp.middleware as middleware_module

    structlog.reset_defaults()
    middleware_module.logger = structlog.get_logger("altr_mcp.middleware")
    yield
    structlog.reset_defaults()
    middleware_module.logger = structlog.get_logger("altr_mcp.middleware")


def _unknown_events(logs):
    return [e for e in logs
            if e["event"] == "tool_restriction_middleware.unknown_tools"]


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
    """The once-only flag is instance state, not shared across servers.

    Two independent instances, each of which must warn on its own — a class
    attribute or module global would let the first one silence the second.
    """
    independent_instances = 2
    tool = MagicMock()
    tool.name = "get_policies"
    for _ in range(independent_instances):
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


SECRET = "123-45-6789"


async def test_coercion_failure_does_not_return_the_rejected_value():
    """A wrong-shaped argument must not come back with its own value.

    FastMCP coerces before log_tool runs, and pydantic's message includes the plaintext.
    """
    from fastmcp import Client, FastMCP
    from altr_mcp.middleware import ValidationRedactionMiddleware

    mcp = FastMCP("test")
    mcp.add_middleware(ValidationRedactionMiddleware())

    @mcp.tool()
    async def vault_tokenize(values: dict[str, str]) -> dict:
        return {"success": True, "data": {}, "error": None}

    async with Client(mcp) as client:
        with pytest.raises(Exception) as excinfo:
            # A bare string where a dict is required -- the most likely
            # mistake an LLM-driven caller makes with this signature.
            await client.call_tool("vault_tokenize", {"values": SECRET})

    message = str(excinfo.value)
    assert SECRET not in message, f"rejected value returned to caller: {message}"
    # The diagnosis survives: which argument, and what was wrong with it.
    assert "values" in message


async def test_coercion_failure_still_names_the_field():
    """The replacement error has to remain actionable."""
    from fastmcp import Client, FastMCP
    from altr_mcp.middleware import ValidationRedactionMiddleware

    mcp = FastMCP("test")
    mcp.add_middleware(ValidationRedactionMiddleware())

    @mcp.tool()
    async def add_rules(rules: list[dict]) -> dict:
        return {"success": True, "data": {}, "error": None}

    async with Client(mcp) as client:
        with pytest.raises(Exception) as excinfo:
            await client.call_tool("add_rules", {"rules": "not-a-list"})

    assert "rules" in str(excinfo.value)


def _pydantic_error():
    from pydantic import BaseModel, ValidationError

    class Args(BaseModel):
        values: dict

    try:
        Args(values=SECRET)
    except ValidationError as exc:
        return exc


def _fastmcp_error(cause):
    """fastmcp 3.4.3+ raises its own ValidationError with pydantic's as cause."""
    from fastmcp.exceptions import ValidationError
    try:
        raise ValidationError(str(_pydantic_error())) from cause
    except ValidationError as exc:
        return exc


@pytest.mark.parametrize("exc", [
    pytest.param(_pydantic_error(), id="pydantic-error"),
    pytest.param(_fastmcp_error(_pydantic_error()), id="fastmcp-wrapped"),
])
def test_rejection_message_names_the_field_without_the_input(exc):
    from altr_mcp.middleware import _rejection_message

    message = _rejection_message(exc)

    assert SECRET not in message
    assert "values" in message and "valid dictionary" in message


def test_rejection_message_fails_closed_without_a_pydantic_cause():
    """The wrapper's own text embeds the input, so it is never repeated."""
    from altr_mcp.middleware import _rejection_message

    message = _rejection_message(_fastmcp_error(None))

    assert SECRET not in message
    assert message == "invalid arguments"
