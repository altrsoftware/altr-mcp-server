from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from altr_mcp.utils.logging import log_tool
from altr_mcp.settings import get_settings
from altr_mcp.utils import access_request


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    @log_tool
    async def create_access_request(
            requester: str,
            justification: str,
            connection_id: int,
            rules: str | list[dict],
            email: str | None = None,
            role: str | None = None,
            snowflake_metadata: dict | None = None
            ) -> dict:
        """Create a new access request for data access approval.

        Submits a request that must be approved before access is granted.
        Use `get_access_requests` to check status after creation.

        Each rule follows the same format as access management policy rules:
        - actors: list with 'type' ("role"), 'condition', and 'identifiers'.
        - objects: list with 'type' ("database"|"schema"|"table"|"view"),
          'condition', and 'identifiers' or 'fully_qualified_identifiers'.
        - access: list with 'name' ("read"|"write").

        Args:
            requester: Name of the person requesting access.
            justification: Reason for the access request.
            connection_id: ALTR connection ID for the target database.
            rules: List of access rule objects, or a JSON string encoding
                such a list.
            email: Requester's email address.
            role: Requester's Snowflake role.
            snowflake_metadata: Optional dict with 'account_region',
                'account_name', and 'organization_name'.
        """
        if isinstance(rules, str):
            import json
            rules = json.loads(rules)
        data = {
            "requester_identity": {"requester": requester},
            "justification": justification,
            "connection_id": connection_id,
            "rules": rules,
        }
        if email is not None:
            data["requester_identity"]["email"] = email
        if role is not None:
            data["requester_identity"]["role"] = role
        if snowflake_metadata is not None:
            data["snowflake_metadata"] = snowflake_metadata

        settings = get_settings()
        response = await access_request.create_access_request(
            settings.auth, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_access_requests(
            limit: int | None = None,
            requester: str | None = None,
            status: str | None = None,
            sort: str | None = None,
            exclusive_start_key: str | None = None
            ) -> dict:
        """List access requests in your ALTR organization.

        Args:
            limit: Max requests to return (default 10).
            requester: Filter by requester name.
            status: Filter by status. Values: OPEN, PENDING, PENDING_APPROVED,
                CLOSED_APPROVED, PENDING_DENIED, CLOSED_DENIED,
                PENDING_CANCELLED, CLOSED_CANCELLED, CLOSED, FAILED.
            sort: Sort order by creation time ("asc" or "desc").
            exclusive_start_key: Pagination token from a prior call.
        """
        params = {}
        if limit is not None:
            params["limit"] = limit
        if requester is not None:
            params["requester"] = requester
        if status is not None:
            params["status"] = status
        if sort is not None:
            params["sort"] = sort
        if exclusive_start_key is not None:
            params["exclusive_start_key"] = exclusive_start_key

        settings = get_settings()
        response = await access_request.get_access_requests(
            settings.auth, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_access_request(request_id: str) -> dict:
        """Get details for a specific access request.

        Args:
            request_id: Access request ID (UUID).
        """
        settings = get_settings()
        response = await access_request.get_access_request(
            settings.auth, request_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def approve_access_request(
            request_id: str, justification: str) -> dict:
        """Approve a pending access request.

        Args:
            request_id: Access request ID (UUID).
            justification: Reason for approving the request.
        """
        settings = get_settings()
        response = await access_request.approve_access_request(
                settings.auth, request_id, justification)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def deny_access_request(
            request_id: str, justification: str) -> dict:
        """Deny a pending access request.

        Args:
            request_id: Access request ID (UUID).
            justification: Reason for denying the request.
        """
        settings = get_settings()
        response = await access_request.deny_access_request(
                settings.auth, request_id, justification)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def cancel_access_request(
            request_id: str, justification: str) -> dict:
        """Cancel an access request you created.

        Args:
            request_id: Access request ID (UUID).
            justification: Reason for cancelling the request.
        """
        settings = get_settings()
        response = await access_request.cancel_access_request(
                settings.auth, request_id, justification)
        return {"success": True, "data": response, "error": None}
