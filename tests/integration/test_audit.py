"""Integration tests for audit tools (altr_mcp/tools/audit.py).

Tests all 6 audit tools using pytest-httpx to mock HTTP responses.
Verifies the {success, data, error} response shape and parameter
passthrough for sidecar / query / system audit families.
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


async def test_search_audits_normalizes_scalars_to_lists(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Scalar list-typed filters are wrapped in single-element lists."""
    httpx_mock.add_response(json={"search_uuid": SEARCH_UUID})
    fn = await get_tool(mcp, "search_audits")
    result = await fn(
        offset=10,
        consuming_user="alice",
        consuming_user_email="alice@example.com",
        query_id="q-1",
        sidecar_id="sc-1",
        sidecar_instance_id="sci-1",
        table_name="employees",
        schema_name="public",
        column_name="ssn",
        statement_type="SELECT",
        statement_text_contains="SELECT",
        order_by="asc",
        sort_by="rows_accessed",
    )
    assert result["success"] is True
    # search_audits sends filters as query-string params (no body).
    url_str = str(httpx_mock.get_request().url)
    for key in (
        "consuming_user=alice",
        "consuming_user_email=alice%40example.com",
        "query_id=q-1",
        "sidecar_id=sc-1",
        "sidecar_instance_id=sci-1",
        "table_name=employees",
        "schema_name=public",
        "column_name=ssn",
        "statement_type=SELECT",
        "statement_text_contains=SELECT",
        "order_by=asc",
        "sort_by=rows_accessed",
        "offset=10",
    ):
        assert key in url_str


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


# ── search_query_audits ─────────────────────────────────────────────────

async def test_search_query_audits_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """search_query_audits returns {success, data, error} with search_uuid."""
    httpx_mock.add_response(json={"search_uuid": SEARCH_UUID})
    fn = await get_tool(mcp, "search_query_audits")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_search_query_audits_with_all_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    """search_query_audits forwards every supported filter param."""
    httpx_mock.add_response(json={"search_uuid": SEARCH_UUID})
    fn = await get_tool(mcp, "search_query_audits")
    result = await fn(
        limit=100,
        offset=5,
        from_date_time="2025-01-01T00:00:00Z",
        to_date_time="2025-01-31T00:00:00Z",
        executing_role="ANALYST",
        executing_user="alice",
        query_id="q-1",
        policy_tag_name="PII",
        policy_tag_value="SSN",
        policy_column_database_name="DB",
        policy_column_schema_name="SCHEMA",
        policy_column_table_name="TBL",
        policy_column_name="COL",
        order_by="asc",
        sort_by="rows_accessed",
    )
    assert result["success"] is True
    url_str = str(httpx_mock.get_request().url)
    for key in (
        "limit=100",
        "offset=5",
        "executing_role=ANALYST",
        "executing_user=alice",
        "policy_tag_name=PII",
        "policy_tag_value=SSN",
        "policy_column_database_name=DB",
        "policy_column_table_name=TBL",
        "order_by=asc",
        "sort_by=rows_accessed",
    ):
        assert key in url_str


# ── get_query_audit_results ─────────────────────────────────────────────

async def test_get_query_audit_results_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_query_audit_results returns {success, data, error} with rows."""
    httpx_mock.add_response(json={
        "rows": [],
        "next_page_token": None,
    })
    fn = await get_tool(mcp, "get_query_audit_results")
    result = await fn(search_uuid=SEARCH_UUID, limit=50)
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_get_query_audit_results_with_pagination_token(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_query_audit_results forwards next_page_token."""
    httpx_mock.add_response(json={"rows": [], "next_page_token": None})
    fn = await get_tool(mcp, "get_query_audit_results")
    result = await fn(
        search_uuid=SEARCH_UUID,
        limit=10,
        next_page_token="page-2",
    )
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert "next_page_token=page-2" in str(request.url)


# ── search_system_audits ────────────────────────────────────────────────

async def test_search_system_audits_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """search_system_audits returns {success, data, error} with token."""
    httpx_mock.add_response(json={
        "token": "system-audit-token-001",
        "moreData": False,
        "results": [],
    })
    fn = await get_tool(mcp, "search_system_audits")
    result = await fn(category="API Keys")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_search_system_audits_with_all_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    """search_system_audits forwards limit, offset, wait, from/to dates."""
    httpx_mock.add_response(json={"token": "tok-1"})
    fn = await get_tool(mcp, "search_system_audits")
    result = await fn(
        category="Data Sources",
        limit=25,
        offset=0,
        wait=500,
        from_date_time="2025-01-01T00:00:00Z",
        to_date_time="2025-01-02T00:00:00Z",
    )
    assert result["success"] is True
    url_str = str(httpx_mock.get_request().url)
    # search_system_audits maps from_date_time → "from" and to_date_time → "to"
    for fragment in (
        "category=Data+Sources",
        "limit=25",
        "offset=0",
        "wait=500",
        "from=2025-01-01T00%3A00%3A00Z",
        "to=2025-01-02T00%3A00%3A00Z",
    ):
        assert fragment in url_str


# ── get_system_audit_results ────────────────────────────────────────────

async def test_get_system_audit_results_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_system_audit_results returns {success, data, error}."""
    httpx_mock.add_response(json={
        "results": [],
        "moreData": False,
        "token": "tok-next",
    })
    fn = await get_tool(mcp, "get_system_audit_results")
    result = await fn(token="some-token")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_get_system_audit_results_url_encodes_token(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_system_audit_results URL-encodes the token in the path."""
    httpx_mock.add_response(json={"results": [], "moreData": False})
    fn = await get_tool(mcp, "get_system_audit_results")
    raw_token = "tok with spaces/and+slashes"
    result = await fn(token=raw_token)
    assert result["success"] is True
    request = httpx_mock.get_request()
    # The token must be URL-encoded in the path — spaces become %20,
    # slashes become %2F, plus signs become %2B
    assert "tok%20with%20spaces%2Fand%2Bslashes" in str(request.url)


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


# ── invalid JSON / 5xx retry ─────────────────────────────────────────────────

async def test_audit_invalid_json_response(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(
        content=b"<html>Bad Gateway</html>",
        headers={"Content-Type": "text/html"},
    )
    fn = await get_tool(mcp, "search_audits")
    result = await fn()
    assert result["success"] is True
    assert "raw" in result["data"]


async def test_audit_5xx_retry_exhaustion(
        httpx_mock: HTTPXMock, retry_env, mcp):
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    fn = await get_tool(mcp, "search_audits")
    result = await fn()
    assert result["success"] is True
    assert result["data"]["success"] is False
    assert "Retry exhausted" in result["data"]["message"]
