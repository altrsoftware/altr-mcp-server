"""Tests for structlog configuration and correlation ID behavior."""
import json
import io
from unittest.mock import patch

import pytest
import structlog
from structlog.contextvars import get_contextvars

from fastmcp.exceptions import ToolError
from altr_mcp.utils.logging import _configure_logging, log_tool


class FakeSettings:
    """Minimal settings stub for logging tests."""
    log_level = "DEBUG"
    log_format = "json"


class FakeSettingsConsole:
    log_level = "DEBUG"
    log_format = "console"


def test_json_log_format():
    """LOG_FORMAT=json produces JSON-parseable output."""
    capture = io.StringIO()
    _configure_logging(FakeSettings())
    # Reconfigure to capture to our StringIO
    structlog.configure(
        logger_factory=structlog.PrintLoggerFactory(file=capture),
    )
    log = structlog.get_logger("test")
    log.info("test_event", key="value")
    output = capture.getvalue().strip()
    parsed = json.loads(output)
    assert parsed["event"] == "test_event"
    assert parsed["key"] == "value"


def test_console_log_format():
    """Default LOG_FORMAT=console produces non-JSON output."""
    capture = io.StringIO()
    _configure_logging(FakeSettingsConsole())
    structlog.configure(
        logger_factory=structlog.PrintLoggerFactory(file=capture),
    )
    log = structlog.get_logger("test")
    log.info("test_event", key="value")
    output = capture.getvalue().strip()
    # Console output should NOT be valid JSON
    try:
        json.loads(output)
        is_json = True
    except json.JSONDecodeError:
        is_json = False
    assert not is_json, f"Console mode should not emit JSON, got: {output}"


async def test_correlation_id_format():
    """log_tool generates correlation_id in format func_name:8hex."""
    @log_tool
    async def get_test_thing():
        ctx = get_contextvars()
        return ctx.get("correlation_id", "")

    with patch("altr_mcp.utils.logging.get_settings", return_value=FakeSettingsConsole()):
        result = await get_test_thing()

    assert result.startswith(
        "get_test_thing:"), f"Expected 'get_test_thing:...' got '{result}'"
    hex_part = result.split(":")[1]
    assert len(hex_part) == 8, f"Expected 8 hex chars, got {len(hex_part)}"
    int(hex_part, 16)  # Validates it's valid hex


async def test_correlation_id_cleared_after_tool():
    """Correlation ID does not leak between tool invocations."""
    @log_tool
    async def first_tool():
        return "ok"

    @log_tool
    async def second_tool():
        ctx = get_contextvars()
        return ctx.get("correlation_id", "")

    with patch("altr_mcp.utils.logging.get_settings", return_value=FakeSettingsConsole()):
        await first_tool()
        result = await second_tool()

    # second_tool should have its OWN correlation ID, not first_tool's
    assert result.startswith(
        "second_tool:"), f"Expected 'second_tool:...' got '{result}'"


async def test_log_tool_raises_tool_error_on_exception():
    """log_tool wraps exceptions in ToolError with JSON error dict."""
    @log_tool
    async def failing_tool():
        raise RuntimeError("boom")

    with patch("altr_mcp.utils.logging.get_settings", return_value=FakeSettingsConsole()):
        with pytest.raises(ToolError) as exc_info:
            await failing_tool()
    error = json.loads(str(exc_info.value))
    assert error["success"] is False
    assert error["data"] is None
    assert "boom" in error["error"]
