import functools
import json
import logging
import sys
import uuid

import structlog
from fastmcp.exceptions import ToolError
from pydantic import ValidationError
from structlog.contextvars import bind_contextvars, clear_contextvars

from altr_mcp.settings import get_settings

logger = structlog.get_logger(__name__)


def _derive_action(func_name: str) -> str:
    """Strip CRUD prefix, replace underscores with spaces."""
    for prefix in ("get_", "create_", "delete_", "update_", "list_",
                   "add_", "connect_", "register_", "deregister_",
                   "trigger_", "approve_", "deny_", "cancel_", "search_"):
        if func_name.startswith(prefix):
            remainder = func_name[len(prefix):]
            return f"{prefix.rstrip('_')} {remainder.replace('_', ' ')}"
    return func_name.replace("_", " ")


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

    if settings.log_format.lower() == "json":
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(),
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
    )


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

        # Dev mode: truncate args; JSON mode: full args
        settings = get_settings()
        if settings.log_format.lower() == "json":
            kwargs_str = repr(kwargs)
        else:
            kwargs_str = _format_kwargs(kwargs)

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
            error_msg = f"Validation failed: {e}"
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
