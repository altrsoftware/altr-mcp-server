import json

from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from altr_mcp.utils.logging import log_tool
from altr_mcp.settings import get_settings
from altr_mcp.utils import access_request

STATUSES = ["NONE", "PENDING_CREATION", "OPEN", "PENDING_APPROVED",
            "CLOSED_APPROVED", "PENDING_DENIED", "CLOSED_DENIED",
            "PENDING_CANCELLED", "CLOSED_CANCELLED", "FAILED"]
MAX_JUSTIFICATION = 1000


def _failed(response) -> bool:
    return isinstance(response, dict) and response.get("success") is False


def _failure(response: dict) -> str:
    if "body" in response:
        body = (response.get("body") or "").strip()[:200]
        return f"HTTP {response.get('status_code')}" + (f": {body}" if body else "")
    return str(response.get("message"))


async def _require_open(request_id: str, action: str) -> None:
    """Only an OPEN request can be decided. Checked here because unified-policy
    before 4.31.1 answers deny on a closed request with 404, as if it didn't exist."""
    response = await access_request.get_access_request(
        get_settings().auth, request_id)
    if _failed(response):
        raise ValueError(
            f"Could not read access request {request_id}: {_failure(response)}")
    status = (response.get("data") or {}).get("status")
    if status != "OPEN":
        raise ValueError(f"Access request {request_id} is {status}; only OPEN "
                         f"requests can be {action}.")


def _justification(justification: str | None) -> str | None:
    justification = (justification or "").strip()
    if len(justification) > MAX_JUSTIFICATION:
        raise ValueError(
            f"justification is limited to {MAX_JUSTIFICATION} characters.")
    return justification or None


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_access_requests(
            limit: int = 100,
            status: str = "OPEN",
            requester: str | None = None,
            sort: str = "desc",
            exclusive_start_key: dict | str | None = None
            ) -> dict:
        """List one page of access requests, newest first, as the console's
        access request list does. Only OPEN requests unless `status` says
        otherwise; the API filters on one status per call.

        To get the next page, pass the response's `last_evaluated_key`
        unchanged as `exclusive_start_key`, with the same `status` and
        `requester`. Keep going until `last_evaluated_key` is absent: the
        last page can be empty and still carry one.

        Args:
            limit: Max requests to return, 1 to 100 (default 100).
            status: OPEN (the default), CLOSED_APPROVED, CLOSED_DENIED,
                CLOSED_CANCELLED or FAILED. The API also accepts NONE,
                PENDING_CREATION and the PENDING_* states.
            requester: Only requests from this requester (exact name).
            sort: "desc" (newest first, the default) or "asc".
            exclusive_start_key: `last_evaluated_key` from the previous page,
                as returned (an object, or the same object as a JSON string).
        """
        if not 1 <= limit <= 100:
            raise ValueError("limit must be from 1 to 100.")
        status = status.strip().upper()
        if status not in STATUSES:
            raise ValueError(f"status must be one of {', '.join(STATUSES)}.")
        sort = sort.strip().lower()
        if sort not in ("asc", "desc"):
            raise ValueError('sort must be "asc" or "desc".')
        params = {"limit": limit, "status": status, "sort": sort}
        if requester is not None:
            params["requester"] = requester
        if isinstance(exclusive_start_key, str) and exclusive_start_key.strip():
            try:
                exclusive_start_key = json.loads(exclusive_start_key)
            except ValueError:
                exclusive_start_key = None
            if not isinstance(exclusive_start_key, dict):
                raise ValueError("exclusive_start_key must be the previous "
                                 "page's last_evaluated_key, unchanged.")
        if isinstance(exclusive_start_key, dict) and exclusive_start_key:
            params["exclusive_start_key"] = exclusive_start_key

        settings = get_settings()
        response = await access_request.get_access_requests(
            settings.auth, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_access_request(request_id: str) -> dict:
        """Get one access request: who asked, for what, why, and its status.

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
            request_id: str, justification: str | None = None) -> dict:
        """Approve an OPEN access request, as the console does. ALTR creates
        a Snowflake access management policy granting what was requested,
        linked to the request, and applies it asynchronously.

        Args:
            request_id: Access request ID (UUID).
            justification: Optional reason recorded with the decision (up
                to 1000 characters).
        """
        justification = _justification(justification)
        await _require_open(request_id, "approved")
        settings = get_settings()
        response = await access_request.approve_access_request(
                settings.auth, request_id, justification)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def deny_access_request(
            request_id: str, justification: str | None = None) -> dict:
        """Deny an OPEN access request, as the console does.

        Args:
            request_id: Access request ID (UUID).
            justification: Optional reason recorded with the decision (up
                to 1000 characters).
        """
        justification = _justification(justification)
        await _require_open(request_id, "denied")
        settings = get_settings()
        response = await access_request.deny_access_request(
                settings.auth, request_id, justification)
        return {"success": True, "data": response, "error": None}
