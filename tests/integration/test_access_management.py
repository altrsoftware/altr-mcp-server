"""Integration tests for access management tools.

The tools build policies in the shape the console's Access Management Policy
editor builds, so pytest-httpx checks the exact request bodies.
"""
import json

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pytest_httpx import HTTPXMock

from altr_mcp.tools.access_management import register
from tests.integration.conftest import get_tool

BASE = "https://api.live.altr.com/v1/unified-policy/management/policy"
GRANT_ID = "GRANT#afe0b9c9-3a29#DATABASE_TYPE#9"
OLTP_ID = "OLTP#5d1c-77aa#DATABASE_TYPE#4"


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


def _body(httpx_mock: HTTPXMock, method: str) -> dict:
    request = next(r for r in httpx_mock.get_requests() if r.method == method)
    return json.loads(request.content)


async def _call(mcp, name, **kwargs):
    return await (await get_tool(mcp, name))(**kwargs)


# ── create_snowflake_access_policy ──────────────────

async def test_snowflake_policy_on_tables_is_built_like_the_console(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="POST", url=f"{BASE}/accessManagement/snowflake",
                            json={"success": True, "data": {"policy_id": GRANT_ID}})
    result = await _call(
        mcp, "create_snowflake_access_policy", policy_name="Analysts",
        connection_id=7, roles=["ANALYST"], access="read_write",
        object_type="table", database="SALES", schema="PUBLIC",
        names=["ORDERS", "CUSTOMERS"], refresh="monthly", refresh_time="02:30",
        refresh_day="tue", refresh_week=2)

    assert result["success"] is True
    assert _body(httpx_mock, "POST") == {
        "policy_name": "Analysts",
        "connection_ids": [7],
        "rules": [{
            "access": [{"name": "read"}, {"name": "write"}],
            "actors": [{"type": "role", "condition": "equals",
                        "identifiers": ["ANALYST"]}],
            "objects": [{
                "type": "table",
                "condition": "fully_qualified",
                "fully_qualified_identifiers": [
                    {"database": "SALES", "schema": "PUBLIC", "table": "ORDERS"},
                    {"database": "SALES", "schema": "PUBLIC", "table": "CUSTOMERS"},
                ],
            }],
        }],
        "policy_maintenance": {"rate": "cron", "value": "30 2 ? * TUE#2 *"},
    }


async def test_snowflake_policy_on_tag_values_without_a_schedule(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="POST", json={"success": True, "data": {}})
    await _call(
        mcp, "create_snowflake_access_policy", policy_name="PII",
        connection_id=7, roles="AUDITOR", refresh="none",
        tag_check_against="view", tag_database="GOV", tag_schema="TAGS",
        tag_names="PII", tag_values=["EMAIL", "SSN"])

    body = _body(httpx_mock, "POST")
    assert "policy_maintenance" not in body
    assert body["rules"] == [{
        "access": [{"name": "read"}],
        "actors": [{"type": "role", "condition": "equals",
                    "identifiers": ["AUDITOR"]}],
        "tagged_objects": [{
            "check_against": ["views"],
            "tagged_with": [
                {"database": "GOV", "schema": "TAGS", "name": "PII", "value": "EMAIL"},
                {"database": "GOV", "schema": "TAGS", "name": "PII", "value": "SSN"},
            ],
            "tag_condition": "or",
        }],
    }]


@pytest.mark.parametrize("kwargs, message", [
    ({}, "not both"),
    ({"object_type": "database", "names": ["A"], "tag_names": ["T"]}, "not both"),
    ({"object_type": "schema", "names": ["S"]}, "needs database"),
    ({"object_type": "view", "names": ["V"], "database": "D"}, "needs schema"),
    ({"object_type": "column", "names": ["C"]}, "object_type must be"),
    ({"tag_names": ["A", "B"], "tag_values": ["x"], "tag_check_against": "table",
      "tag_database": "D", "tag_schema": "S"}, "exactly one tag name"),
    ({"object_type": "database", "names": [], "refresh": "none"}, "at least one"),
    ({"object_type": "database", "names": ["A"], "refresh": "daily"}, "HH:MM"),
    ({"object_type": "database", "names": ["A"], "refresh": "weekly",
      "refresh_time": "01:00"}, "refresh_day"),
    ({"object_type": "database", "names": ["A"], "refresh": "monthly",
      "refresh_time": "01:00", "refresh_day": "MON", "refresh_week": 5},
     "refresh_week"),
    ({"object_type": "database", "names": ["A"], "access": "admin"}, "access must be"),
])
async def test_snowflake_policy_outside_the_console_shape_is_refused(
        httpx_mock: HTTPXMock, test_env, mcp, kwargs, message):
    args = {"policy_name": "P", "connection_id": 1, "roles": ["R"],
            "refresh": "none", **kwargs}
    with pytest.raises(ToolError, match=message):
        await _call(mcp, "create_snowflake_access_policy", **args)
    assert not httpx_mock.get_requests()


# ── update_snowflake_access_policy ──────────────────

STORED_GRANT = {
    "policy_id": GRANT_ID,
    "policy_name": "Analysts",
    "rules_applied": [{"access": [{"name": "read"}],
                       "actors": [{"type": "role", "condition": "starts_with",
                                   "identifiers": ["DEV_"]}]}],
    "policy_maintenance": {"rate": "day", "value": 7},
}


async def test_renaming_a_snowflake_policy_keeps_its_rule_and_schedule(
        httpx_mock: HTTPXMock, test_env, mcp):
    """The API deletes the schedule when an update leaves it out."""
    httpx_mock.add_response(method="GET", json={"success": True, "data": STORED_GRANT})
    httpx_mock.add_response(method="PUT", json={"success": True, "data": {}})
    await _call(mcp, "update_snowflake_access_policy", policy_id=GRANT_ID,
                policy_name="Renamed")

    assert _body(httpx_mock, "PUT") == {
        "policy_name": "Renamed",
        "rules": STORED_GRANT["rules_applied"],
        "policy_maintenance": {"rate": "day", "value": 7},
    }
    put = next(r for r in httpx_mock.get_requests() if r.method == "PUT")
    assert str(put.url) == (f"{BASE}/accessManagement/snowflake/"
                            "GRANT%23afe0b9c9-3a29%23DATABASE_TYPE%239")


async def test_a_new_rule_and_no_schedule_replace_the_old_ones(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", json={"success": True, "data": STORED_GRANT})
    httpx_mock.add_response(method="PUT", json={"success": True, "data": {}})
    await _call(mcp, "update_snowflake_access_policy", policy_id=GRANT_ID,
                roles=["BI"], access="read", object_type="database",
                names=["MART"], refresh="none")

    body = _body(httpx_mock, "PUT")
    assert body["policy_name"] == "Analysts"
    assert body["rules"][0]["objects"][0]["fully_qualified_identifiers"] == [
        {"database": "MART"}]
    assert body["rules"][0]["access"] == [{"name": "read"}]
    assert "policy_maintenance" not in body


async def test_updating_a_policy_of_another_kind_is_refused(
        httpx_mock: HTTPXMock, test_env, mcp):
    with pytest.raises(ToolError, match="must start with GRANT#"):
        await _call(mcp, "update_snowflake_access_policy", policy_id=OLTP_ID,
                    policy_name="x")
    assert not httpx_mock.get_requests()


# ── create_oltp_access_policy ───────────────────────

async def test_oltp_policy_takes_its_database_type_from_the_repository(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", json={"name": "orders_db", "type": "Oracle"})
    httpx_mock.add_response(method="POST", url=f"{BASE}/accessManagement/oltp",
                            json={"success": True, "data": {"policy_id": OLTP_ID}})
    await _call(mcp, "create_oltp_access_policy", policy_name="Support",
                repo_name="orders_db", rules=json.dumps([
                    {"access": "update", "groups": ["support"],
                     "object_type": "column", "database": "sales", "schema": "*",
                     "table": "orders", "column": ["email", "phone"]},
                    {"users": ["ana@example.com"], "object_type": "table",
                     "database": "sales", "schema": "public", "table": "*"},
                ]))

    assert _body(httpx_mock, "POST") == {
        "policy_name": "Support",
        "repo_name": "orders_db",
        "database_type": 4,
        "database_type_name": "oracle",
        "case_sensitivity": "case_sensitive",
        "rules": [
            {"type": "update",
             "actors": [{"type": "idp_group", "condition": "equals",
                         "identifiers": ["support"]}],
             "objects": [{"type": "column", "identifiers": [
                 {"database": {"name": "sales"}, "schema": {"wildcard": True},
                  "table": {"name": "orders"}, "column": {"name": "email"}},
                 {"database": {"name": "sales"}, "schema": {"wildcard": True},
                  "table": {"name": "orders"}, "column": {"name": "phone"}},
             ]}]},
            {"type": "read",
             "actors": [{"type": "idp_user", "condition": "equals",
                         "identifiers": ["ana@example.com"]}],
             "objects": [{"type": "table", "identifiers": [
                 {"database": {"name": "sales"}, "schema": {"name": "public"},
                  "table": {"wildcard": True}}]}]},
        ],
    }


async def test_oltp_levels_follow_the_repository_type(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", json={"name": "docs", "type": "MongoDB"})
    httpx_mock.add_response(method="POST", json={"success": True, "data": {}})
    await _call(mcp, "create_oltp_access_policy", policy_name="Docs",
                repo_name="docs", rules=[{
                    "access": "delete", "users": ["ops@example.com"],
                    "object_type": "field", "database": "app",
                    "collection": "events", "field": "*"}])

    body = _body(httpx_mock, "POST")
    assert (body["database_type"], body["database_type_name"]) == (23, "mongodb")
    assert body["rules"][0]["objects"][0]["identifiers"] == [
        {"database": {"name": "app"}, "collection": {"name": "events"},
         "field": {"wildcard": True}}]


@pytest.mark.parametrize("repo_type, rule, message", [
    ("MySQL", {"users": ["u"], "object_type": "schema", "database": "d",
               "schema": ["s"]}, "database, table, column"),
    ("Oracle", {"users": ["u"], "groups": ["g"], "object_type": "database",
                "database": ["d"]}, "users or groups, not both"),
    ("Oracle", {"users": ["u"], "object_type": "table", "database": "d",
                "table": ["t"]}, "needs schema"),
    ("Oracle", {"access": "admin", "users": ["u"], "object_type": "database",
                "database": ["d"]}, "access must be"),
    ("S3", {"users": ["u"], "object_type": "database", "database": ["d"]},
     "S3 repository"),
])
async def test_oltp_rules_outside_the_console_shape_are_refused(
        httpx_mock: HTTPXMock, test_env, mcp, repo_type, rule, message):
    httpx_mock.add_response(method="GET", json={"name": "r", "type": repo_type})
    with pytest.raises(ToolError, match=message):
        await _call(mcp, "create_oltp_access_policy", policy_name="P",
                    repo_name="r", rules=[rule])
    assert not [r for r in httpx_mock.get_requests() if r.method == "POST"]


async def test_oltp_policy_for_a_missing_repository_is_refused(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", status_code=404, json={"message": "nope"})
    with pytest.raises(ToolError, match="No repository named gone"):
        await _call(mcp, "create_oltp_access_policy", policy_name="P",
                    repo_name="gone", rules=[{"users": ["u"],
                                              "object_type": "database",
                                              "database": ["d"]}])


# ── update_oltp_access_policy ───────────────────────

STORED_OLTP = {
    "policy_id": OLTP_ID,
    "policy_name": "Support",
    "description": "Support desk",
    "database_type": 4,
    "database_type_name": "oracle",
    "case_sensitivity": "case_sensitive",
    "rules": [{"type": "read", "actors": [], "objects": []}],
}


async def test_renaming_an_oltp_policy_keeps_its_rules_and_description(
        httpx_mock: HTTPXMock, test_env, mcp):
    """The API clears a description the update leaves out."""
    httpx_mock.add_response(method="GET", json={"success": True, "data": STORED_OLTP})
    httpx_mock.add_response(method="PUT", url=(
        f"{BASE}/accessManagement/oltp/OLTP%235d1c-77aa%23DATABASE_TYPE%234"),
        json={"success": True, "data": {}})
    await _call(mcp, "update_oltp_access_policy", policy_id=OLTP_ID,
                policy_name="Support desk")

    assert _body(httpx_mock, "PUT") == {
        "policy_name": "Support desk",
        "database_type": 4,
        "database_type_name": "oracle",
        "case_sensitivity": "case_sensitive",
        "rules": STORED_OLTP["rules"],
        "description": "Support desk",
    }


async def test_new_oltp_rules_use_the_policys_database_levels(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", json={"success": True, "data": STORED_OLTP})
    with pytest.raises(ToolError, match="database, schema, table, column"):
        await _call(mcp, "update_oltp_access_policy", policy_id=OLTP_ID,
                    rules=[{"users": ["u"], "object_type": "collection",
                            "database": "d", "collection": ["c"]}])


# ── trigger_access_policy_check ─────────────────────

async def test_trigger_check_queues_a_snowflake_refresh(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="PUT", url=(
        f"{BASE}/accessManagement/triggerCheck/"
        "GRANT%23afe0b9c9-3a29%23DATABASE_TYPE%239"),
        json={"success": True, "data": {}})
    result = await _call(mcp, "trigger_access_policy_check", policy_id=GRANT_ID)
    assert result["success"] is True
    assert httpx_mock.get_requests()[0].content == b""


async def test_trigger_check_on_an_oltp_policy_is_refused(
        httpx_mock: HTTPXMock, test_env, mcp):
    with pytest.raises(ToolError, match="Only Snowflake"):
        await _call(mcp, "trigger_access_policy_check", policy_id=OLTP_ID)
    assert not httpx_mock.get_requests()


# ── review follow-ups ───────────────────────────────

@pytest.mark.parametrize("refresh, day, expected", [
    ("daily", None, "30 2 ? * * *"),
    ("weekly", "friday", "30 2 ? * FRI *"),
])
async def test_refresh_schedules_match_the_console(
        httpx_mock: HTTPXMock, test_env, mcp, refresh, day, expected):
    httpx_mock.add_response(method="POST", json={"success": True, "data": {}})
    await _call(mcp, "create_snowflake_access_policy", policy_name="P",
                connection_id=1, roles=["R"], object_type="database",
                names=["D"], refresh=refresh, refresh_time="2:30",
                refresh_day=day)
    assert _body(httpx_mock, "POST")["policy_maintenance"] == {
        "rate": "cron", "value": expected}


async def test_tag_names_without_values_match_any_of_the_tags(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="POST", json={"success": True, "data": {}})
    await _call(mcp, "create_snowflake_access_policy", policy_name="P",
                connection_id=1, roles=["R"], refresh="none",
                tag_check_against="schema", tag_database="GOV",
                tag_schema="TAGS", tag_names=["PII", "PHI"])
    assert _body(httpx_mock, "POST")["rules"][0]["tagged_objects"][0][
        "tagged_with"] == [
            {"database": "GOV", "schema": "TAGS", "name": "PII"},
            {"database": "GOV", "schema": "TAGS", "name": "PHI"}]


@pytest.mark.parametrize("kwargs, message", [
    ({"object_type": "database", "names": ["A"], "tag_values": ["x"]},
     "tag_values can't be combined"),
    ({"tag_names": ["T"], "tag_check_against": "table", "tag_database": "D",
      "tag_schema": "S", "names": ["A"]}, "names can't be combined"),
    ({"object_type": "database", "names": ["A"], "schema": "S"},
     "doesn't take schema"),
    ({"object_type": "database", "names": ["A"], "refresh": "weekly",
      "refresh_time": "01:00", "refresh_day": "Monkey"}, "refresh_day"),
])
async def test_mixed_or_garbled_snowflake_arguments_are_refused(
        httpx_mock: HTTPXMock, test_env, mcp, kwargs, message):
    args = {"policy_name": "P", "connection_id": 1, "roles": ["R"],
            "refresh": "none", **kwargs}
    with pytest.raises(ToolError, match=message):
        await _call(mcp, "create_snowflake_access_policy", **args)


@pytest.mark.parametrize("stored, expected", [
    ({"rules_pending": ["P"], "rules_failed": ["F"], "rules_applied": ["A"]}, ["P"]),
    ({"rules_failed": ["F"], "rules_applied": ["A"]}, ["F"]),
    ({"rules_applied": ["A"], "rules": ["R"]}, ["A"]),
    ({"rules": ["R"]}, ["R"]),
])
async def test_update_starts_from_the_rules_the_console_shows(
        httpx_mock: HTTPXMock, test_env, mcp, stored, expected):
    httpx_mock.add_response(method="GET", json={"success": True, "data": {
        "policy_name": "P", **stored}})
    httpx_mock.add_response(method="PUT", json={"success": True, "data": {}})
    await _call(mcp, "update_snowflake_access_policy", policy_id=GRANT_ID,
                policy_name="Q")
    assert _body(httpx_mock, "PUT")["rules"] == expected


async def test_update_can_replace_the_schedule(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", json={"success": True, "data": STORED_GRANT})
    httpx_mock.add_response(method="PUT", json={"success": True, "data": {}})
    await _call(mcp, "update_snowflake_access_policy",
                policy_id="GRANT%23afe0b9c9-3a29%23DATABASE_TYPE%239",
                refresh="weekly", refresh_time="04:00", refresh_day="SUN")
    assert _body(httpx_mock, "PUT")["policy_maintenance"] == {
        "rate": "cron", "value": "0 4 ? * SUN *"}


@pytest.mark.parametrize("kwargs, message", [
    ({"roles": ["R"]}, "pass all of it"),
    ({"access": "write"}, "pass all of it"),
    ({"refresh_time": "04:00"}, "Pass refresh"),
])
async def test_partial_snowflake_updates_are_refused(
        httpx_mock: HTTPXMock, test_env, mcp, kwargs, message):
    httpx_mock.add_response(method="GET", json={"success": True, "data": STORED_GRANT})
    with pytest.raises(ToolError, match=message):
        await _call(mcp, "update_snowflake_access_policy", policy_id=GRANT_ID,
                    **kwargs)
    assert not [r for r in httpx_mock.get_requests() if r.method == "PUT"]


async def test_update_of_a_policy_that_cannot_be_read_is_refused(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", status_code=404, json={"message": "nope"})
    with pytest.raises(ToolError, match="Could not read policy"):
        await _call(mcp, "update_snowflake_access_policy", policy_id=GRANT_ID,
                    policy_name="Q")


async def test_oltp_policy_when_the_repository_cannot_be_read(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", status_code=403, json={"message": "no"})
    with pytest.raises(ToolError, match="Could not read repository"):
        await _call(mcp, "create_oltp_access_policy", policy_name="P",
                    repo_name="r", rules=[{"users": ["u"],
                                           "object_type": "database",
                                           "database": ["d"]}])


@pytest.mark.parametrize("rule, message", [
    ({"users": ["u"], "object_type": "table", "database": "d", "schema": "s",
      "table": ["*", "orders"]}, "alone for any table"),
    ({"acess": "update", "users": ["u"], "object_type": "database",
      "database": ["d"]}, "unknown keys acess"),
])
async def test_ambiguous_oltp_rules_are_refused(
        httpx_mock: HTTPXMock, test_env, mcp, rule, message):
    httpx_mock.add_response(method="GET", json={"name": "r", "type": "Postgres"})
    with pytest.raises(ToolError, match=message):
        await _call(mcp, "create_oltp_access_policy", policy_name="P",
                    repo_name="r", rules=[rule])


async def test_a_listed_wildcard_is_the_wildcard(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", json={"name": "r", "type": "Cassandra"})
    httpx_mock.add_response(method="POST", json={"success": True, "data": {}})
    await _call(mcp, "create_oltp_access_policy", policy_name="P", repo_name="r",
                rules=[{"users": ["u"], "object_type": "table",
                        "keyspace": " app ", "table": ["*"]}])
    assert _body(httpx_mock, "POST")["rules"][0]["objects"][0]["identifiers"] == [
        {"keyspace": {"name": "app"}, "table": {"wildcard": True}}]


async def test_oltp_update_with_new_rules_resends_the_stored_database_type(
        httpx_mock: HTTPXMock, test_env, mcp):
    """The API refuses a database type that differs from the stored one."""
    stored = {**STORED_OLTP, "description": ""}
    httpx_mock.add_response(method="GET", json={"success": True, "data": stored})
    httpx_mock.add_response(method="PUT", json={"success": True, "data": {}})
    await _call(mcp, "update_oltp_access_policy",
                policy_id="OLTP%235d1c-77aa%23DATABASE_TYPE%234",
                rules=[{"access": "delete", "groups": ["dba"],
                        "object_type": "database", "database": ["sales"]}])
    body = _body(httpx_mock, "PUT")
    assert (body["database_type"], body["database_type_name"]) == (4, "oracle")
    assert body["rules"] == [{
        "type": "delete",
        "actors": [{"type": "idp_group", "condition": "equals",
                    "identifiers": ["dba"]}],
        "objects": [{"type": "database",
                     "identifiers": [{"database": {"name": "sales"}}]}]}]
    assert "description" not in body


async def test_renaming_an_oltp_policy_of_an_older_stored_type_works(
        httpx_mock: HTTPXMock, test_env, mcp):
    stored = {**STORED_OLTP, "database_type": 2, "database_type_name": "postgresql"}
    httpx_mock.add_response(method="GET", json={"success": True, "data": stored})
    httpx_mock.add_response(method="PUT", json={"success": True, "data": {}})
    await _call(mcp, "update_oltp_access_policy", policy_id=OLTP_ID,
                policy_name="New")
    assert _body(httpx_mock, "PUT")["database_type_name"] == "postgresql"


async def test_a_schema_target_takes_its_database(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="POST", json={"success": True, "data": {}})
    await _call(mcp, "create_snowflake_access_policy", policy_name="P",
                connection_id=1, roles=["R"], object_type="schema",
                database="D", names=["S1"], refresh="monthly",
                refresh_time="23:05", refresh_day="Monday", refresh_week=4)
    body = _body(httpx_mock, "POST")
    assert body["rules"][0]["objects"][0]["fully_qualified_identifiers"] == [
        {"database": "D", "schema": "S1"}]
    assert body["policy_maintenance"]["value"] == "5 23 ? * MON#4 *"


@pytest.mark.parametrize("kwargs, message", [
    ({"refresh": "none", "refresh_time": "01:00"}, "none refresh doesn't take"),
    ({"refresh": "daily", "refresh_time": "01:00", "refresh_day": "MON"},
     "daily refresh doesn't take refresh_day"),
    ({"refresh": "weekly", "refresh_time": "01:00", "refresh_day": "MON",
      "refresh_week": 2}, "weekly refresh doesn't take refresh_week"),
])
async def test_refresh_arguments_that_dont_fit_are_refused(
        httpx_mock: HTTPXMock, test_env, mcp, kwargs, message):
    with pytest.raises(ToolError, match=message):
        await _call(mcp, "create_snowflake_access_policy", policy_name="P",
                    connection_id=1, roles=["R"], object_type="database",
                    names=["D"], **kwargs)


async def test_a_level_below_the_object_type_says_so(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", json={"name": "r", "type": "Postgres"})
    with pytest.raises(ToolError, match="column is below object_type table"):
        await _call(mcp, "create_oltp_access_policy", policy_name="P",
                    repo_name="r", rules=[{
                        "users": ["u"], "object_type": "table", "database": "d",
                        "schema": "s", "table": ["t"], "column": ["c"]}])


async def test_new_rules_on_a_policy_found_by_its_numeric_type(
        httpx_mock: HTTPXMock, test_env, mcp):
    stored = {**STORED_OLTP, "database_type": 3, "database_type_name": "MySQL 8"}
    httpx_mock.add_response(method="GET", json={"success": True, "data": stored})
    httpx_mock.add_response(method="PUT", json={"success": True, "data": {}})
    await _call(mcp, "update_oltp_access_policy", policy_id=OLTP_ID,
                rules=[{"users": ["u"], "object_type": "table",
                        "database": "d", "table": ["t"]}])
    body = _body(httpx_mock, "PUT")
    assert body["database_type_name"] == "MySQL 8"
    assert body["rules"][0]["objects"][0]["identifiers"] == [
        {"database": {"name": "d"}, "table": {"name": "t"}}]
