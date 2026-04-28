"""Integration tests for audit tools (altr_mcp/tools/audit.py).

Tests 2 audit tools using pytest-httpx to mock HTTP responses.
Verifies the {success, data, error} response shape for happy paths.
"""
import pytest
from fastmcp import FastMCP
from pytest_httpx import HTTPXMock

from altr_mcp.tools.audit import register
from tests.integration.conftest import get_tool


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


SEARCH_UUID = "search-uuid-1234"


# ── search_audits ───────────────────────────────────────────────────────

async def test_search_audits_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """search_audits returns {success, data, error} with search_uuid."""
    # POST /audits returns only search_uuid — no status field in real API
    httpx_mock.add_response(json={
        "search_uuid": SEARCH_UUID,
    })
    fn = await get_tool(mcp, "search_audits")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_search_audits_with_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    """search_audits passes filter params and returns search_uuid."""
    httpx_mock.add_response(json={
        "search_uuid": SEARCH_UUID,
    })
    fn = await get_tool(mcp, "search_audits")
    result = await fn(
        from_date_time="2025-01-01T00:00:00Z",
        to_date_time="2025-01-31T23:59:59Z",
        database_name=["MYDB"],
        limit=1000,
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── get_audit_results ───────────────────────────────────────────────────

async def test_get_audit_results_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_audit_results returns {success, data, error} with audit records."""
    # GET /audits/{search_uuid} returns audits array with real audit event
    # shape
    httpx_mock.add_response(json={
        "audits": [
            {
                "event_id": "evt-abc123",
                "event_name": "Query",
                "event_source": "sidecar",
                "event_time": "2025-01-15T10:30:00Z",
                "event_time_nano_seconds": 0,
                "event_version": "1.0",
                "org_id": "org-xyz",
                "tracking_id": "track-001",
                "configuration_version_id": "cfg-v1",
                "policy_version_id": "pol-v1",
                "client": {
                    "connection_id": "conn-001",
                    "connection_time": "2025-01-15T10:29:58Z",
                    "host": "10.0.0.1",
                    "port": 5432,
                    "application_name": "psql",
                },
                "sidecar": {
                    "id": "sc-001",
                    "instance_id": "sc-inst-001",
                    "version": "1.2.3",
                },
                "repo": {
                    "host": "db.example.com",
                    "name": "EMPLOYEES",
                    "port": 5432,
                    "type": "Postgres",
                },
                "user_identity": {
                    "repo_user": "dbuser",
                    "consuming_user": {
                        "username": "alice",
                        "email": "alice@example.com",
                        "user_groups": ["analysts"],
                    },
                },
                "statement_request": {
                    "statement": "SELECT * FROM employees",
                    "statement_type": "SELECT",
                    "applied_policy_result": {"block": False},
                    "applied_policies": [],
                    "scanned_columns": [],
                    "projected_columns": [],
                    "destinations": [],
                    "response": {
                        "success": True,
                        "execution_time": "0.023s",
                        "message": "",
                        "records": 42,
                        "bytes": 1024,
                    },
                },
            }
        ],
        "next_page_token": None,
    })
    fn = await get_tool(mcp, "get_audit_results")
    result = await fn(search_uuid=SEARCH_UUID)
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_get_audit_results_with_pagination(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_audit_results passes pagination params."""
    httpx_mock.add_response(json={
        "audits": [],
        "next_page_token": None,
    })
    fn = await get_tool(mcp, "get_audit_results")
    result = await fn(
        search_uuid=SEARCH_UUID,
        limit=50,
        next_page_token=None,
    )
    assert result["success"] is True
    assert result["error"] is None


# ── error path ──────────────────────────────────────────────────────────

async def test_audit_error_path(httpx_mock: HTTPXMock, test_env, mcp):
    """audit tools return error data on HTTP failure."""
    httpx_mock.add_response(status_code=404)
    fn = await get_tool(mcp, "get_audit_results")
    result = await fn(search_uuid="nonexistent-uuid")
    assert result["success"] is True
    assert result["error"] is None
    inner = result["data"]
    assert inner.get("success") is False
