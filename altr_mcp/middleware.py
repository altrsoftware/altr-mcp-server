"""Tool restriction middleware.

Hides and blocks tools listed in RESTRICTED_TOOLS.
"""

from typing import Optional

import structlog
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

logger = structlog.get_logger(__name__)


class ToolRestrictionMiddleware(Middleware):
    """Hide restricted tools from tools/list and block them on tools/call."""

    def __init__(self, restricted_tools: Optional[str] = None) -> None:
        raw = restricted_tools or ""
        self.restricted_tools: set[str] = {
            t.strip() for t in raw.split(",") if t.strip()
        }
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

    async def on_list_tools(self, context: MiddlewareContext, call_next):
        all_tools = await call_next(context)
        if not self.restricted_tools:
            return all_tools
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
