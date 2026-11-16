"""Integration tests for audit report tools (altr_mcp/tools/audit_report.py).

Tests the audit report tools using pytest-httpx to mock HTTP responses.
"""
import json
import re

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pytest_httpx import HTTPXMock

from altr_mcp.tools.audit_report import UNSCOPED_SNOWFLAKE, register
from tests.integration.conftest import get_tool

DEF_ID = "def-abc123"
INST_ID = "inst-xyz789"
COMMENT_ID = "cmt-001"
AR = "https://test-org.audit-report.live.altr.com/v1/audit-reports/definitions"
SC = "https://test-org.sc-control.live.altr.com/v1"
DATABASES = re.compile(r"https://altrnet\.live\.altr\.com/api/databases\?.*")
INSTANCES = re.compile(re.escape(f"{AR}/{DEF_ID}/instances/") + r"\?.*")
EMAIL = {"channels": [{"type": "email", "recipients": ["a@example.com"],
                       "enabled": True}]}


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


def _sent(httpx_mock, method):
    return json.loads(next(
        r for r in httpx_mock.get_requests() if r.method == method).content)


def _methods(httpx_mock):
    return [r.method for r in httpx_mock.get_requests()]


def _instances(httpx_mock, *statuses):
    httpx_mock.add_response(method="GET", url=INSTANCES, json={
        "items": [{"instance_id": f"i{n}", "status": s}
                  for n, s in enumerate(statuses)], "has_more": False})


def _instance(httpx_mock, **fields):
    instance = {"instance_id": INST_ID, "status": "generated",
                "required_approvals": 1, "sign_off_count": 0, **fields}
    httpx_mock.add_response(method="GET", url=f"{AR}/{DEF_ID}/instances/{INST_ID}",
                            json=instance)


def _stored(httpx_mock, **fields):
    definition = {
        "definition_id": DEF_ID, "name": "Daily", "description": "d",
        "integration_type": "oltp", "retention_days": 365,
        "required_approvals": 2,
        "report_window": {"lookback_days": 7, "timezone": "America/New_York"},
        "schedule": {"cron": "0 9 * * ? *", "enabled": False,
                     "timezone": "America/New_York"},
        "delivery": EMAIL,
        "filters": {"filter_groups": [{"filters": [
            {"field": "repo_name", "mode": "include",
             "patterns": [{"match_type": "exact", "value": "pg"}]},
            {"field": "repo_type", "mode": "include",
             "patterns": [{"match_type": "exact", "value": "POSTGRES"}]},
            {"field": "consuming_user", "mode": "include",
             "patterns": [{"match_type": "exact", "value": "bob"}]},
            {"field": "row_count", "range": {"min": 10}},
        ]}]},
        **fields,
    }
    httpx_mock.add_response(method="GET", url=f"{AR}/{DEF_ID}", json=definition)
    return definition


def _create_args(**overrides):
    return {"name": "Daily", "integration_type": "oltp",
            "timezone": "America/New_York", "schedule_cron": "0 9 * * ? *",
            "required_approvals": 1, "recipients": ["a@example.com"],
            **overrides}


# ── list ─────────────────────────────────────────────────────────────────────

async def test_list_report_definitions_sends_paging_and_archived(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"items": [], "has_more": False})
    fn = await get_tool(mcp, "list_report_definitions")
    result = await fn(archived=True, limit=10, cursor="c2")
    assert result["success"] is True
    url = str(httpx_mock.get_request().url)
    assert "archived=true" in url and "limit=10" in url and "cursor=c2" in url


@pytest.mark.parametrize("tool", [
    "list_report_definitions", "list_report_instances",
    "list_report_comments", "list_report_sign_offs"])
async def test_list_refuses_limit_above_api_cap(
        httpx_mock: HTTPXMock, test_env, mcp, tool):
    fn = await get_tool(mcp, tool)
    args = {"limit": 101}
    if tool != "list_report_definitions":
        args["definition_id"] = DEF_ID
    if tool in ("list_report_comments", "list_report_sign_offs"):
        args["instance_id"] = INST_ID
    with pytest.raises(ToolError, match="limit must be 1-100"):
        await fn(**args)
    assert httpx_mock.get_requests() == []


# ── create_report_definition ─────────────────────────────────────────────────

async def test_create_oltp_builds_the_console_body(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", url=f"{SC}/repos/pg",
                            json={"name": "pg", "type": "POSTGRES"})
    httpx_mock.add_response(method="POST", json={"definition_id": DEF_ID})
    fn = await get_tool(mcp, "create_report_definition")
    result = await fn(**_create_args(
        repo_names=["pg"], description="nightly",
        filters=[{"field": "statement_type", "operator": "is", "values": ["select", "delete"]},
                 {"field": "consuming_user", "operator": "does_not_contain", "values": ["svc_"]},
                 {"field": "execution_success", "operator": "is_not", "values": [True]}]))
    assert result["data"] == {"definition_id": DEF_ID}
    assert "warning" not in result
    assert _sent(httpx_mock, "POST") == {
        "name": "Daily", "description": "nightly", "integration_type": "oltp",
        "filters": {"filter_groups": [{"filters": [
            {"field": "repo_name", "mode": "include",
             "patterns": [{"match_type": "exact", "value": "pg"}]},
            {"field": "repo_type", "mode": "include",
             "patterns": [{"match_type": "exact", "value": "POSTGRES"}]},
            {"field": "statement_type", "mode": "include",
             "patterns": [{"match_type": "exact", "value": "SELECT"},
                          {"match_type": "exact", "value": "DELETE"}]},
            {"field": "consuming_user", "mode": "exclude",
             "patterns": [{"match_type": "contains", "value": "svc_"}]},
            {"field": "execution_success", "mode": "exclude", "value": True},
        ]}]},
        "retention_days": 90,
        "schedule": {"cron": "0 9 * * ? *", "enabled": True,
                     "timezone": "America/New_York"},
        "report_window": {"lookback_days": 7, "timezone": "America/New_York"},
        "required_approvals": 1,
        "delivery": EMAIL,
    }


async def test_create_without_filters_sends_no_groups(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="POST", json={"definition_id": DEF_ID})
    fn = await get_tool(mcp, "create_report_definition")
    await fn(**_create_args(schedule_enabled=False, lookback_days=30))
    body = _sent(httpx_mock, "POST")
    assert body["filters"] == {"filter_groups": []}
    assert body["description"] == ""
    assert body["schedule"]["enabled"] is False
    assert body["report_window"]["lookback_days"] == 30


async def test_create_snowflake_scopes_by_database_id(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", url=DATABASES, json={
        "data": {"databases": [{"id": 11}, {"id": 12}], "count": 2}, "success": True})
    httpx_mock.add_response(method="POST", json={"definition_id": DEF_ID})
    fn = await get_tool(mcp, "create_report_definition")
    result = await fn(**_create_args(
        integration_type="snowflake", database_ids=[12],
        filters=[{"field": "warehouse", "operator": "is", "values": ["WH"]}]))
    assert "warning" not in result
    assert "databaseType=snowflake_external_functions" in str(
        httpx_mock.get_requests()[0].url)
    assert _sent(httpx_mock, "POST")["filters"]["filter_groups"][0]["filters"] == [
        {"field": "database_id", "mode": "include",
         "patterns": [{"match_type": "exact", "value": "12"}]},
        {"field": "warehouse", "mode": "include",
         "patterns": [{"match_type": "exact", "value": "WH"}]},
    ]


async def test_create_unscoped_snowflake_warns(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="POST", json={"definition_id": DEF_ID})
    fn = await get_tool(mcp, "create_report_definition")
    result = await fn(**_create_args(integration_type="snowflake"))
    assert result["warning"] == UNSCOPED_SNOWFLAKE


async def test_create_refuses_an_unknown_snowflake_database(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", url=DATABASES, json={
        "data": {"databases": [{"id": 11}], "count": 1}, "success": True})
    fn = await get_tool(mcp, "create_report_definition")
    with pytest.raises(ToolError, match="No connected Snowflake database has id 99"):
        await fn(**_create_args(integration_type="snowflake", database_ids=[99]))
    assert "POST" not in _methods(httpx_mock)


async def test_create_refuses_an_unreadable_repo(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", url=f"{SC}/repos/nope", status_code=404)
    fn = await get_tool(mcp, "create_report_definition")
    with pytest.raises(ToolError, match="Could not read repo 'nope'"):
        await fn(**_create_args(repo_names=["nope"]))
    assert "POST" not in _methods(httpx_mock)


@pytest.mark.parametrize("overrides, error", [
    ({"lookback_days": 5}, "lookback_days must be one of"),
    ({"required_approvals": 6}, "required_approvals must be 0-5"),
    ({"schedule_cron": "0 9 * * *"}, "needs 6 fields"),
    ({"schedule_cron": "0 9 * * * *"}, "exactly one of day-of-month"),
    ({"schedule_cron": "0 9 ? * ? *"}, "exactly one of day-of-month"),
    ({"timezone": "Local"}, "Unknown timezone"),
    ({"integration_type": "databricks"}, "integration_type must be"),
    ({"recipients": []}, "at least one email"),
    ({"recipients": [f"u{n}@example.com" for n in range(21)]}, "at most 20"),
    ({"database_ids": [1]}, "database_ids scopes Snowflake"),
    ({"filters": [{"field": "repo_name", "operator": "is", "values": ["x"]}]},
     "Scope the report with repo_names"),
    ({"filters": [{"field": "policy_blocked", "operator": "is", "values": ["x"]}]},
     "not a oltp filter field"),
    ({"filters": [{"field": "username", "operator": "is", "values": ["x"]}]},
     "not a oltp filter field"),
    ({"filters": [{"field": "table_name", "operator": "starts_with", "values": ["x"]}]},
     "operator must be one of"),
    ({"filters": [{"field": "table_name", "operator": "is", "values": [" "]}]},
     "non-blank"),
    ({"filters": [{"field": "statement_type", "operator": "is", "values": ["FOO"]}]},
     "statement_type values must be among"),
    ({"filters": [{"field": "event_name", "operator": "is", "values": ["LOGIN"]}]},
     "event_name values must be among"),
    ({"filters": [{"field": "execution_success", "operator": "contains",
                   "values": ["true"]}]}, "execution_success takes one filter"),
    ({"filters": "not json"}, "filters is not valid JSON"),
])
async def test_create_refuses_what_the_console_cant_build(
        httpx_mock: HTTPXMock, test_env, mcp, overrides, error):
    fn = await get_tool(mcp, "create_report_definition")
    with pytest.raises(ToolError, match=error):
        await fn(**_create_args(**overrides))
    assert httpx_mock.get_requests() == []


async def test_create_refuses_database_id_filter_on_snowflake(
        httpx_mock: HTTPXMock, test_env, mcp):
    fn = await get_tool(mcp, "create_report_definition")
    with pytest.raises(ToolError, match="Scope the report with database_ids"):
        await fn(**_create_args(integration_type="snowflake", filters=[
            {"field": "database_id", "operator": "is_not", "values": ["1"]}]))


# ── update_report_definition ─────────────────────────────────────────────────

async def test_update_changes_only_what_is_passed(
        httpx_mock: HTTPXMock, test_env, mcp):
    stored = _stored(httpx_mock)
    _instances(httpx_mock, "generated", "failed")
    httpx_mock.add_response(method="PUT", json={"definition_id": DEF_ID})
    fn = await get_tool(mcp, "update_report_definition")
    result = await fn(definition_id=DEF_ID, name="Renamed")
    assert "warning" not in result
    assert _sent(httpx_mock, "PUT") == {
        "name": "Renamed", "description": "d", "integration_type": "oltp",
        "filters": stored["filters"], "retention_days": 365,
        "schedule": stored["schedule"], "report_window": stored["report_window"],
        "required_approvals": 2, "delivery": EMAIL,
    }


async def test_update_timezone_moves_window_and_schedule(
        httpx_mock: HTTPXMock, test_env, mcp):
    _stored(httpx_mock)
    _instances(httpx_mock)
    httpx_mock.add_response(method="PUT", json={})
    fn = await get_tool(mcp, "update_report_definition")
    await fn(definition_id=DEF_ID, timezone="Europe/London",
             schedule_enabled=True, required_approvals=0,
             recipients=["b@example.com"])
    body = _sent(httpx_mock, "PUT")
    assert body["report_window"] == {"lookback_days": 7, "timezone": "Europe/London"}
    assert body["schedule"] == {"cron": "0 9 * * ? *", "enabled": True,
                                "timezone": "Europe/London"}
    assert body["required_approvals"] == 0
    assert body["delivery"]["channels"][0]["recipients"] == ["b@example.com"]


async def test_update_filters_keep_scope_and_unmodeled_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    _stored(httpx_mock)
    _instances(httpx_mock)
    httpx_mock.add_response(method="PUT", json={})
    fn = await get_tool(mcp, "update_report_definition")
    await fn(definition_id=DEF_ID, filters=[
        {"field": "table_name", "operator": "contains", "values": ["pay"]}])
    group = _sent(httpx_mock, "PUT")["filters"]["filter_groups"][0]["filters"]
    assert [f["field"] for f in group] == [
        "repo_name", "repo_type", "row_count", "table_name"]


async def test_update_repo_names_keep_field_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    _stored(httpx_mock)
    _instances(httpx_mock)
    httpx_mock.add_response(method="GET", url=f"{SC}/repos/my", json={"type": "MYSQL"})
    httpx_mock.add_response(method="PUT", json={})
    fn = await get_tool(mcp, "update_report_definition")
    await fn(definition_id=DEF_ID, repo_names=["my"])
    group = _sent(httpx_mock, "PUT")["filters"]["filter_groups"][0]["filters"]
    assert group[:2] == [
        {"field": "repo_name", "mode": "include",
         "patterns": [{"match_type": "exact", "value": "my"}]},
        {"field": "repo_type", "mode": "include",
         "patterns": [{"match_type": "exact", "value": "MYSQL"}]}]
    assert [f["field"] for f in group[2:]] == ["consuming_user", "row_count"]


async def test_update_clearing_snowflake_scope_warns(
        httpx_mock: HTTPXMock, test_env, mcp):
    _stored(httpx_mock, integration_type="snowflake", filters={"filter_groups": [
        {"filters": [{"field": "database_id", "mode": "include",
                      "patterns": [{"match_type": "exact", "value": "12"}]}]}]})
    _instances(httpx_mock)
    httpx_mock.add_response(method="PUT", json={})
    fn = await get_tool(mcp, "update_report_definition")
    result = await fn(definition_id=DEF_ID, database_ids=[])
    assert result["warning"] == UNSCOPED_SNOWFLAKE
    assert _sent(httpx_mock, "PUT")["filters"] == {"filter_groups": []}


async def test_update_keeps_several_filter_groups_untouched(
        httpx_mock: HTTPXMock, test_env, mcp):
    groups = {"filter_groups": [{"filters": []}, {"filters": []}]}
    _stored(httpx_mock, filters=groups)
    _instances(httpx_mock)
    httpx_mock.add_response(method="PUT", json={})
    fn = await get_tool(mcp, "update_report_definition")
    await fn(definition_id=DEF_ID, description="")
    body = _sent(httpx_mock, "PUT")
    assert body["filters"] == groups
    assert body["description"] == ""


async def test_update_refuses_filters_on_several_groups(
        httpx_mock: HTTPXMock, test_env, mcp):
    _stored(httpx_mock, filters={"filter_groups": [{"filters": []}, {"filters": []}]})
    fn = await get_tool(mcp, "update_report_definition")
    with pytest.raises(ToolError, match="has 2 filter groups"):
        await fn(definition_id=DEF_ID, filters=[])
    assert "PUT" not in _methods(httpx_mock)


async def test_update_refuses_while_generating(
        httpx_mock: HTTPXMock, test_env, mcp):
    _stored(httpx_mock)
    _instances(httpx_mock, "in_progress")
    fn = await get_tool(mcp, "update_report_definition")
    with pytest.raises(ToolError, match="while a report is generating"):
        await fn(definition_id=DEF_ID, name="x")
    assert "PUT" not in _methods(httpx_mock)


@pytest.mark.parametrize("stored, error", [
    ({"delivery": None}, "has no email recipients"),
    ({"schedule": None}, "has no schedule"),
])
async def test_update_needs_what_the_console_requires(
        httpx_mock: HTTPXMock, test_env, mcp, stored, error):
    _stored(httpx_mock, **stored)
    _instances(httpx_mock)
    fn = await get_tool(mcp, "update_report_definition")
    with pytest.raises(ToolError, match=error):
        await fn(definition_id=DEF_ID, name="x")
    assert "PUT" not in _methods(httpx_mock)


async def test_update_stops_when_the_read_fails(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", url=f"{AR}/{DEF_ID}", status_code=404)
    fn = await get_tool(mcp, "update_report_definition")
    with pytest.raises(ToolError, match=f"Could not read definition {DEF_ID}"):
        await fn(definition_id=DEF_ID, name="x")


# ── archive / restore / trigger ──────────────────────────────────────────────

async def test_archive_and_restore(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="DELETE", url=f"{AR}/{DEF_ID}", json={})
    httpx_mock.add_response(method="POST", url=f"{AR}/{DEF_ID}/restore", json={})
    await (await get_tool(mcp, "archive_report_definition"))(definition_id=DEF_ID)
    await (await get_tool(mcp, "restore_report_definition"))(definition_id=DEF_ID)
    assert _methods(httpx_mock) == ["DELETE", "POST"]


async def test_trigger_returns_the_instance(httpx_mock: HTTPXMock, test_env, mcp):
    _instances(httpx_mock, "generated")
    httpx_mock.add_response(method="POST", url=f"{AR}/{DEF_ID}/trigger",
                            status_code=202, json={"instance_id": INST_ID})
    fn = await get_tool(mcp, "trigger_report_definition")
    result = await fn(definition_id=DEF_ID)
    assert result["data"] == {"instance_id": INST_ID}


async def test_trigger_refuses_while_generating(
        httpx_mock: HTTPXMock, test_env, mcp):
    _instances(httpx_mock, "generating")
    fn = await get_tool(mcp, "trigger_report_definition")
    with pytest.raises(ToolError, match="Can't trigger"):
        await fn(definition_id=DEF_ID)
    assert "POST" not in _methods(httpx_mock)


async def test_trigger_cooldown_is_not_retried(
        httpx_mock: HTTPXMock, retry_env, mcp):
    _instances(httpx_mock)
    httpx_mock.add_response(method="POST", url=f"{AR}/{DEF_ID}/trigger",
                            status_code=429, headers={"Retry-After": "300"},
                            json={"error": {"message": "cooldown"}})
    fn = await get_tool(mcp, "trigger_report_definition")
    result = await fn(definition_id=DEF_ID)
    assert _methods(httpx_mock) == ["GET", "POST"]
    assert result["data"]["status_code"] == 429
    assert "last 5 minutes" in result["data"]["message"]


# ── instances ────────────────────────────────────────────────────────────────

async def test_instance_reads(httpx_mock: HTTPXMock, test_env, mcp):
    _instances(httpx_mock)
    _instance(httpx_mock)
    httpx_mock.add_response(method="GET", json={"url": "https://s3/x"})
    await (await get_tool(mcp, "list_report_instances"))(definition_id=DEF_ID, limit=5)
    await (await get_tool(mcp, "get_report_instance"))(
        definition_id=DEF_ID, instance_id=INST_ID)
    result = await (await get_tool(mcp, "get_report_instance_download_url"))(
        definition_id=DEF_ID, instance_id=INST_ID, format="csv")
    assert result["data"] == {"url": "https://s3/x"}
    assert "format=csv" in str(httpx_mock.get_requests()[-1].url)


# ── comments and sign-offs ───────────────────────────────────────────────────

async def test_create_comment_on_an_open_instance(
        httpx_mock: HTTPXMock, test_env, mcp):
    _instance(httpx_mock)
    httpx_mock.add_response(method="POST", json={"comment_id": COMMENT_ID})
    fn = await get_tool(mcp, "create_report_comment")
    result = await fn(definition_id=DEF_ID, instance_id=INST_ID, text="Looks right")
    assert result["data"] == {"comment_id": COMMENT_ID}
    assert _sent(httpx_mock, "POST") == {"text": "Looks right"}


async def test_pin_and_unpin_on_an_open_instance(
        httpx_mock: HTTPXMock, test_env, mcp):
    _instance(httpx_mock)
    _instance(httpx_mock)
    base = f"{AR}/{DEF_ID}/instances/{INST_ID}/comments/{COMMENT_ID}"
    httpx_mock.add_response(method="POST", url=f"{base}/pin", json={})
    httpx_mock.add_response(method="POST", url=f"{base}/unpin", json={})
    args = {"definition_id": DEF_ID, "instance_id": INST_ID, "comment_id": COMMENT_ID}
    await (await get_tool(mcp, "pin_report_comment"))(**args)
    await (await get_tool(mcp, "unpin_report_comment"))(**args)


async def test_sign_off_sends_the_console_body(
        httpx_mock: HTTPXMock, test_env, mcp):
    _instance(httpx_mock, required_approvals=2, sign_off_count=1)
    httpx_mock.add_response(method="POST", json={"sign_off": {}})
    fn = await get_tool(mcp, "create_report_sign_off")
    await fn(definition_id=DEF_ID, instance_id=INST_ID)
    assert _sent(httpx_mock, "POST") == {
        "action": "approve", "attestation": True, "comments": ""}


@pytest.mark.parametrize("tool, args", [
    ("create_report_comment", {"text": "x"}),
    ("pin_report_comment", {"comment_id": COMMENT_ID}),
    ("unpin_report_comment", {"comment_id": COMMENT_ID}),
    ("create_report_sign_off", {}),
])
@pytest.mark.parametrize("instance, error", [
    ({"required_approvals": 0}, "needs no approvals"),
    ({"status": "finalizing"}, "is finalizing"),
    ({"status": "finalized"}, "is finalized"),
    ({"required_approvals": 2, "sign_off_count": 2}, "is fully approved"),
])
async def test_closed_instances_take_no_comments_or_sign_offs(
        httpx_mock: HTTPXMock, test_env, mcp, tool, args, instance, error):
    _instance(httpx_mock, **instance)
    fn = await get_tool(mcp, tool)
    with pytest.raises(ToolError, match=error):
        await fn(definition_id=DEF_ID, instance_id=INST_ID, **args)
    assert _methods(httpx_mock) == ["GET"]


async def test_comment_on_an_unknown_instance_is_refused(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", status_code=404)
    fn = await get_tool(mcp, "create_report_comment")
    with pytest.raises(ToolError, match=f"Could not read instance {INST_ID}"):
        await fn(definition_id=DEF_ID, instance_id=INST_ID, text="x")


async def test_sign_off_and_comment_reads(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"sign_off": None})
    httpx_mock.add_response(json={"items": [], "has_more": False})
    httpx_mock.add_response(json={"items": [], "has_more": False})
    args = {"definition_id": DEF_ID, "instance_id": INST_ID}
    result = await (await get_tool(mcp, "get_report_sign_off"))(**args)
    assert result["data"] == {"sign_off": None}
    await (await get_tool(mcp, "list_report_sign_offs"))(**args, cursor="c")
    await (await get_tool(mcp, "list_report_comments"))(**args, limit=100)
    urls = [str(r.url) for r in httpx_mock.get_requests()]
    assert urls[1].endswith("/sign_offs?cursor=c")
    assert "limit=100" in urls[2]
