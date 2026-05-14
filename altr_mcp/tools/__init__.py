from fastmcp import FastMCP


def register_all(mcp: FastMCP) -> None:
    """Register all tool handlers with the MCP server.

    Imports are deferred to avoid circular dependencies with server.py.
    """
    from altr_mcp.tools import (
        access_management,
        access_request,
        audit,
        classification,
        database,
        policy,
        sidecar_config,
        tag,
        telemetry,
    )

    policy.register(mcp)
    tag.register(mcp)
    classification.register(mcp)
    database.register(mcp)
    access_management.register(mcp)
    access_request.register(mcp)
    telemetry.register(mcp)
    audit.register(mcp)
    sidecar_config.register(mcp)
