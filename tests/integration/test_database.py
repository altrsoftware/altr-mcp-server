"""Integration tests for database tools (altr_mcp/tools/database.py).

Tests the 6 database tools using pytest-httpx to mock HTTP responses.
Verifies the {success, data, error} response shape for happy paths.
"""
import pytest
from fastmcp import FastMCP
from pytest_httpx import HTTPXMock

from altr_mcp.tools.database import register
from tests.integration.conftest import get_tool


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


# ── get_databases ───────────────────────────────────────────────────────

async def test_get_databases_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """get_databases returns {success, data, error} with database list."""
    httpx_mock.add_response(json={
        "data": {
            "databases": [
                {
                    "id": 1,
                    "clientId": "a0a7b846-95d5-4248",
                    "friendlyDatabaseName": "My Database",
                    "databaseType": "snowflake_external_functions",
                    "databaseName": "MYDB",
                    "databaseUsername": "ALTR_SERVICE_USER",
                    "SFCount": 10,
                    "inProgress": 0,
                    "lastConnectedTime": "2025-06-10T20:00:37.000Z",
                },
            ],
            "count": 1,
        },
        "success": True,
    })
    fn = await get_tool(mcp, "get_databases")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_get_databases_empty(httpx_mock: HTTPXMock, test_env, mcp):
    """get_databases handles empty database list."""
    httpx_mock.add_response(json={
        "data": {"databases": [], "count": 0},
        "success": True,
    })
    fn = await get_tool(mcp, "get_databases")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None


# ── get_database_id ─────────────────────────────────────────────────────

async def test_get_database_id_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_database_id returns {success, data, error} with database ID info."""
    httpx_mock.add_response(json={
        "data": {
            "databases": [
                {
                    "id": 42,
                    "clientId": "a0a7b846-95d5-4248",
                    "friendlyDatabaseName": "My Database",
                    "databaseType": "snowflake_external_functions",
                    "databaseName": "MYDB",
                    "databaseUsername": "ALTR_SERVICE_USER",
                    "SFCount": 5,
                    "inProgress": 0,
                    "lastConnectedTime": "2025-06-10T20:00:37.000Z",
                },
            ],
            "count": 1,
        },
        "success": True,
    })
    fn = await get_tool(mcp, "get_database_id")
    result = await fn(database_name="My Database")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_get_database_id_error_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_database_id returns success:True with error data payload on 404."""
    httpx_mock.add_response(status_code=404)
    fn = await get_tool(mcp, "get_database_id")
    # 404 -> api.request returns {success: False} dict
    # Tool wraps: {success: True, data: {success: False, ...}, error: None}
    result = await fn(database_name="NONEXISTENT_DB")
    assert result["success"] is True
    assert result["error"] is None
    inner = result["data"]
    assert inner.get("success") is False


# ── get_service_users ────────────────────────────────────────────────────────

async def test_get_service_users_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_service_users returns {success, data, error}."""
    httpx_mock.add_response(json=[
        {"serviceUserID": "abc123", "name": "SVC_USER_1"},
    ])
    fn = await get_tool(mcp, "get_service_users")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None


# ── create_database ──────────────────────────────────────────────────────────

async def test_create_database_with_service_user(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_database with service_user_id (keypair auth)."""
    httpx_mock.add_response(status_code=201, json={
        "data": {
            "id": 99,
            "friendlyDatabaseName": "test_db",
            "databaseType": "snowflake_external_functions",
        },
        "success": True,
    })
    fn = await get_tool(mcp, "create_database")
    result = await fn(
        friendly_database_name="test_db",
        database_type="snowflake_external_functions",
        database_name="TEST_DB",
        service_user_id="abc123",
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_create_database_with_password(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_database with password auth fallback."""
    httpx_mock.add_response(status_code=201, json={
        "data": {
            "id": 99,
            "friendlyDatabaseName": "test_db",
            "maxNumberOfConnections": 5,
            "maxNumberOfBatches": 15,
            "databasePort": 3305,
            "databaseUsername": "ROOT",
        },
    })
    fn = await get_tool(mcp, "create_database")
    result = await fn(
        friendly_database_name="test_db",
        database_type="snowflake_external_functions",
        database_name="TEST_DB",
        database_username="SVC_USER",
        database_password="secret",
        hostname="abc123.snowflakecomputing.com",
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── update_database ──────────────────────────────────────────────────────────

async def test_update_database_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """update_database returns {success, data, error} on 200."""
    httpx_mock.add_response(json={
        "data": {
            "id": 42,
            "friendlyDatabaseName": "updated_name",
        },
        "success": True,
    })
    fn = await get_tool(mcp, "update_database")
    result = await fn(database_id=42, friendly_database_name="updated_name")
    assert result["success"] is True
    assert result["error"] is None


# ── trigger_database_status_sync ─────────────────────────────────────────────

async def test_trigger_database_status_sync_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """trigger_database_status_sync returns {success, data, error}."""
    httpx_mock.add_response(json={"data": {"ok": True}, "success": True})
    fn = await get_tool(mcp, "trigger_database_status_sync")
    result = await fn(database_id=42)
    assert result["success"] is True
    assert result["error"] is None


# ── delete_database ──────────────────────────────────────────────────────────

async def test_delete_database_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """delete_database returns {success, data, error} on 204."""
    httpx_mock.add_response(status_code=204)
    fn = await get_tool(mcp, "delete_database")
    result = await fn(database_id=42)
    assert result["success"] is True
    assert result["error"] is None
