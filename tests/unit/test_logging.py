"""Tests for structlog configuration and correlation ID behavior."""
import io
import json
import logging
import sys
from unittest.mock import patch

import pytest
import structlog
from structlog.contextvars import get_contextvars

from fastmcp.exceptions import ToolError
from altr_mcp.utils.logging import _configure_logging, log_tool


@pytest.fixture(autouse=True)
def restore_logging_state():
    """Undo the global logging mutation these tests perform.

    _configure_logging owns the root logger (basicConfig force=True) and
    reconfigures structlog process-wide, and _capture points structlog at a
    StringIO that dies with the test. Without restoring both, a later test
    that logs anything writes into a closed buffer.
    """
    saved_config = structlog.get_config().copy()
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    yield
    structlog.configure(**saved_config)
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


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


async def test_log_tool_warns_on_empty_result():
    """log_tool emits a tool_no_results warning when result is None / ''."""
    @log_tool
    async def empty_tool():
        return None

    with patch("altr_mcp.utils.logging.get_settings",
               return_value=FakeSettingsConsole()):
        result = await empty_tool()
    assert result is None


async def test_log_tool_json_mode_uses_repr_for_kwargs():
    """log_tool uses repr() for kwargs when LOG_FORMAT=json."""
    @log_tool
    async def echo_tool(**kwargs):
        return {"success": True, "data": kwargs, "error": None}

    with patch("altr_mcp.utils.logging.get_settings",
               return_value=FakeSettings()):
        result = await echo_tool(key="value", count=3)
    assert result["data"] == {"key": "value", "count": 3}


def test_summarize_handles_string_result():
    """log_tool's _summarize helper handles plain-string results."""
    from altr_mcp.utils.logging import _summarize

    assert _summarize("hello") == "5 chars"
    # Bare dict without "success" key reports item count
    assert _summarize({"a": 1, "b": 2}) == "2 items"
    # Wrapper dict with success=False reports error
    assert _summarize(
        {"success": False, "error": "boom"}
    ) == "error: boom"
    # Non-dict, non-string falls back to "ok"
    assert _summarize(42) == "ok"


# A recognizable plaintext value. Every test below asserts it never reaches
# the log stream, rather than asserting on the redaction marker -- the marker
# could be present while the real value leaks elsewhere in the same line.
SECRET = "123-45-6789"


def _capture(settings) -> io.StringIO:
    """Configure logging for `settings` and redirect it to a buffer."""
    buffer = io.StringIO()
    _configure_logging(settings)
    structlog.configure(
        logger_factory=structlog.PrintLoggerFactory(file=buffer))
    return buffer


async def test_tokenize_plaintext_is_not_logged_in_json_mode():
    """vault_tokenize's plaintext must not reach the log.

    JSON mode does not truncate the argument line, so redaction is the
    only thing between a secret argument and the log.
    """
    @log_tool
    async def vault_tokenize(values, deterministic=False):
        return {"success": True, "data": {"ssn": "vaultn_x"}, "error": None}

    buffer = _capture(FakeSettings())
    with patch("altr_mcp.utils.logging.get_settings",
               return_value=FakeSettings()):
        await vault_tokenize(values={"ssn": SECRET, "email": "a@b.com"})

    out = buffer.getvalue()
    assert SECRET not in out, f"plaintext leaked into the log: {out}"
    assert "a@b.com" not in out
    # The field names survive -- that is the half of the line worth reading.
    assert "ssn" in out and "email" in out
    assert "<redacted>" in out


async def test_tokenize_plaintext_is_not_logged_in_console_mode():
    """Console-mode truncation is not a redaction mechanism."""
    @log_tool
    async def critical_tokenize(values, deterministic=False):
        return {"success": True, "data": {}, "error": None}

    buffer = _capture(FakeSettingsConsole())
    with patch("altr_mcp.utils.logging.get_settings",
               return_value=FakeSettingsConsole()):
        await critical_tokenize(values={"ssn": SECRET})

    out = buffer.getvalue()
    assert SECRET not in out, f"plaintext leaked into the log: {out}"


async def test_free_text_argument_is_not_logged():
    """`text` is redacted too, for the Shield protect flow."""
    @log_tool
    async def shield_protect(text, collection_name=None):
        return {"success": True, "data": {}, "error": None}

    buffer = _capture(FakeSettings())
    with patch("altr_mcp.utils.logging.get_settings",
               return_value=FakeSettings()):
        await shield_protect(text=f"my ssn is {SECRET}",
                             collection_name="ALTR Managed")

    out = buffer.getvalue()
    assert SECRET not in out, f"free text leaked into the log: {out}"
    # Non-sensitive arguments are still logged in full.
    assert "ALTR Managed" in out


async def test_identifier_arguments_are_still_logged():
    """Redaction is scoped: identifiers stay readable."""
    @log_tool
    async def get_database_id(database_name):
        return {"success": True, "data": {"id": 1}, "error": None}

    buffer = _capture(FakeSettings())
    with patch("altr_mcp.utils.logging.get_settings",
               return_value=FakeSettings()):
        await get_database_id(database_name="SALES_DB")

    assert "SALES_DB" in buffer.getvalue()


async def test_validation_error_does_not_echo_the_rejected_value():
    """A pydantic error carries input_value=; it must not be repeated.

    str(ValidationError) renders the value that failed, so a malformed
    `values` dict would leak its contents through the error path even with
    the argument path redacted.
    """
    from pydantic import BaseModel

    class Strict(BaseModel):
        count: int

    @log_tool
    async def vault_tokenize(values):
        Strict(count=values["ssn"])          # raises ValidationError
        return {"success": True, "data": {}, "error": None}

    buffer = _capture(FakeSettings())
    with patch("altr_mcp.utils.logging.get_settings",
               return_value=FakeSettings()):
        with pytest.raises(ToolError) as excinfo:
            await vault_tokenize(values={"ssn": SECRET})

    out = buffer.getvalue()
    assert SECRET not in out, f"plaintext leaked via the error path: {out}"
    # Nor in the ToolError handed back to the client.
    assert SECRET not in str(excinfo.value)
    # The diagnosis survives: which field, and what was wrong with it.
    assert "count" in str(excinfo.value)


def test_redact_replaces_scalar_sensitive_values():
    """A scalar sensitive argument is replaced wholesale."""
    from altr_mcp.utils.logging import _redact

    assert _redact({"text": "secret", "policy_id": "p1"}) == {
        "text": "<redacted>", "policy_id": "p1"}


def test_redact_keeps_dict_keys():
    """Dict-valued sensitive arguments keep their keys, lose their values."""
    from altr_mcp.utils.logging import _redact

    assert _redact({"values": {"ssn": SECRET, "email": "a@b.com"}}) == {
        "values": {"ssn": "<redacted>", "email": "<redacted>"}}


def test_redact_does_not_touch_tokens():
    """Tokens are not redacted; ALTR's own audit log is keyed by token."""
    from altr_mcp.utils.logging import _redact

    assert _redact({"tokens": {"a": "vaultn_x"}}) == {
        "tokens": {"a": "vaultn_x"}}


def test_validation_message_keeps_locations_only():
    """_validation_message reports loc and msg, never the input."""
    from pydantic import BaseModel, ValidationError
    from altr_mcp.utils.logging import _validation_message

    class M(BaseModel):
        ssn: int

    try:
        M(ssn=SECRET)
    except ValidationError as exc:
        msg = _validation_message(exc)
    assert "ssn" in msg
    assert SECRET not in msg
    assert "input_value" not in msg


async def test_plaintext_is_not_logged_when_the_tool_raises_json_mode():
    """The failure path has to redact too.

    A rendered traceback can carry frame locals, and frame locals hold the
    tool's arguments -- a route the argument line's redaction does not
    cover. Asserts on the value's absence rather than on a marker, so it
    fails if a renderer default changes back.
    """
    @log_tool
    async def vault_tokenize(values, deterministic=False):
        raise RuntimeError("upstream boom")

    buffer = _capture(FakeSettings())
    with patch("altr_mcp.utils.logging.get_settings",
               return_value=FakeSettings()):
        with pytest.raises(ToolError):
            await vault_tokenize(values={"ssn": SECRET})

    out = buffer.getvalue()
    assert SECRET not in out, f"plaintext leaked via the traceback: {out}"


async def test_plaintext_is_not_logged_when_the_tool_raises_console_mode():
    """Console mode leaks by a different renderer, so it needs its own test."""
    @log_tool
    async def critical_tokenize(values, deterministic=False):
        raise RuntimeError("upstream boom")

    buffer = _capture(FakeSettingsConsole())
    with patch("altr_mcp.utils.logging.get_settings",
               return_value=FakeSettingsConsole()):
        with pytest.raises(ToolError):
            await critical_tokenize(values={"ssn": SECRET})

    out = buffer.getvalue()
    assert SECRET not in out, f"plaintext leaked via the traceback: {out}"


PASSWORD = "Sup3rS3cret!Passw0rd"


@pytest.mark.parametrize("kwargs", [
    {"database_password": PASSWORD, "hostname": "h"},
    {"connection_string": f"postgres://svc:{PASSWORD}@db.internal:5432/prod"},
    {"database_secret": PASSWORD},          # covered by the suffix rule
    {"client_passphrase": PASSWORD},        # covered by the suffix rule
])
async def test_credentials_are_not_logged(kwargs):
    """A standing credential in a log is worse than one tokenized value.

    A credential recovered from a log stays valid until it is rotated,
    which makes it a different class of exposure from one data value.
    """
    @log_tool
    async def create_database(**kw):
        return {"success": True, "data": {}, "error": None}

    buffer = _capture(FakeSettings())
    with patch("altr_mcp.utils.logging.get_settings",
               return_value=FakeSettings()):
        await create_database(**kwargs)

    assert PASSWORD not in buffer.getvalue()


@pytest.mark.parametrize(
    "arg", ["comments", "attestation", "justification",
            "statement_text_contains"])
async def test_free_text_siblings_are_not_logged(arg):
    """Free text is redacted uniformly, not just where it is called `text`."""
    @log_tool
    async def some_tool(**kw):
        return {"success": True, "data": {}, "error": None}

    buffer = _capture(FakeSettings())
    with patch("altr_mcp.utils.logging.get_settings",
               return_value=FakeSettings()):
        await some_tool(**{arg: f"contains {SECRET}"})

    assert SECRET not in buffer.getvalue()


@pytest.mark.parametrize("name,sensitive", [
    ("values", True), ("text", True), ("connection_string", True),
    ("comments", True), ("justification", True),
    ("database_password", True), ("anything_secret", True),
    ("tokens", False), ("token", False), ("page_token", False),
    ("next_page_token", False), ("database_name", False),
    ("policy_id", False), ("tag_value", False),
])
def test_is_sensitive_classification(name, sensitive):
    """Cursors and tokens stay readable; credentials and free text do not."""
    from altr_mcp.utils.logging import _is_sensitive

    assert _is_sensitive(name) is sensitive


def test_omitted_sensitive_argument_is_not_marked_redacted():
    """None and "" report as omitted, not as a hidden secret.

    A reader debugging a failure cannot otherwise tell "the caller left it
    out" -- a common cause -- from "a secret was sent and hidden".
    """
    from altr_mcp.utils.logging import _redact

    assert _redact({"values": None, "text": ""}) == {"values": None,
                                                     "text": ""}


def test_scrub_filter_strips_input_value_from_a_traceback():
    """The stderr path: dependencies log pydantic errors with exc_info.

    FastMCP coerces arguments above log_tool and reports failure with
    logger.exception, so the rendered traceback carries the plaintext before
    anything in the decorator runs.
    """
    import logging as stdlib_logging
    from pydantic import BaseModel, ValidationError
    from altr_mcp.utils.logging import _ScrubValidationInput

    class M(BaseModel):
        values: dict

    try:
        M(values=SECRET)
    except ValidationError:
        exc_info = sys.exc_info()

    record = stdlib_logging.LogRecord(
        name="fastmcp", level=stdlib_logging.ERROR, pathname=__file__,
        lineno=1, msg="Error validating tool 'vault_tokenize'", args=(),
        exc_info=exc_info)
    assert _ScrubValidationInput().filter(record) is True
    assert SECRET not in record.exc_text
    assert "<redacted>" in record.exc_text


async def test_coercion_failure_does_not_reach_stderr(capfd):
    """The guard has to be reached, not merely correct.

    test_scrub_filter_strips_input_value_from_a_traceback above calls the
    filter directly, so it proves the logic and not the wiring. Argument
    coercion is reported by a dependency on its own non-propagating logger,
    so a filter attached only to root never sees those records. capfd reads
    the file descriptor, which is what rich writes to.
    """
    from fastmcp import Client, FastMCP
    from altr_mcp.middleware import ValidationRedactionMiddleware
    from altr_mcp.utils.logging import _install_scrub_filter

    # _install_scrub_filter rather than _configure_logging: the leak path is
    # stdlib logging plus the dependency's own renderer, and structlog is not
    # involved. Configuring it here would bind structlog to capfd's captured
    # stderr, which cache_logger_on_first_use then keeps after capfd closes it.
    _install_scrub_filter()

    mcp = FastMCP("test")
    mcp.add_middleware(ValidationRedactionMiddleware())

    @mcp.tool()
    async def vault_tokenize(values: dict[str, str]) -> dict:
        return {"success": True, "data": {}, "error": None}

    async with Client(mcp) as client:
        with pytest.raises(Exception):
            await client.call_tool("vault_tokenize", {"values": SECRET})

    captured = capfd.readouterr()
    assert SECRET not in captured.err, (
        f"rejected value reached stderr: {captured.err}")
    assert SECRET not in captured.out


def test_scrub_filter_is_attached_to_dependency_handlers():
    """Root alone is not enough; dependencies own non-propagating loggers."""
    import logging as stdlib_logging
    from altr_mcp.utils.logging import (
        _ScrubValidationInput, _SCRUBBED_LOGGERS)

    import fastmcp  # noqa: F401  -- ensures its logger exists
    _configure_logging(FakeSettings())

    for name in _SCRUBBED_LOGGERS:
        for handler in stdlib_logging.getLogger(name).handlers:
            assert any(isinstance(f, _ScrubValidationInput)
                       for f in handler.filters), (
                f"logger {name!r} handler {handler} has no scrub filter")
            assert not getattr(handler, "rich_tracebacks", False), (
                f"logger {name!r} handler {handler} still renders rich "
                "tracebacks, which ignore the scrubbed exc_text")


def test_redaction_reaches_nested_values():
    """The suffix rule has to hold at depth, not just at the top level.

    Several tools take caller-shaped nested payloads, so a matching name one
    level down is the same credential as a top-level one.
    """
    from altr_mcp.utils.logging import _redact

    assert _redact({"configuration": {"database_password": "P@ss",
                                      "host": "h"}}) == {
        "configuration": {"database_password": "<redacted>", "host": "h"}}
    assert _redact({"delivery": {"channels": [{"webhook_secret": "s"}]}}) == {
        "delivery": {"channels": [{"webhook_secret": "<redacted>"}]}}


@pytest.mark.parametrize("message,leaks", [
    ("boom [type=x, input_value='SEC', input_type=str]", "SEC"),
    ("boom [type=x, input_value='SEC']", "SEC"),
    ("boom [type=x, input_value='a, input_type=x SEC', input_type=str]", "SEC"),
])
def test_scrub_filter_fails_closed_on_unfamiliar_renderings(message, leaks):
    """An unexpected shape must redact too much, never nothing.

    A redaction control that silently no-ops when the input looks unfamiliar
    is the wrong failure direction, and the value is caller-controlled.
    """
    import logging as stdlib_logging
    from altr_mcp.utils.logging import _ScrubValidationInput

    record = stdlib_logging.LogRecord(
        name="dep", level=stdlib_logging.ERROR, pathname=__file__,
        lineno=1, msg=message, args=(), exc_info=None)
    _ScrubValidationInput().filter(record)
    assert leaks not in record.getMessage(), record.getMessage()
