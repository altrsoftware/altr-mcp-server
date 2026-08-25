import argparse
import sys
from pathlib import Path

from fastmcp import FastMCP
from pydantic import ValidationError

from altr_mcp import __version__
from altr_mcp.middleware import (
    ToolRestrictionMiddleware,
    ValidationRedactionMiddleware,
)
from altr_mcp.settings import get_settings
from altr_mcp.utils.logging import (
    _configure_logging,
    _validation_message,
)
from altr_mcp.tools import register_all

_INSTRUCTIONS = (
    Path(__file__).parent / "instructions.md"
).read_text(encoding="utf-8")
# version= is what clients see as serverInfo.version in the MCP handshake.
# Without it FastMCP reports its own version, not ours.
mcp = FastMCP("altr", instructions=_INSTRUCTIONS, version=__version__)
register_all(mcp)


def _parse_args(argv=None):
    """Handle --version/--help before any configuration is loaded.

    Both must work without ORG_ID/MAPI_* set: asking a program its version
    should never require credentials.
    """
    parser = argparse.ArgumentParser(
        prog="altr-mcp",
        description=(
            "MCP server for ALTR data security. Configuration is read from "
            "the environment; see the README for the full list."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"altr-mcp {__version__}",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Entry point. argv defaults to sys.argv[1:]; pass a list in tests."""
    _parse_args(argv)

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
            # _validation_message rather than str(e): it drops the rejected
            # value. SecretStr masks MAPI_* today, but that is the field
            # type's doing, not this call site's.
            print(
                "ERROR: Configuration validation failed:\n"
                f"{_validation_message(e)}",
                file=sys.stderr,
            )
        sys.exit(1)
    _configure_logging(settings)

    # Register middleware before starting the server
    # Registered first so it is the outermost of ours: FastMCP wraps in
    # reverse registration order, so a ValidationError raised anywhere below
    # -- including inside the restriction middleware -- is still redacted.
    mcp.add_middleware(ValidationRedactionMiddleware())
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
