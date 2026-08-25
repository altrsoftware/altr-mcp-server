"""Server middleware.

ToolRestrictionMiddleware hides and blocks tools listed in
RESTRICTED_TOOLS. ValidationRedactionMiddleware keeps rejected argument
values out of the error returned to the caller.
"""

from typing import Optional

import structlog
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from pydantic import ValidationError

from altr_mcp.utils.logging import _validation_message

logger = structlog.get_logger(__name__)


class ToolRestrictionMiddleware(Middleware):
    """Hide restricted tools from tools/list and block them on tools/call."""

    def __init__(self, restricted_tools: Optional[str] = None) -> None:
        raw = restricted_tools or ""
        self.restricted_tools: set[str] = {
            t.strip() for t in raw.split(",") if t.strip()
        }
        self._checked_names = False
        if self.restricted_tools:
            logger.info(
                "tool_restriction_middleware.init",
                restricted_count=len(self.restricted_tools),
                restricted_tools=sorted(self.restricted_tools),
            )

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.message.name
        if tool_name in self.restricted_tools:
            logger.warning(
                "tool_restriction_middleware.blocked",
                tool=tool_name,
            )
            raise ToolError(
                f"Tool '{tool_name}' is not available"
                " due to access restrictions"
            )
        return await call_next(context)

    def _check_names_once(self, registered: set[str]) -> None:
        """Warn about restricted names that match no registered tool.

        A name matching nothing restricts nothing, so a stale or misspelled
        entry silently leaves a tool exposed while the operator believes it is
        blocked. The 11 `delete_*` tools renamed to `disconnect_*` in 0.4.0 are
        the likely source.

        Deferred to the first tools/list rather than done in __init__ because
        this middleware holds no reference to the server and every FastMCP tool
        accessor is async, while main() is sync. Note the comparison set is the
        caller's visible tool list, which FastMCP has already filtered by
        enablement and per-session auth — not the raw registry.
        """
        if self._checked_names:
            return
        self._checked_names = True
        unknown = sorted(self.restricted_tools - registered)
        if unknown:
            logger.warning(
                "tool_restriction_middleware.unknown_tools",
                unknown_tools=unknown,
                unknown_count=len(unknown),
                hint=(
                    "these RESTRICTED_TOOLS entries match no registered tool"
                    " and restrict nothing; check for tools renamed in 0.4.0"
                ),
            )

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        all_tools = await call_next(context)
        if not self.restricted_tools:
            return all_tools
        self._check_names_once({t.name for t in all_tools})
        filtered = [
            t for t in all_tools
            if t.name not in self.restricted_tools
        ]
        logger.debug(
            "tool_restriction_middleware.filtered",
            total=len(all_tools),
            visible=len(filtered),
        )
        return filtered


class ValidationRedactionMiddleware(Middleware):
    """Replace argument-coercion errors with a message carrying no input.

    FastMCP coerces tool arguments *above* the log_tool decorator, so a
    wrong-shaped argument never enters the tool body and never reaches that
    decorator's own ValidationError handling. The pydantic error it raises
    embeds the value it rejected, which for some tools is the data those
    tools exist to protect, and FastMCP surfaces it to the caller.

    A middleware is the outermost seam that still sees the exception, so the
    replacement happens here. `from None` matters: chaining would keep the
    original message reachable through __cause__ for any handler that renders
    it.
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        try:
            return await call_next(context)
        except ValidationError as exc:
            logger.warning(
                "tool_argument_validation_failed",
                tool=context.message.name,
                error=_validation_message(exc),
            )
            raise ToolError(
                f"Validation failed: {_validation_message(exc)}") from None
