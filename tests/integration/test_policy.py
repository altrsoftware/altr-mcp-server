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


async def test_create_policy_databricks_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_policy for Databricks sends database_ids as a list and PUSHDOWN type."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {
            "policy_id": "TAG#PAC_ACCESS_LEVEL",
        },
    })
    fn = await get_tool(mcp, "create_policy")
    result = await fn(
        tag="PAC_ACCESS_LEVEL",
        policy_type="PUSHDOWN",
        database_ids=[2167],
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result

    # Verify the API request actually carried type=PUSHDOWN and
    # database_ids=[2167] — the two Databricks-required fields.
    request = httpx_mock.get_request()
    import json as _json
    body = _json.loads(request.content)
    assert body.get("type") == "PUSHDOWN"
    assert body.get("database_ids") == [2167]


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


async def test_update_rule_all_simple_fields(
        httpx_mock: HTTPXMock, test_env, mcp):
    """update_rule forwards masking_policy, role, and tag_value."""
    httpx_mock.add_response(status_code=204, json={"success": True})
    fn = await get_tool(mcp, "update_rule")
    result = await fn(
        policy_id="TAG#p1",
        rule_id="r1",
        masking_policy=10003,
        role="ANALYST",
        tag_value="PII_SSN",
    )
    assert result["success"] is True
    import json as _json
    body = _json.loads(httpx_mock.get_request().content)
    assert body == {
        "masking_policy": 10003,
        "role": "ANALYST",
        "tag_value": "PII_SSN",
    }


async def test_update_rule_threshold_scalars_normalized(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Single threshold dicts are wrapped to lists before validation."""
    httpx_mock.add_response(status_code=204, json={"success": True})
    fn = await get_tool(mcp, "update_rule")
    result = await fn(
        policy_id="TAG#p1",
        rule_id="r1",
        access_rate_thresholds={
            "access_rate_unit": "minute",
            "access_rate_limit": 10,
            "action": "block",
        },
        time_window_thresholds={
            "day": ["MONDAY"],
            "start_time": {"hour": 9, "minute": 0},
            "end_time": {"hour": 17, "minute": 0},
            "timezone": "UTC",
            "action": "block",
        },
    )
    assert result["success"] is True
    import json as _json
    body = _json.loads(httpx_mock.get_request().content)
    assert isinstance(body["access_rate_thresholds"], list)
    assert len(body["access_rate_thresholds"]) == 1
    assert isinstance(body["time_window_thresholds"], list)
    assert len(body["time_window_thresholds"]) == 1


async def test_update_rule_invalid_access_rate_threshold_raises(
        test_env, mcp):
    """Malformed access_rate_thresholds surface a ValueError."""
    fn = await get_tool(mcp, "update_rule")
    with pytest.raises((ToolError, ValueError)):
        await fn(
            policy_id="TAG#p1",
            rule_id="r1",
            access_rate_thresholds=[{"bad": "value"}],
        )


async def test_update_rule_invalid_time_window_threshold_raises(
        test_env, mcp):
    """Malformed time_window_thresholds surface a ValueError."""
    fn = await get_tool(mcp, "update_rule")
    with pytest.raises((ToolError, ValueError)):
        await fn(
            policy_id="TAG#p1",
            rule_id="r1",
            time_window_thresholds=[{"missing": "fields"}],
        )


async def test_add_rules_json_string_form(httpx_mock: HTTPXMock, test_env, mcp):
    """add_rules accepts rules as a JSON string and parses it."""
    httpx_mock.add_response(json={"success": True})
    fn = await get_tool(mcp, "add_rules")
    result = await fn(
        policy_id="TAG#p1",
        rules='[{"masking_policy": 10001, "role": "X", "tag_value": "V"}]',
    )
    assert result["success"] is True


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


# ── invalid JSON / 5xx retry ─────────────────────────────────────────────────

async def test_policy_invalid_json_response(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(
        content=b"<html>Bad Gateway</html>",
        headers={"Content-Type": "text/html"},
    )
    fn = await get_tool(mcp, "delete_policy")
    result = await fn(policy_id="test-policy-id")
    assert result["success"] is True
    assert "raw" in result["data"]


async def test_policy_5xx_retry_exhaustion(
        httpx_mock: HTTPXMock, retry_env, mcp):
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    fn = await get_tool(mcp, "delete_policy")
    result = await fn(policy_id="test-policy-id")
    assert result["success"] is True
    assert result["data"]["success"] is False
    assert "Retry exhausted" in result["data"]["message"]
