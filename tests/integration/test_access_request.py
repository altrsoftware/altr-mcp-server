"""Integration tests for access request tools (altr_mcp/tools/access_request.py).

Tests 6 access request tools using pytest-httpx to mock HTTP responses.
Verifies the {success, data, error} response shape for happy paths.
"""
import pytest
from fastmcp import FastMCP
from pytest_httpx import HTTPXMock

from altr_mcp.tools.access_request import register
from tests.integration.conftest import get_tool


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


# ── create_access_request ───────────────────────────────────────────────

async def test_create_access_request_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_access_request returns {success, data, error} on creation."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {
            "id": "a56f3f23-e523-46a8",
            "client_id": "12e06dcd-8b2e-4102",
            "tracking_id": "c4773270-0265-4f41",
            "created_at": "2025-06-12T18:20:05.713Z",
            "rules": [],
            "requester": "Alice",
            "requester_identity": {
                "requester": "Alice",
                "email": "alice@example.com",
                "role": "ANALYST",
            },
            "requester_justification": "Need access for reporting",
            "snowflake_metadata": {
                "account_region": "AWS_US_WEST_2",
                "account_name": "ORG",
                "organization_name": "COMPANY_ORG",
            },
            "status": "OPEN",
        },
    })
    fn = await get_tool(mcp, "create_access_request")
    rules = [{
        "actors": [{"type": "role", "condition": "equals", "identifiers": ["ANALYST"]}],
        "objects": [{"type": "database", "condition": "equals", "identifiers": ["MYDB"]}],
        "access": [{"name": "read"}],
    }]
    result = await fn(
        requester="Alice",
        justification="Need access for reporting",
        connection_id=1,
        rules=rules,
        email="alice@example.com",
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── get_access_requests ─────────────────────────────────────────────────

async def test_get_access_requests_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_access_requests returns {success, data, error} with request list."""
    httpx_mock.add_response(json={
        "success": True,
        "data": [
            {
                "PK": "ORG#12e06dcd#ACCESS_REQUEST",
                "SK": "ACCESS_REQUEST#a56f3f23",
                "id": "req-001",
                "status": "CLOSED_DENIED",
                "requester_justification": "Need access for reporting",
                "approver_justification": "Approved by manager",
                "tracking_id": "b8490d10-0808-44f0",
            }
        ],
    })
    fn = await get_tool(mcp, "get_access_requests")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_get_access_requests_with_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_access_requests passes filter params."""
    httpx_mock.add_response(json={
        "success": True,
        "data": [
            {
                "PK": "ORG#12e06dcd#ACCESS_REQUEST",
                "SK": "ACCESS_REQUEST#req-002",
                "id": "req-002",
                "status": "CLOSED_APPROVED",
                "requester_justification": "Quarterly reporting",
                "tracking_id": "track-uvw012",
            }
        ],
    })
    fn = await get_tool(mcp, "get_access_requests")
    result = await fn(status="CLOSED_APPROVED", limit=5)
    assert result["success"] is True
    assert result["error"] is None


async def test_get_access_requests_all_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_access_requests forwards every filter param."""
    httpx_mock.add_response(json={"success": True, "data": []})
    fn = await get_tool(mcp, "get_access_requests")
    result = await fn(
        limit=20,
        requester="Alice",
        status="OPEN",
        sort="asc",
        exclusive_start_key="cur",
    )
    assert result["success"] is True
    url = str(httpx_mock.get_request().url)
    for fragment in (
        "limit=20",
        "requester=Alice",
        "status=OPEN",
        "sort=asc",
        "exclusive_start_key=cur",
    ):
        assert fragment in url


async def test_create_access_request_json_string_rules_and_all_optionals(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_access_request parses string rules and forwards role + metadata."""
    httpx_mock.add_response(json={"success": True, "data": {}})
    fn = await get_tool(mcp, "create_access_request")
    result = await fn(
        requester="Alice",
        justification="audit",
        connection_id=1,
        rules='[{"actors":[{"type":"role","condition":"equals",'
              '"identifiers":["A"]}],"objects":[{"type":"database",'
              '"condition":"equals","identifiers":["DB"]}],'
              '"access":[{"name":"read"}]}]',
        email="alice@example.com",
        role="ANALYST",
        snowflake_metadata={
            "account_region": "AWS_US_WEST_2",
            "account_name": "ORG",
            "organization_name": "COMPANY",
        },
    )
    assert result["success"] is True
    import json as _json
    body = _json.loads(httpx_mock.get_request().content)
    assert isinstance(body["rules"], list)
    assert body["requester_identity"] == {
        "requester": "Alice",
        "email": "alice@example.com",
        "role": "ANALYST",
    }
    assert body["snowflake_metadata"]["account_region"] == "AWS_US_WEST_2"


# ── get_access_request ──────────────────────────────────────────────────

async def test_get_access_request_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_access_request returns {success, data, error} for specific request."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {
            "PK": "ORG#12e06dcd#ACCESS_REQUEST",
            "SK": "ACCESS_REQUEST#a56f3f23",
            "client_id": "12e06dcd-8b2e-4102",
            "id": "req-001",
            "status": "PENDING",
            "created_at": "2025-06-12T18:20:05.713Z",
            "updated_at": "2025-06-12T18:20:05.718Z",
            "requester_justification": "Need access for reporting",
            "failure_reason": None,
            "tracking_id": "b8490d10-0808-44f0",
        },
    })
    fn = await get_tool(mcp, "get_access_request")
    result = await fn(request_id="req-001")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── approve_access_request ──────────────────────────────────────────────

async def test_approve_access_request_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """approve_access_request returns {success, data, error} on approval."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {
            "PK": "ORG#12e06dcd#ACCESS_REQUEST",
            "SK": "ACCESS_REQUEST#a56f3f23",
            "status": "CLOSED_APPROVED",
            "id": "req-001",
        },
    })
    fn = await get_tool(mcp, "approve_access_request")
    result = await fn(request_id="req-001", justification="Approved for Q1 reporting")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── deny_access_request ─────────────────────────────────────────────────

async def test_deny_access_request_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """deny_access_request returns {success, data, error} on denial."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {
            "status": "CLOSED_DENIED",
            "id": "req-001",
        },
    })
    fn = await get_tool(mcp, "deny_access_request")
    result = await fn(request_id="req-001", justification="Access not justified")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── cancel_access_request ───────────────────────────────────────────────

async def test_cancel_access_request_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """cancel_access_request returns {success, data, error} on cancellation."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {
            "status": "CLOSED_CANCELLED",
            "id": "req-001",
        },
    })
    fn = await get_tool(mcp, "cancel_access_request")
    result = await fn(request_id="req-001", justification="No longer needed")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── error path ──────────────────────────────────────────────────────────

async def test_access_request_error_path(httpx_mock: HTTPXMock, test_env, mcp):
    """access_request tools return error data on HTTP failure."""
    httpx_mock.add_response(status_code=403)
    fn = await get_tool(mcp, "get_access_request")
    result = await fn(request_id="req-forbidden")
    assert result["success"] is True
    assert result["error"] is None
    inner = result["data"]
    assert inner.get("success") is False
