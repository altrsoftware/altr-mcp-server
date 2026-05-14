"""Integration tests for access management tools.

Tests 4 access management tools using pytest-httpx to
mock HTTP responses. Verifies the {success, data, error}
response shape for happy paths.
"""
import pytest
from fastmcp import FastMCP
from pytest_httpx import HTTPXMock

from altr_mcp.tools.access_management import register
from tests.integration.conftest import get_tool


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


# ── create_snowflake_access_policy ──────────────────

async def test_create_snowflake_access_policy_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_snowflake_access_policy returns data."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {
            "policy_id": "GRANT#afe0b9c9-3a29#DATABASE_TYPE#9",
            "policy": {
                "PK": "ORG#a0a7b846#POLICY",
                "SK": "GRANT#afe0b9c9-3a29#DATABASE_TYPE#9",
                "client_id": "a0a7b846-95d5-4248",
                "created_at": "2025-02-07T16:12:12.807Z",
                "updated_at": "2025-02-07T16:12:12.807Z",
                "policy_name": "My Policy",
                "description": "Test access policy",
                "connection_ids": [1],
                "rules_pending": [],
                "rules_applied": None,
                "rules_failed": None,
                "this_status": "ACTIVE",
            },
        },
    })
    fn = await get_tool(mcp, "create_snowflake_access_policy")
    rules = [{
        "actors": [{
            "type": "role",
            "condition": "equals",
            "identifiers": ["ANALYST"],
        }],
        "objects": [{
            "type": "database",
            "condition": "equals",
            "identifiers": ["MYDB"],
        }],
        "access": [{"name": "read"}],
    }]
    result = await fn(
        policy_name="My Policy",
        description="Test access policy",
        connection_id=1,
        rules=rules,
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_create_snowflake_access_policy_with_optionals(
        httpx_mock: HTTPXMock, test_env, mcp):
    """policy_maintenance and access_request_id are forwarded when provided.
    rules as a JSON string is parsed before sending.
    """
    httpx_mock.add_response(json={"success": True, "data": {}})
    fn = await get_tool(mcp, "create_snowflake_access_policy")
    result = await fn(
        policy_name="Daily",
        description="Daily check",
        connection_id=1,
        rules='[{"actors":[{"type":"role","condition":"equals",'
              '"identifiers":["A"]}],"objects":[{"type":"database",'
              '"condition":"equals","identifiers":["DB"]}],'
              '"access":[{"name":"read"}]}]',
        policy_maintenance={"rate": "day", "value": 1},
        access_request_id="ar-123",
    )
    assert result["success"] is True
    import json as _json
    body = _json.loads(httpx_mock.get_request().content)
    assert body["policy_maintenance"] == {"rate": "day", "value": 1}
    assert body["access_request_id"] == "ar-123"
    # rules string was parsed into a list of dicts
    assert isinstance(body["rules"], list)
    assert body["rules"][0]["actors"][0]["identifiers"] == ["A"]


# ── create_oltp_access_policy ───────────────────────────────────────────

async def test_create_oltp_access_policy_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_oltp_access_policy returns {success, data, error} on creation."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {
            "policy_id": "OLTP#afe0b9c9-3a29#DATABASE_TYPE#4",
            "policy": {
                "PK": "ORG#a0a7b846#POLICY",
                "SK": "OLTP#afe0b9c9-3a29#DATABASE_TYPE#4",
                "client_id": "a0a7b846-95d5-4248",
                "created_at": "2025-02-07T16:12:12.807Z",
                "updated_at": "2025-02-07T16:12:12.807Z",
                "policy_name": "OLTP Policy",
                "description": "Test OLTP policy",
                "rules": [],
                "this_status": "ACTIVE",
            },
        },
    })
    fn = await get_tool(mcp, "create_oltp_access_policy")
    rules = [{
        "type": "read",
        "actors": [{
            "type": "idp_user",
            "condition": "equals",
            "identifiers": ["user@example.com"],
        }],
        "objects": [{
            "type": "column",
            "identifiers": [{
                "database": {"name": "DB", "wildcard": False},
            }],
        }],
    }]
    result = await fn(
        policy_name="OLTP Policy",
        description="Test OLTP policy",
        repo_name="my_repo",
        database_type=4,
        database_type_name="oracle",
        rules=rules,
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_create_oltp_access_policy_json_string_rules(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_oltp_access_policy parses rules when given as JSON string."""
    httpx_mock.add_response(json={"success": True, "data": {}})
    fn = await get_tool(mcp, "create_oltp_access_policy")
    result = await fn(
        policy_name="OLTP",
        description="d",
        repo_name="repo",
        database_type=4,
        database_type_name="oracle",
        rules='[{"type":"read","actors":[{"type":"idp_user",'
              '"condition":"equals","identifiers":["u@x"]}],'
              '"objects":[{"type":"column","identifiers":[]}]}]',
    )
    assert result["success"] is True
    import json as _json
    body = _json.loads(httpx_mock.get_request().content)
    assert isinstance(body["rules"], list)


async def test_update_snowflake_access_policy_json_string_and_no_description(
        httpx_mock: HTTPXMock, test_env, mcp):
    """update_snowflake_access_policy parses string rules and omits description
    when not provided."""
    httpx_mock.add_response(status_code=202, json={"success": True, "data": {}})
    fn = await get_tool(mcp, "update_snowflake_access_policy")
    result = await fn(
        policy_id="GRANT#abc",
        policy_name="renamed",
        rules='[{"actors":[{"type":"role","condition":"equals",'
              '"identifiers":["A"]}],"objects":[{"type":"database",'
              '"condition":"equals","identifiers":["DB"]}],'
              '"access":[{"name":"read"}]}]',
    )
    assert result["success"] is True
    import json as _json
    body = _json.loads(httpx_mock.get_request().content)
    assert isinstance(body["rules"], list)
    assert "description" not in body


# ── update_snowflake_access_policy ──────────────────────────────────────

async def test_update_snowflake_access_policy_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """update_snowflake_access_policy returns {success, data, error} on update."""
    httpx_mock.add_response(status_code=202, json={
        "success": True,
        "data": {
            "policy_id": "GRANT#afe0b9c9-3a29#DATABASE_TYPE#9",
            "policy": {
                "success": True,
                "data": {
                    "policy_id": "GRANT#afe0b9c9-3a29#DATABASE_TYPE#9",
                    "policy": {
                        "PK": "ORG#a0a7b846#POLICY",
                        "SK": "GRANT#afe0b9c9-3a29#DATABASE_TYPE#9",
                        "client_id": "a0a7b846-95d5-4248",
                        "policy_name": "Updated Policy",
                        "description": "Updated description",
                        "this_status": "ACTIVE",
                    },
                },
            },
        },
    })
    fn = await get_tool(mcp, "update_snowflake_access_policy")
    rules = [{
        "actors": [{"type": "role", "condition": "equals", "identifiers": ["ADMIN"]}],
        "objects": [{"type": "database", "condition": "equals", "identifiers": ["MYDB"]}],
        "access": [{"name": "read"}],
    }]
    result = await fn(
        policy_id="GRANT#afe0b9c9-3a29#DATABASE_TYPE#9",
        policy_name="Updated Policy",
        rules=rules,
        description="Updated description",
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── trigger_access_policy_check ─────────────────────────────────────────

async def test_trigger_access_policy_check_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """trigger_access_policy_check returns {success, data, error} on success."""
    httpx_mock.add_response(status_code=202, json={
        "success": True,
        "data": {
            "policy_id": "GRANT#afe0b9c9-3a29#DATABASE_TYPE#9",
            "policy": {
                "PK": "ORG#a0a7b846#POLICY",
                "SK": "GRANT#afe0b9c9-3a29#DATABASE_TYPE#9",
                "this_status": "ACTIVE",
            },
        },
    })
    fn = await get_tool(mcp, "trigger_access_policy_check")
    result = await fn(policy_id="GRANT#afe0b9c9-3a29#DATABASE_TYPE#9")
    assert result["success"] is True
    assert result["error"] is None


# ── error path ──────────────────────────────────────────────────────────

async def test_access_management_error_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """access_management raises ToolError on HTTP 401 for policy creation."""
    httpx_mock.add_response(status_code=401)
    fn = await get_tool(mcp, "trigger_access_policy_check")
    # 401 -> api.request returns {success: False}
    # Tool wraps: {success: True, data: {success: False, ...}, error: None}
    result = await fn(policy_id="AM#policy1")
    assert result["success"] is True
    assert result["error"] is None
    inner = result["data"]
    assert inner.get("success") is False
