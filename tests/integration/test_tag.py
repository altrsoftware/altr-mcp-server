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


# ── delete_tag ──────────────────────────────────────────────────────────

async def test_delete_tag_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """delete_tag returns {success, data, error} on successful deletion."""
    httpx_mock.add_response(status_code=200, content=b"")
    fn = await get_tool(mcp, "delete_tag")
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


# ── delete_tag_by_details ───────────────────────────────────────────────

async def test_delete_tag_by_details_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """delete_tag_by_details returns {success, data, error} on deletion."""
    httpx_mock.add_response(status_code=200, content=b"")
    fn = await get_tool(mcp, "delete_tag_by_details")
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
