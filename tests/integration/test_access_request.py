"""Integration tests for access request tools (altr_mcp/tools/access_request.py).

The tools review requests the way the console does, so pytest-httpx checks the
exact requests sent.
"""
import json

import httpx
import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pytest_httpx import HTTPXMock

from altr_mcp.tools.access_request import register
from tests.integration.conftest import get_tool

BASE = "https://api.live.altr.com/v1/unified-policy/management/accessRequest"
REQUEST_ID = "a56f3f23-e523-46a8-9c1e-0b5a2f6d7e11"


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


async def _call(mcp, name, **kwargs):
    return await (await get_tool(mcp, name))(**kwargs)


def _request(status: str) -> dict:
    return {"success": True, "data": {"id": REQUEST_ID, "status": status}}


# ── get_access_requests ─────────────────────────────

async def test_list_defaults_to_the_consoles_view(
        httpx_mock: HTTPXMock, test_env, mcp):
    """The console lists 100 OPEN requests, newest first."""
    httpx_mock.add_response(
        url=f"{BASE}?limit=100&status=OPEN&sort=desc",
        json={"success": True, "data": {"access_requests": [], "count": 0}})
    result = await _call(mcp, "get_access_requests")
    assert result["success"] is True


async def test_list_filters_are_forwarded(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(
        url=f"{BASE}?limit=5&status=CLOSED_DENIED&sort=asc&requester=Alice",
        json={"success": True, "data": {"access_requests": [], "count": 0}})
    await _call(mcp, "get_access_requests", limit=5, status="closed_denied",
                sort="asc", requester="Alice")


@pytest.mark.parametrize("kwargs, message", [
    ({"limit": 101}, "limit must be"),
    ({"limit": 0}, "limit must be"),
    ({"status": "CLOSED"}, "status must be"),
    ({"sort": "newest"}, "sort must be"),
])
async def test_list_values_the_api_rejects_are_refused(
        httpx_mock: HTTPXMock, test_env, mcp, kwargs, message):
    with pytest.raises(ToolError, match=message):
        await _call(mcp, "get_access_requests", **kwargs)
    assert not httpx_mock.get_requests()


# ── get_access_request ──────────────────────────────

async def test_get_one_request(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(url=f"{BASE}/{REQUEST_ID}", json=_request("OPEN"))
    result = await _call(mcp, "get_access_request", request_id=REQUEST_ID)
    assert result["data"]["data"]["status"] == "OPEN"


# ── approve_access_request / deny_access_request ────

@pytest.mark.parametrize("tool, action", [
    ("approve_access_request", "approve"), ("deny_access_request", "deny")])
async def test_a_decision_on_an_open_request_sends_the_justification(
        httpx_mock: HTTPXMock, test_env, mcp, tool, action):
    httpx_mock.add_response(method="PUT", url=f"{BASE}/{REQUEST_ID}/{action}",
                            json=_request("CLOSED_APPROVED"))
    await _call(mcp, tool, request_id=REQUEST_ID, justification=" Ticket 42 ")

    put = next(r for r in httpx_mock.get_requests() if r.method == "PUT")
    assert json.loads(put.content) == {"justification": "Ticket 42"}


@pytest.mark.parametrize("tool", ["approve_access_request", "deny_access_request"])
async def test_a_decision_without_a_justification_sends_no_body(
        httpx_mock: HTTPXMock, test_env, mcp, tool):
    """The console's comment is optional and sends nothing when empty."""
    httpx_mock.add_response(method="PUT", json=_request("CLOSED_DENIED"))
    await _call(mcp, tool, request_id=REQUEST_ID)

    put = next(r for r in httpx_mock.get_requests() if r.method == "PUT")
    assert put.content == b""


@pytest.mark.parametrize("tool", ["approve_access_request", "deny_access_request"])
async def test_a_decision_the_api_refuses_fails_with_its_error(
        httpx_mock: HTTPXMock, test_env, mcp, tool):
    """Only one request is sent; the API refuses a closed request with 400."""
    httpx_mock.add_response(method="PUT", status_code=400, json={
        "message": "Cannot update an access request that is not in the open state."})
    with pytest.raises(ToolError, match="not in the open state"):
        await _call(mcp, tool, request_id=REQUEST_ID)
    assert len(httpx_mock.get_requests()) == 1


async def test_a_decision_that_cannot_reach_the_api_fails(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_exception(httpx.ConnectError("down"), method="PUT")
    with pytest.raises(ToolError, match="Could not approve access request"):
        await _call(mcp, "approve_access_request", request_id=REQUEST_ID)


async def test_a_long_justification_is_refused(httpx_mock: HTTPXMock, test_env, mcp):
    with pytest.raises(ToolError, match="1000 characters"):
        await _call(mcp, "deny_access_request", request_id=REQUEST_ID,
                    justification="x" * 1001)
    assert not httpx_mock.get_requests()


async def test_sort_is_case_insensitive(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(url=f"{BASE}?limit=100&status=OPEN&sort=desc",
                            json={"success": True, "data": {}})
    await _call(mcp, "get_access_requests", sort="DESC")


AR_KEY = {"PK": {"S": "ORG#o#ACCESS_REQUEST"}, "SK": {"S": "ACCESS_REQUEST#i"},
          "GSI2PK": {"S": "ORG#o#ACCESS_REQUEST"},
          "GSI2SK": {"S": "STATUS#OPEN#CREATED_AT#t#ACCESS_REQUEST#i"}}


@pytest.mark.parametrize("key", [AR_KEY, json.dumps(AR_KEY)])
async def test_the_next_page_sends_the_key_back_as_json(
        httpx_mock: HTTPXMock, test_env, mcp, key):
    httpx_mock.add_response(json={"success": True, "data": {
        "access_requests": [], "count": 0}})
    await _call(mcp, "get_access_requests", exclusive_start_key=key)

    sent = httpx_mock.get_requests()[0].url.params
    assert json.loads(sent["exclusive_start_key"]) == AR_KEY
    assert sent["exclusive_start_key"].startswith('{"PK":{"S":')
    assert sent["status"] == "OPEN"


@pytest.mark.parametrize("key", ["", "  ", {}])
async def test_an_empty_key_asks_for_the_first_page(
        httpx_mock: HTTPXMock, test_env, mcp, key):
    httpx_mock.add_response(url=f"{BASE}?limit=100&status=OPEN&sort=desc",
                            json={"success": True, "data": {}})
    await _call(mcp, "get_access_requests", exclusive_start_key=key)


@pytest.mark.parametrize("key", ["next-page-token", "[1, 2]"])
async def test_a_key_that_isnt_a_returned_key_is_refused(
        httpx_mock: HTTPXMock, test_env, mcp, key):
    with pytest.raises(ToolError, match="last_evaluated_key, unchanged"):
        await _call(mcp, "get_access_requests", exclusive_start_key=key)
    assert not httpx_mock.get_requests()
