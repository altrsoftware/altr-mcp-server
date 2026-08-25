import functools
import json
import logging
import re
import sys
import uuid

import structlog
from fastmcp.exceptions import ToolError
from pydantic import ValidationError
from structlog.contextvars import bind_contextvars, clear_contextvars

from altr_mcp.settings import get_settings

logger = structlog.get_logger(__name__)

# structlog's default console renderer shows frame locals, and frame locals
# hold tool arguments -- so a consumer that imports log_tool without calling
# _configure_logging must not be the unsafe case. _configure_logging replaces
# this with the configured renderer.
structlog.configure(
    processors=[
        structlog.dev.ConsoleRenderer(
            exception_formatter=structlog.dev.plain_traceback),
    ],
)


def _derive_action(func_name: str) -> str:
    """Strip CRUD prefix, replace underscores with spaces."""
    for prefix in ("get_", "create_", "delete_", "update_", "list_",
                   "add_", "connect_", "register_", "deregister_",
                   "trigger_", "approve_", "deny_", "cancel_", "search_"):
        if func_name.startswith(prefix):
            remainder = func_name[len(prefix):]
            return f"{prefix.rstrip('_')} {remainder.replace('_', ' ')}"
    return func_name.replace("_", " ")


# The rule: redact an argument whose value is a credential or user-supplied
# free text; log identifiers, enums, and cursors. Keyed on the argument name
# rather than the tool name, so a new tool taking one of these is covered when
# it is written rather than when someone remembers to extend a list.
#
# The list was audited against every tool parameter name in the package. An
# exact list is only as good as the audit behind it, which is why the suffix
# rule below carries the cases nobody thought to enumerate.
#
# `tokens`, `token`, `page_token` and `next_page_token` are deliberately
# absent. A token is the artifact tokenization produces precisely so it can be
# handled freely, ALTR's own Shield audit log is itself keyed by token, and the
# paging ones are cursors. `values` covers the mixed case -- the
# partial_detokenize tools take tokens and plaintext in one dict.
_REDACTED_ARGS = frozenset({
    # Plaintext being tokenized, and the free text Shield's protect flow takes.
    "values", "text",
    # A DSN embeds its password inline: postgres://user:pw@host/db.
    "connection_string",
    # Human free text, which is where unannounced PII arrives. The cost is a
    # comment or justification body missing from the log; the alternative is
    # redacting `text` and leaving its siblings in, which reads as an
    # oversight rather than a rule.
    "comments", "attestation", "justification",
    # An audit search term is a data value, not a filter key -- someone
    # hunting a value in the audit log types that value. `filters` carries
    # the same term structurally: the report-definition filter groups take
    # {"field": "statement_text", "match_type": "contains", "value": ...}.
    "statement_text_contains", "filters",
})
# Applied to any argument name, so the next credential-bearing parameter is
# covered by construction. Deliberately no `_token` rule: it would catch the
# pagination cursors above.
_REDACTED_SUFFIXES = ("_password", "_secret", "_credential", "_credentials",
                      "_private_key", "_passphrase")
_REDACTED = "<redacted>"


def _is_sensitive(name: str) -> bool:
    """Whether an argument's value must not be logged."""
    return name in _REDACTED_ARGS or name.endswith(_REDACTED_SUFFIXES)


def _redact(obj):
    """Replace sensitive values at every depth, preserving shape.

    Some tools take a secret or a plaintext value *as* an argument, so an
    unredacted argument line would carry it. Truncation is not a substitute:
    sensitive values are routinely shorter than any sane truncation limit.

    Recursive, because the suffix rule exists to cover names nobody
    enumerated -- and several tools take caller-shaped nested payloads, where
    a matching name one level down is the same credential as a top-level one.

    Dict keys survive. Which fields were sent is the half of the log line
    worth reading; their values are not.
    """
    if isinstance(obj, dict):
        return {
            key: _redact_value(value) if _is_sensitive(key) else _redact(value)
            for key, value in obj.items()
        }
    if isinstance(obj, list):
        return [_redact(item) for item in obj]
    return obj


def _redact_value(value):
    """Redact one value, keeping enough shape to debug with."""
    # An omitted optional argument is reported as omitted. "<redacted>" here
    # would tell a reader a secret was sent when none was, and "the caller
    # left it out" is a common cause of the failure being debugged.
    if value is None or value == "":
        return value
    if isinstance(value, dict):
        return {name: _REDACTED for name in value}
    return _REDACTED


def _validation_message(exc: ValidationError) -> str:
    """Field paths and messages, without the values that were rejected.

    pydantic's own rendering of a ValidationError includes the value that
    failed, which may be sensitive. errors() keeps that value in a separate
    `input` field, so loc + msg is the part that is safe to repeat.

    The exception is `type == "value_error"`, where msg is "Value error,
    <the ValueError's own text>": a custom validator that interpolates the
    rejected value into its own message puts it back. No validator in
    models.py does that -- they build messages from loc and msg only. Keep it
    that way.
    """
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ())) or "(root)"
        parts.append(f"{loc}: {err.get('msg', 'invalid')}")
    return "; ".join(parts) if parts else "validation failed"


def _format_kwargs(kwargs: dict) -> str:
    """Format kwargs for log line, truncating long values."""
    parts = []
    for k, v in kwargs.items():
        s = repr(v)
        if len(s) > 100:
            s = s[:97] + "..."
        parts.append(f"{k}={s}")
    return ", ".join(parts) if parts else "no args"


def _summarize(result) -> str:
    """Extract a brief result summary for the completion log."""
    if isinstance(result, dict):
        # Handle {success, data, error} wrapper
        if "success" in result:
            if not result.get("success"):
                return f"error: {result.get('error', 'unknown')}"
            data = result.get("data")
            if isinstance(data, (list, dict)):
                return f"{len(data)} items"
            return "ok"
        return f"{len(result)} items"
    if isinstance(result, str):
        return f"{len(result)} chars"
    return "ok"


# pydantic renders `input_value=<repr>, input_type=<type>]` inside its message.
# Anchored on the closing bracket as well as input_type=, so an unfamiliar
# rendering redacts too much rather than nothing, and a value whose repr
# itself contains ", input_type=" cannot end the match early.
_INPUT_VALUE = re.compile(
    r"input_value=.*?(?=, input_type=[^,\]]*\]|\])", re.DOTALL)


class _ScrubValidationInput(logging.Filter):
    """Strip pydantic's `input_value=` from records emitted by dependencies.

    Argument coercion happens above this decorator, and the dependency that
    performs it reports failures with logger.exception -- so a rejected value
    can reach stderr inside a rendered traceback, untouched by anything the
    decorator does. The traceback is produced by the formatter from exc_info,
    so it is pre-rendered here and the formatter handed a scrubbed exc_text
    instead (logging.Formatter reuses exc_text when it is already set).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(
                record.exc_info)
        if record.exc_text:
            record.exc_text = _INPUT_VALUE.sub(
                f"input_value={_REDACTED}", record.exc_text)
        message = record.getMessage()
        if "input_value=" in message:
            record.msg = _INPUT_VALUE.sub(f"input_value={_REDACTED}", message)
            record.args = ()
        return True


# Loggers whose handlers can render a dependency's validation error. Root is
# not enough: a dependency may install handlers on its own non-propagating
# logger, in which case root never sees the record at all.
_SCRUBBED_LOGGERS = ("", "fastmcp", "mcp", "uvicorn", "uvicorn.error")


def _install_scrub_filter() -> None:
    """Attach the scrubbing filter wherever a dependency's records surface.

    Handler-level rather than logger-level. A logger's own filters run only
    for records that logger created, so a filter on `fastmcp` never sees one
    from `fastmcp.server.server`; the propagation walk calls *handlers*, and
    their filters are what every record passes through.

    Rich tracebacks are turned off on any handler that has them, because rich
    renders from the live exception object and ignores the scrubbed exc_text
    this filter prepares.
    """
    scrub = _ScrubValidationInput()
    for name in _SCRUBBED_LOGGERS:
        for handler in logging.getLogger(name).handlers:
            if not any(isinstance(f, _ScrubValidationInput)
                       for f in handler.filters):
                handler.addFilter(scrub)
            if getattr(handler, "rich_tracebacks", False):
                handler.rich_tracebacks = False


def _configure_logging(settings) -> None:
    """Configure structlog.

    JSON mode for production, console mode for development.
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    # show_locals=False on both renderers, stated explicitly rather than
    # relied on -- structlog's default has moved before. Frame locals hold
    # tool arguments, so serialising them would bypass the redaction applied
    # to the argument line.
    if settings.log_format.lower() == "json":
        processors = shared_processors + [
            structlog.processors.ExceptionRenderer(
                structlog.tracebacks.ExceptionDictTransformer(
                    show_locals=False)),
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(
                exception_formatter=structlog.dev.plain_traceback),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    # Bridge stdlib logging for any dependencies that use it
    logging.basicConfig(
        level=log_level,
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )
    _install_scrub_filter()


def log_tool(func):
    """Decorator: correlation ID, structlog binding, invocation logging.

    On success: returns the tool's return value
    (expected: {success, data, error} dict).
    On ValidationError: logs tool_validation_error and
    raises ToolError with JSON error dict, which causes
    fastmcp to set isError: true in the MCP response.
    On general Exception: logs tool_failed and raises
    ToolError with JSON error dict.
    """
    action = _derive_action(func.__name__)

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        correlation_id = f"{func.__name__}:{uuid.uuid4().hex[:8]}"
        clear_contextvars()
        bind_contextvars(correlation_id=correlation_id)
        log = structlog.get_logger(__name__)

        # Dev mode: truncate args; JSON mode: full args. Redacted first in
        # both, since JSON mode does not truncate at all.
        settings = get_settings()
        safe_kwargs = _redact(kwargs)
        if settings.log_format.lower() == "json":
            kwargs_str = repr(safe_kwargs)
        else:
            kwargs_str = _format_kwargs(safe_kwargs)

        log.info("tool_invoked", action=action, args=kwargs_str)
        try:
            result = await func(*args, **kwargs)
            if result is None or result == "":
                log.warning("tool_no_results", action=action)
            else:
                log.info(
                    "tool_completed",
                    action=action,
                    summary=_summarize(result),
                )
            return result
        except ValidationError as e:
            error_msg = f"Validation failed: {_validation_message(e)}"
            log.warning(
                "tool_validation_error",
                action=action, error=error_msg)
            error_dict = {
                "success": False,
                "data": None,
                "error": error_msg,
            }
            raise ToolError(json.dumps(error_dict)) from e
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            log.error(
                "tool_failed",
                action=action,
                error=error_msg,
                exc_info=True,
            )
            error_dict = {
                "success": False,
                "data": None,
                "error": (
                    f"Failed to {action}: {error_msg}"
                ),
            }
            raise ToolError(json.dumps(error_dict)) from e
        finally:
            clear_contextvars()

    return wrapper
