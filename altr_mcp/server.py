import asyncio as _asyncio
import sys
from pathlib import Path

from fastmcp import FastMCP
from pydantic import ValidationError

from altr_mcp.middleware import ToolRestrictionMiddleware
from altr_mcp.settings import get_settings
from altr_mcp.utils.logging import _configure_logging
from altr_mcp.tools import register_all

_INSTRUCTIONS = (
    Path(__file__).parent / "instructions.md"
).read_text(encoding="utf-8")
mcp = FastMCP("altr", instructions=_INSTRUCTIONS)
register_all(mcp)

_tool_count = len(_asyncio.get_event_loop().run_until_complete(mcp.get_tools()))
assert _tool_count == 97, (
    f"Expected 97 tools registered, got {_tool_count}. "
    f"Check tools/ modules for missing register() calls."
)


def main():
    from dotenv import load_dotenv

    load_dotenv(override=True)
    try:
        settings = get_settings()
    except ValidationError as e:
        missing = [
            err["loc"][0]
            for err in e.errors()
            if err["type"] == "missing"
        ]
        if missing:
            fields = ", ".join(str(f).upper() for f in missing)
            print(
                f"ERROR: Missing required environment variables: {fields}",
                file=sys.stderr,
            )
        else:
            print(
                f"ERROR: Configuration validation failed:\n{e}",
                file=sys.stderr,
            )
        sys.exit(1)
    _configure_logging(settings)

    # Register middleware before starting the server
    mcp.add_middleware(
        ToolRestrictionMiddleware(restricted_tools=settings.restricted_tools)
    )

    # Build transport kwargs — host/port only for non-stdio transports
    kwargs: dict = {"transport": settings.mcp_transport}
    if settings.mcp_transport in ("sse", "streamable-http"):
        kwargs["host"] = settings.mcp_host
        kwargs["port"] = settings.mcp_port
    mcp.run(**kwargs)


if __name__ == "__main__":
    main()
