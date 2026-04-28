"""Integration tests for policy tools (altr_mcp/tools/policy.py).

Tests each of the 8 policy tools using pytest-httpx to mock HTTP responses.
Verifies the {success, data, error} response shape for happy paths.
"""
import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pytest_httpx import HTTPXMock

from altr_mcp.tools.policy import register
from tests.integration.conftest import get_tool


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


# ── get_policies ────────────────────────────────────────────────────────

async def test_get_policies_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """get_policies without policy_type queries all 7 types and merges."""
    # TAG type returns one policy
    tag_response = {
        "success": True,
        "data": {
            "policies": [
                {
                    "policy_id": "TAG#p1",
                    "name": "p1",
                    "this_status": "SUCCESS",
                    "metadata": {
                        "updated_at": "2025-02-07T16:12:12.807Z",
                        "roles": ["ANALYST"],
                    },
                }
            ],
            "last_evaluated_key": None,
            "count": 1,
        },
    }
    # All other types return empty
    empty_response = {
        "success": True,
        "data": {"policies": [], "last_evaluated_key": None, "count": 0},
    }
    # 7 responses: TAG, COLUMN, PUSHDOWN, IMPERSONATION, GRANT, ROW, OLTP
    httpx_mock.add_response(json=tag_response)
    for _ in range(6):
        httpx_mock.add_response(json=empty_response)
    fn = await get_tool(mcp, "get_policies")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result
    # Should have merged the one TAG policy
    policies = result["data"]["data"]["policies"]
    assert len(policies) == 1
    assert policies[0]["policy_id"] == "TAG#p1"


async def test_get_policies_with_filter(httpx_mock: HTTPXMock, test_env, mcp):
    """get_policies with policy_type filter passes param and returns data."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {
            "policies": [
                {
                    "policy_id": "TAG#p2",
                    "name": "p2",
                    "this_status": "SUCCESS",
                    "metadata": {
                        "updated_at": "2025-02-07T16:12:12.807Z",
                        "roles": ["ADMIN"],
                    },
                }
            ],
            "last_evaluated_key": None,
            "count": 1,
        },
    })
    fn = await get_tool(mcp, "get_policies")
    result = await fn(policy_type="TAG")
    assert result["success"] is True
    assert result["error"] is None


async def test_get_policies_error_path(httpx_mock: HTTPXMock, test_env, mcp):
    """get_policies with specific type returns empty on 404."""
    httpx_mock.add_response(status_code=404)
    fn = await get_tool(mcp, "get_policies")
    # With policy_type specified, only 1 API call
    # 404 -> api.request returns {success: False} dict (no "data" key)
    # Pagination util does .get("data", {}).get("policies", []) -> empty list
    result = await fn(policy_type="TAG")
    assert result["success"] is True
    assert result["error"] is None


# ── get_rules ───────────────────────────────────────────────────────────

async def test_get_rules_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """get_rules returns {success, data, error} with rules data."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {
            "count": 1,
            "items": {
                "9417c2bc077fda72CREDIT_CARD": [
                    {
                        "rule_id": "r1",
                        "rule_hash": "9417c2bc077fda72CREDIT_CARD",
                        "pending_rule_json": {},
                        "success_rule_json": {"masking_policy": "10001"},
                        "failed_rule_json": {},
                        "policy_id": "TAG#p1",
                        "role": "ANALYST",
                        "tag_value": "PII",
                        "updated_at": "2023-10-01T12:00:00Z",
                    }
                ]
            },
            "last_evaluated_key": None,
        },
    })
    fn = await get_tool(mcp, "get_rules")
    result = await fn(policy_id="TAG#p1")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── create_policy ───────────────────────────────────────────────────────

async def test_create_policy_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """create_policy returns {success, data, error} with new policy_id."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {
            "policy_id": "TAG#MY_TAG",
        },
    })
    fn = await get_tool(mcp, "create_policy")
    result = await fn(tag="MY_TAG")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── add_rules ───────────────────────────────────────────────────────────

async def test_add_rules_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """add_rules batches rules and returns list of batch responses."""
    httpx_mock.add_response(json={"success": True})
    fn = await get_tool(mcp, "add_rules")
    rules = [{"masking_policy": 10001, "role": "ANALYST", "tag_value": "PII"}]
    result = await fn(policy_id="TAG#p1", rules=rules)
    assert result["success"] is True
    assert result["error"] is None


async def test_add_rules_validates_input(test_env, mcp):
    """add_rules raises ToolError when rules fail validation."""
    fn = await get_tool(mcp, "add_rules")
    # Invalid rule — missing required fields
    with pytest.raises((ToolError, ValueError)):
        await fn(policy_id="TAG#p1", rules=[{"bad_key": "value"}])


# ── delete_policy ───────────────────────────────────────────────────────

async def test_delete_policy_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """delete_policy returns {success, data, error} on successful deletion."""
    httpx_mock.add_response(status_code=204, json={"success": True})
    fn = await get_tool(mcp, "delete_policy")
    result = await fn(policy_id="TAG#p1")
    assert result["success"] is True
    assert result["error"] is None


# ── update_rule ─────────────────────────────────────────────────────────

async def test_update_rule_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """update_rule returns {success, data, error} on successful update."""
    httpx_mock.add_response(status_code=204, json={
        "success": True, "rule_id": "r1", "role": "ADMIN",
    })
    fn = await get_tool(mcp, "update_rule")
    result = await fn(policy_id="TAG#p1", rule_id="r1", role="ADMIN")
    assert result["success"] is True
    assert result["error"] is None


async def test_update_rule_no_fields_raises(test_env, mcp):
    """update_rule raises when no optional fields provided."""
    fn = await get_tool(mcp, "update_rule")
    with pytest.raises((ToolError, ValueError)):
        await fn(policy_id="TAG#p1", rule_id="r1")


# ── delete_rule ─────────────────────────────────────────────────────────

async def test_delete_rule_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """delete_rule returns {success, data, error} on successful deletion."""
    httpx_mock.add_response(status_code=204, json={"success": True})
    fn = await get_tool(mcp, "delete_rule")
    result = await fn(policy_id="TAG#p1", rule_id="r1")
    assert result["success"] is True
    assert result["error"] is None


# ── get_roles ───────────────────────────────────────────────────────────

async def test_get_roles_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """get_roles returns {success, data, error} with list of role names."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {
            "userGroups": [{"userGroupName": "ANALYST"}, {"userGroupName": "ADMIN"}],
            "count": 2,
        }
    })
    fn = await get_tool(mcp, "get_roles")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result
