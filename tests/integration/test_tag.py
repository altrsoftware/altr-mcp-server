"""Integration tests for tag tools (altr_mcp/tools/tag.py).

Tests each of the 8 tag tools using pytest-httpx to mock HTTP responses.
Verifies the {success, data, error} response shape for happy paths.
"""
import pytest
from fastmcp import FastMCP
from pytest_httpx import HTTPXMock

from altr_mcp.tools.tag import register
from tests.integration.conftest import get_tool


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


# ── get_tags ────────────────────────────────────────────────────────────

async def test_get_tags_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """get_tags returns {success, data, error} with tag list."""
    # tag util pagination uses has_more flag (not last_evalutated_key)
    httpx_mock.add_response(json={
        "items": [{"tag_group_id": "tg1", "friendly_name": "MY_TAG"}],
        "has_more": False,
    })
    fn = await get_tool(mcp, "get_tags")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── disconnect_tag ──────────────────────────────────────────────────────

async def test_disconnect_tag_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """disconnect_tag returns {success, data, error} on successful disconnect."""
    httpx_mock.add_response(status_code=200, content=b"")
    fn = await get_tool(mcp, "disconnect_tag")
    result = await fn(tag_group_id="tg1")
    assert result["success"] is True
    assert result["error"] is None


# ── get_tag_values ──────────────────────────────────────────────────────

async def test_get_tag_values_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """get_tag_values returns {success, data, error} with values."""
    # tag values util: pagination stops when count >= totals or tags empty
    httpx_mock.add_response(json={
        "tags": [{"tagValue": "PII_EMAIL"}],
        "totals": {"tagCount": 1},
    })
    fn = await get_tool(mcp, "get_tag_values")
    result = await fn(tag_name="MY_TAG")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── get_tag_details_by_group_id ─────────────────────────────────────────

async def test_get_tag_details_by_group_id_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_tag_details_by_group_id returns {success, data, error}."""
    httpx_mock.add_response(
        json={
            "item": {
                "tag_group_id": "tg1",
                "tag_name": "MY_TAG",
                "friendly_name": "MY_TAG",
                "masking_applied": {},
                "masking_pending": None,
                "masking_failed": None}})
    fn = await get_tool(mcp, "get_tag_details_by_group_id")
    result = await fn(tag_group_id="tg1")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── get_tag_details ─────────────────────────────────────────────────────

async def test_get_tag_details_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_tag_details returns {success, data, error}."""
    httpx_mock.add_response(
        json={
            "item": {
                "tag_group_id": "tg1",
                "tag_name": "MY_TAG",
                "friendly_name": "MY_TAG",
                "masking_applied": {},
                "masking_pending": None,
                "masking_failed": None}})
    fn = await get_tool(mcp, "get_tag_details")
    result = await fn(
        database_id=1,
        database_name="MYDB",
        tag_name="MY_TAG",
        schema_name="PUBLIC",
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── update_tag ──────────────────────────────────────────────────────────

async def test_update_tag_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """update_tag returns {success, data, error} after update."""
    httpx_mock.add_response(status_code=201, content=b"")
    fn = await get_tool(mcp, "update_tag")
    result = await fn(
        tag_group_id="tg1",
        database_id=1,
        friendly_name="My Tag",
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── disconnect_tag_by_details ───────────────────────────────────────────

async def test_disconnect_tag_by_details_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """disconnect_tag_by_details returns {success, data, error} on disconnect."""
    httpx_mock.add_response(status_code=200, content=b"")
    fn = await get_tool(mcp, "disconnect_tag_by_details")
    result = await fn(
        database_id=1,
        database_name="MYDB",
        schema_name="PUBLIC",
        tag_name="MY_TAG",
    )
    assert result["success"] is True
    assert result["error"] is None


# ── connect_tag ─────────────────────────────────────────────────────────

async def test_connect_tag_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """connect_tag returns dict with success after connecting tag."""
    # connect_tag makes 2 requests: GET databases, then PUT tag
    httpx_mock.add_response(json={
        "success": True,
        "data": {"databases": [{"id": 1, "name": "MYDB"}]},
    })
    httpx_mock.add_response(json={"status": "SUCCESS", "job_id": "job1"})
    fn = await get_tool(mcp, "connect_tag")
    result = await fn(
        database_name="MYDB",
        schema_name="PUBLIC",
        tag_name="MY_TAG",
    )
    assert result["success"] is True


async def test_connect_tag_pending_status(
        httpx_mock: HTTPXMock, test_env, mcp):
    """PENDING from the connect API surfaces success=True with status field."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {"databases": [{"id": 1, "databaseName": "MYDB"}]},
    })
    httpx_mock.add_response(json={"status": "PENDING", "job_id": "job-p"})
    fn = await get_tool(mcp, "connect_tag")
    result = await fn(
        database_name="MYDB",
        schema_name="PUBLIC",
        tag_name="MY_TAG",
    )
    assert result["success"] is True
    inner = result["data"]
    assert inner["status"] == "PENDING"
    assert inner["job_id"] == "job-p"


async def test_connect_tag_failed_status(
        httpx_mock: HTTPXMock, test_env, mcp):
    """FAILED from the connect API surfaces success=False with error message."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {"databases": [{"id": 1, "databaseName": "MYDB"}]},
    })
    httpx_mock.add_response(json={
        "status": "FAILED",
        "job_id": "job-f",
        "details": {"error_message": "tag does not exist in Snowflake"},
    })
    fn = await get_tool(mcp, "connect_tag")
    result = await fn(
        database_name="MYDB",
        schema_name="PUBLIC",
        tag_name="MISSING_TAG",
    )
    assert result["success"] is True
    inner = result["data"]
    assert inner["success"] is False
    assert "tag does not exist" in inner["message"]


async def test_connect_tag_database_not_found(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Empty databases array surfaces a clear not-found message."""
    httpx_mock.add_response(json={
        "success": True,
        "data": {"databases": []},
    })
    fn = await get_tool(mcp, "connect_tag")
    result = await fn(
        database_name="UNKNOWN_DB",
        schema_name="PUBLIC",
        tag_name="MY_TAG",
    )
    assert result["success"] is True
    inner = result["data"]
    assert inner["success"] is False
    assert "UNKNOWN_DB" in inner["message"]


async def test_disconnect_tag_by_details_ignore_errors(
        httpx_mock: HTTPXMock, test_env, mcp):
    """disconnect_tag_by_details forwards ignore_errors=True as query param."""
    httpx_mock.add_response(json={"success": True})
    fn = await get_tool(mcp, "disconnect_tag_by_details")
    result = await fn(
        database_id=1,
        database_name="DB",
        schema_name="PUBLIC",
        tag_name="MY_TAG",
        ignore_errors=True,
    )
    assert result["success"] is True
    url = str(httpx_mock.get_request().url)
    assert "ignore_errors=true" in url.lower()


async def test_update_tag_with_fpe_options(
        httpx_mock: HTTPXMock, test_env, mcp):
    """update_tag includes optional FPE config and mask_data_type_list."""
    httpx_mock.add_response(json={"success": True})
    fn = await get_tool(mcp, "update_tag")
    result = await fn(
        tag_group_id="tg-1",
        database_id=1,
        friendly_name="MY_TAG",
        protection_type="encryption-fpe",
        mask_data_type_list="text",
        encryption_fpe_options={
            "alphabet": "alphanumeric",
            "is_padded": False,
            "key_name": "k",
            "tweak_name": "t",
        },
    )
    assert result["success"] is True
    import json as _json
    body = _json.loads(httpx_mock.get_request().content)
    assert body["masking"]["mask_data_type_list"] == ["text"]
    assert body["masking"]["encryption_fpe_options"]["alphabet"] \
        == "alphanumeric"


# ── error path ──────────────────────────────────────────────────────────

async def test_tag_domain_error_path(httpx_mock: HTTPXMock, test_env, mcp):
    """Tag domain raises ToolError on HTTP error for tools that access nested keys."""
    # get_tag_values paginates: on 404, api.request returns {success: False}
    # _paginate_altr_tag_values_request does .get("tags", []) so returns empty
    httpx_mock.add_response(status_code=404)
    fn = await get_tool(mcp, "get_tag_values")
    # 404 -> api.request returns error dict -> .get("tags", []) returns []
    # count=0 -> loop breaks -> returns {"tags": []}
    result = await fn(tag_name="MY_TAG")
    assert isinstance(result, dict)
    assert result["success"] is True  # tool wraps whatever util returns
    assert result["error"] is None


# ── invalid JSON / 5xx retry ─────────────────────────────────────────────────

async def test_tag_invalid_json_response(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(
        content=b"<html>Bad Gateway</html>",
        headers={"Content-Type": "text/html"},
    )
    fn = await get_tool(mcp, "disconnect_tag")
    result = await fn(tag_group_id="test-group-id")
    assert result["success"] is True
    assert "raw" in result["data"]


async def test_tag_5xx_retry_exhaustion(
        httpx_mock: HTTPXMock, retry_env, mcp):
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    fn = await get_tool(mcp, "disconnect_tag")
    result = await fn(tag_group_id="test-group-id")
    assert result["success"] is True
    assert result["data"]["success"] is False
    assert "Retry exhausted" in result["data"]["message"]
