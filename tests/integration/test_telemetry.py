"""Integration tests for telemetry tools (altr_mcp/tools/telemetry.py).

Tests 9 telemetry tools using pytest-httpx to mock HTTP responses.
Verifies the {success, data, error} response shape for happy paths.
"""
import pytest
from fastmcp import FastMCP
from pytest_httpx import HTTPXMock

from altr_mcp.tools.telemetry import register
from tests.integration.conftest import get_tool


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


AGENT_ID = "agent-uuid-1234"
SIDECAR_ID = "sidecar-uuid-5678"
INSTANCE_ID = "instance-uuid-abcd"
TASK_ID = "task-uuid-efgh"


# ── get_agent_instances ─────────────────────────────────────────────────

async def test_get_agent_instances_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_agent_instances returns {success, data, error} with instance list."""
    httpx_mock.add_response(json={
        "agent_instances": [
            {
                "agent_id": AGENT_ID,
                "instance_id": INSTANCE_ID,
                "agent_time": 1700000000000,
                "checkin_time": 1700000060000,
                "active_tasks": 2,
                "idle_tasks": 1,
                "tags": {"env": "prod"},
            }
        ],
        "contiguous_id": "",
    })
    fn = await get_tool(mcp, "get_agent_instances")
    result = await fn(agent_id=AGENT_ID)
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── get_agent_instance ──────────────────────────────────────────────────

async def test_get_agent_instance_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_agent_instance returns {success, data, error} for specific instance."""
    httpx_mock.add_response(json={
        "agent_id": AGENT_ID,
        "instance_id": INSTANCE_ID,
        "agent_time": 1700000000000,
        "checkin_time": 1700000060000,
        "active_tasks": 2,
        "idle_tasks": 1,
        "tags": {"env": "prod"},
    })
    fn = await get_tool(mcp, "get_agent_instance")
    result = await fn(agent_id=AGENT_ID, instance_id=INSTANCE_ID)
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── delete_agent_instance ───────────────────────────────────────────────

async def test_delete_agent_instance_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """delete_agent_instance returns {success, data, error} on deletion."""
    httpx_mock.add_response(status_code=204, content=b"")
    fn = await get_tool(mcp, "delete_agent_instance")
    result = await fn(agent_id=AGENT_ID, instance_id=INSTANCE_ID)
    assert result["success"] is True
    assert result["error"] is None


# ── get_agent_task_telemetry ────────────────────────────────────────────

async def test_get_agent_task_telemetry_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_agent_task_telemetry returns {success, data, error} with task data."""
    httpx_mock.add_response(json={
        "task_telemetry": [
            {
                "task_id": TASK_ID,
                "agent_id": AGENT_ID,
                "status": "completed",
                "task_type": "encryption",
                "repository": "my_oracle_db",
                "service_user": "svc_user_1",
                "agent_time": 1700000000000,
                "checkin_time": 1700000060000,
                "messages": [{"severity": "INFO", "message": "Task completed."}],
                "tags": {},
            }
        ],
        "contiguous_id": "",
    })
    fn = await get_tool(mcp, "get_agent_task_telemetry")
    result = await fn(agent_id=AGENT_ID)
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── get_sidecar_instances ───────────────────────────────────────────────

async def test_get_sidecar_instances_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_sidecar_instances returns {success, data, error} with instance list."""
    httpx_mock.add_response(json={
        "sidecar_instances": [
            {
                "sidecar_id": SIDECAR_ID,
                "instance_id": INSTANCE_ID,
                "checkin_time": 1700000060000,
                "active_connections": 5,
                "sidecar_version": "1.2.3",
                "tags": {"env": "prod"},
            }
        ],
        "contiguous_id": "",
    })
    fn = await get_tool(mcp, "get_sidecar_instances")
    result = await fn(sidecar_id=SIDECAR_ID)
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── get_sidecar_instance ────────────────────────────────────────────────

async def test_get_sidecar_instance_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_sidecar_instance returns {success, data, error} for specific instance."""
    httpx_mock.add_response(json={
        "sidecar_id": SIDECAR_ID,
        "instance_id": INSTANCE_ID,
        "checkin_time": 1700000060000,
        "active_connections": 5,
        "sidecar_version": "1.2.3",
        "tags": {"env": "prod"},
    })
    fn = await get_tool(mcp, "get_sidecar_instance")
    result = await fn(sidecar_id=SIDECAR_ID, instance_id=INSTANCE_ID)
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── delete_sidecar_instance ─────────────────────────────────────────────

async def test_delete_sidecar_instance_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """delete_sidecar_instance returns {success, data, error} on deletion."""
    httpx_mock.add_response(status_code=204, content=b"")
    fn = await get_tool(mcp, "delete_sidecar_instance")
    result = await fn(sidecar_id=SIDECAR_ID, instance_id=INSTANCE_ID)
    assert result["success"] is True
    assert result["error"] is None


# ── get_task_telemetry ──────────────────────────────────────────────────

async def test_get_task_telemetry_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_task_telemetry returns {success, data, error} for specific task."""
    httpx_mock.add_response(json={
        "task_id": TASK_ID,
        "agent_id": AGENT_ID,
        "status": "completed",
        "task_type": "encryption",
        "repository": "my_oracle_db",
        "service_user": "svc_user_1",
        "agent_time": 1700000000000,
        "checkin_time": 1700000060000,
        "messages": [{"severity": "INFO", "message": "Task completed."}],
        "tags": {},
    })
    fn = await get_tool(mcp, "get_task_telemetry")
    result = await fn(task_id=TASK_ID)
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── delete_task_telemetry ───────────────────────────────────────────────

async def test_delete_task_telemetry_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """delete_task_telemetry returns {success, data, error} on deletion."""
    httpx_mock.add_response(status_code=204, content=b"")
    fn = await get_tool(mcp, "delete_task_telemetry")
    result = await fn(task_id=TASK_ID)
    assert result["success"] is True
    assert result["error"] is None


async def test_get_agent_instances_with_pagination(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_agent_instances forwards limit and contiguous_id."""
    httpx_mock.add_response(json={"instances": []})
    fn = await get_tool(mcp, "get_agent_instances")
    result = await fn(agent_id="ag-1", limit=25, contiguous_id="cur")
    assert result["success"] is True
    url = str(httpx_mock.get_request().url)
    assert "limit=25" in url
    assert "contiguous_id=cur" in url


async def test_get_agent_task_telemetry_with_pagination(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_agent_task_telemetry forwards limit and contiguous_id."""
    httpx_mock.add_response(json={"tasks": []})
    fn = await get_tool(mcp, "get_agent_task_telemetry")
    result = await fn(agent_id="ag-1", limit=10, contiguous_id="cur")
    assert result["success"] is True
    url = str(httpx_mock.get_request().url)
    assert "limit=10" in url
    assert "contiguous_id=cur" in url


async def test_get_sidecar_instances_with_pagination(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_sidecar_instances forwards limit and contiguous_id."""
    httpx_mock.add_response(json={"instances": []})
    fn = await get_tool(mcp, "get_sidecar_instances")
    result = await fn(sidecar_id="sc-1", limit=5, contiguous_id="cur")
    assert result["success"] is True
    url = str(httpx_mock.get_request().url)
    assert "limit=5" in url
    assert "contiguous_id=cur" in url


# ── error path ──────────────────────────────────────────────────────────

async def test_telemetry_error_path(httpx_mock: HTTPXMock, test_env, mcp):
    """telemetry tools return error data on HTTP 404."""
    httpx_mock.add_response(status_code=404)
    fn = await get_tool(mcp, "get_task_telemetry")
    result = await fn(task_id="nonexistent-task")
    assert result["success"] is True
    assert result["error"] is None
    inner = result["data"]
    assert inner.get("success") is False


# ── invalid JSON / 5xx retry ─────────────────────────────────────────────────

async def test_telemetry_invalid_json_response(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(
        content=b"<html>Bad Gateway</html>",
        headers={"Content-Type": "text/html"},
    )
    fn = await get_tool(mcp, "get_agent_instances")
    result = await fn(agent_id="test-agent")
    assert result["success"] is True
    assert "raw" in result["data"]


async def test_telemetry_5xx_retry_exhaustion(
        httpx_mock: HTTPXMock, retry_env, mcp):
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    fn = await get_tool(mcp, "get_agent_instances")
    result = await fn(agent_id="test-agent")
    assert result["success"] is True
    assert result["data"]["success"] is False
    assert "Retry exhausted" in result["data"]["message"]
