"""Integration tests for audit report tools (altr_mcp/tools/audit_report.py).

Tests all 17 audit report tools using pytest-httpx to mock HTTP responses.
"""
import pytest
from fastmcp import FastMCP
from pytest_httpx import HTTPXMock

from altr_mcp.tools.audit_report import register
from tests.integration.conftest import get_tool

DEF_ID = "def-abc123"
INST_ID = "inst-xyz789"
COMMENT_ID = "cmt-001"


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


# ── list_report_definitions ──────────────────────────────────────────────────

async def test_list_report_definitions_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"items": [], "cursor": None})
    fn = await get_tool(mcp, "list_report_definitions")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_list_report_definitions_with_archived(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"items": []})
    fn = await get_tool(mcp, "list_report_definitions")
    result = await fn(archived=True, limit=10)
    assert result["success"] is True
    url_str = str(httpx_mock.get_request().url)
    assert "archived=True" in url_str or "archived=true" in url_str
    assert "limit=10" in url_str


async def test_list_report_definitions_with_cursor(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"items": []})
    fn = await get_tool(mcp, "list_report_definitions")
    result = await fn(cursor="page-2-token")
    assert result["success"] is True
    assert "cursor=page-2-token" in str(httpx_mock.get_request().url)


# ── create_report_definition ─────────────────────────────────────────────────

async def test_create_report_definition_minimal(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"id": DEF_ID, "name": "My Report"})
    fn = await get_tool(mcp, "create_report_definition")
    result = await fn(name="My Report", integration_type="oltp")
    assert result["success"] is True
    assert result["data"]["id"] == DEF_ID


async def test_create_report_definition_with_schedule(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"id": DEF_ID})
    fn = await get_tool(mcp, "create_report_definition")
    result = await fn(
        name="Daily Report",
        integration_type="snowflake",
        description="A daily report",
        lookback_days=7,
        timezone="America/New_York",
        schedule_cron="0 12 * * ? *",
        schedule_enabled=True,
        schedule_timezone="America/New_York",
    )
    assert result["success"] is True


async def test_create_report_definition_delivery_as_json_string(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"id": DEF_ID})
    fn = await get_tool(mcp, "create_report_definition")
    delivery = '{"channels": [{"type": "email", "enabled": true, "recipients": ["test@example.com"]}]}'
    result = await fn(
        name="Email Report",
        integration_type="oltp",
        delivery=delivery,
    )
    assert result["success"] is True


# ── get_report_definition ────────────────────────────────────────────────────

async def test_get_report_definition(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"id": DEF_ID, "name": "My Report"})
    fn = await get_tool(mcp, "get_report_definition")
    result = await fn(definition_id=DEF_ID)
    assert result["success"] is True
    assert DEF_ID in str(httpx_mock.get_request().url)


# ── update_report_definition ─────────────────────────────────────────────────

async def test_update_report_definition(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"id": DEF_ID, "name": "Updated Report"})
    fn = await get_tool(mcp, "update_report_definition")
    result = await fn(
        definition_id=DEF_ID,
        name="Updated Report",
        integration_type="oltp",
    )
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert DEF_ID in str(request.url)
    assert request.method == "PUT"


# ── archive_report_definition ────────────────────────────────────────────────

async def test_archive_report_definition(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=204, content=b"")
    fn = await get_tool(mcp, "archive_report_definition")
    result = await fn(definition_id=DEF_ID)
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert DEF_ID in str(request.url)
    assert request.method == "DELETE"


# ── restore_report_definition ────────────────────────────────────────────────

async def test_restore_report_definition(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"id": DEF_ID})
    fn = await get_tool(mcp, "restore_report_definition")
    result = await fn(definition_id=DEF_ID)
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert "restore" in str(request.url)
    assert request.method == "POST"


# ── trigger_report_definition ────────────────────────────────────────────────

async def test_trigger_report_definition(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"instance_id": INST_ID})
    fn = await get_tool(mcp, "trigger_report_definition")
    result = await fn(definition_id=DEF_ID)
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert "trigger" in str(request.url)
    assert request.method == "POST"


# ── list_report_instances ────────────────────────────────────────────────────

async def test_list_report_instances_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"items": [], "cursor": None})
    fn = await get_tool(mcp, "list_report_instances")
    result = await fn(definition_id=DEF_ID)
    assert result["success"] is True
    assert DEF_ID in str(httpx_mock.get_request().url)


async def test_list_report_instances_with_pagination(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"items": []})
    fn = await get_tool(mcp, "list_report_instances")
    result = await fn(definition_id=DEF_ID, limit=5, cursor="c2")
    assert result["success"] is True
    url_str = str(httpx_mock.get_request().url)
    assert "limit=5" in url_str
    assert "cursor=c2" in url_str


# ── get_report_instance ──────────────────────────────────────────────────────

async def test_get_report_instance(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={
        "id": INST_ID, "status": "completed", "definition_id": DEF_ID
    })
    fn = await get_tool(mcp, "get_report_instance")
    result = await fn(definition_id=DEF_ID, instance_id=INST_ID)
    assert result["success"] is True
    assert INST_ID in str(httpx_mock.get_request().url)


# ── get_report_instance_download_url ─────────────────────────────────────────

async def test_get_report_instance_download_url_default_pdf(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"url": "https://s3.example.com/report.pdf"})
    fn = await get_tool(mcp, "get_report_instance_download_url")
    result = await fn(definition_id=DEF_ID, instance_id=INST_ID)
    assert result["success"] is True
    assert "format=pdf" in str(httpx_mock.get_request().url)


async def test_get_report_instance_download_url_csv(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"url": "https://s3.example.com/report.csv"})
    fn = await get_tool(mcp, "get_report_instance_download_url")
    result = await fn(
        definition_id=DEF_ID, instance_id=INST_ID, format="csv")
    assert result["success"] is True
    assert "format=csv" in str(httpx_mock.get_request().url)


# ── list_report_comments ─────────────────────────────────────────────────────

async def test_list_report_comments(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"items": [], "cursor": None})
    fn = await get_tool(mcp, "list_report_comments")
    result = await fn(definition_id=DEF_ID, instance_id=INST_ID)
    assert result["success"] is True
    url_str = str(httpx_mock.get_request().url)
    assert DEF_ID in url_str
    assert INST_ID in url_str


# ── create_report_comment ────────────────────────────────────────────────────

async def test_create_report_comment(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"id": COMMENT_ID, "text": "LGTM"})
    fn = await get_tool(mcp, "create_report_comment")
    result = await fn(
        definition_id=DEF_ID, instance_id=INST_ID, text="LGTM")
    assert result["success"] is True
    assert result["data"]["id"] == COMMENT_ID


# ── pin_report_comment ───────────────────────────────────────────────────────

async def test_pin_report_comment(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"id": COMMENT_ID, "pinned": True})
    fn = await get_tool(mcp, "pin_report_comment")
    result = await fn(
        definition_id=DEF_ID, instance_id=INST_ID, comment_id=COMMENT_ID)
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert "pin" in str(request.url)
    assert request.method == "POST"


# ── unpin_report_comment ─────────────────────────────────────────────────────

async def test_unpin_report_comment(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"id": COMMENT_ID, "pinned": False})
    fn = await get_tool(mcp, "unpin_report_comment")
    result = await fn(
        definition_id=DEF_ID, instance_id=INST_ID, comment_id=COMMENT_ID)
    assert result["success"] is True
    assert "unpin" in str(httpx_mock.get_request().url)


# ── get_report_sign_off ──────────────────────────────────────────────────────

async def test_get_report_sign_off(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={
        "action": "approve", "attestation": True, "user_id": "u-1"
    })
    fn = await get_tool(mcp, "get_report_sign_off")
    result = await fn(definition_id=DEF_ID, instance_id=INST_ID)
    assert result["success"] is True
    assert "sign_off" in str(httpx_mock.get_request().url)


# ── create_report_sign_off ───────────────────────────────────────────────────

async def test_create_report_sign_off_defaults(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"action": "approve", "attestation": True})
    fn = await get_tool(mcp, "create_report_sign_off")
    result = await fn(definition_id=DEF_ID, instance_id=INST_ID)
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert request.method == "POST"


async def test_create_report_sign_off_with_comments(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"action": "approve"})
    fn = await get_tool(mcp, "create_report_sign_off")
    result = await fn(
        definition_id=DEF_ID,
        instance_id=INST_ID,
        action="approve",
        attestation=True,
        comments="Reviewed and approved.",
    )
    assert result["success"] is True


# ── list_report_sign_offs ────────────────────────────────────────────────────

async def test_list_report_sign_offs(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"items": [], "cursor": None})
    fn = await get_tool(mcp, "list_report_sign_offs")
    result = await fn(definition_id=DEF_ID, instance_id=INST_ID)
    assert result["success"] is True
    assert "sign_offs" in str(httpx_mock.get_request().url)


async def test_list_report_sign_offs_with_pagination(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"items": []})
    fn = await get_tool(mcp, "list_report_sign_offs")
    result = await fn(
        definition_id=DEF_ID, instance_id=INST_ID,
        limit=20, cursor="pg3",
    )
    assert result["success"] is True
    url_str = str(httpx_mock.get_request().url)
    assert "limit=20" in url_str
    assert "cursor=pg3" in url_str


# ── error path ───────────────────────────────────────────────────────────────

async def test_audit_report_error_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=404)
    fn = await get_tool(mcp, "get_report_definition")
    result = await fn(definition_id="nonexistent")
    assert result["success"] is True
    assert result["error"] is None
    assert result["data"].get("success") is False


async def test_audit_report_invalid_json_response(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(
        content=b"<html>Bad Gateway</html>",
        headers={"Content-Type": "text/html"},
    )
    fn = await get_tool(mcp, "list_report_definitions")
    result = await fn()
    assert result["success"] is True
    assert "raw" in result["data"]


async def test_audit_report_5xx_retry_exhaustion(
        httpx_mock: HTTPXMock, retry_env, mcp):
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    fn = await get_tool(mcp, "list_report_definitions")
    result = await fn()
    assert result["success"] is True
    assert result["data"]["success"] is False
    assert "Retry exhausted" in result["data"]["message"]
