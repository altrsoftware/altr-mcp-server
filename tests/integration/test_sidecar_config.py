"""Integration tests for sidecar config tools (altr_mcp/tools/sidecar_config.py).

Tests representative tools across all 6 resource types (agents, repos, repo_users,
service_users, sidecars, sidecar_bindings/listeners) using pytest-httpx to mock
HTTP responses. Verifies the {success, data, error} response shape.

The sidecar_config module has 33 CRUD tools; testing one per resource type
plus one error path provides sufficient coverage without redundant repetition.
"""
import pytest
from fastmcp import FastMCP
from pytest_httpx import HTTPXMock

from altr_mcp.tools.sidecar_config import register
from tests.integration.conftest import get_tool


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


# ── Agents ──────────────────────────────────────────────────────────────

async def test_list_sc_agents(httpx_mock: HTTPXMock, test_env, mcp):
    """list_sc_agents returns {success, data, error} with agent list."""
    httpx_mock.add_response(json={
        "agents": [
            {
                "id": "ag-uuid-1234",
                "type": "SIS",
                "name": "My Agent",
                "description": "Primary SIS agent",
                "data_plane_url": "https://agent.example.com",
                "task_count": 2,
                "public_key_1": "-----BEGIN PUBLIC KEY-----\nMIIBIj...",
                "public_key_2": "",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-06-01T12:30:00Z",
            }
        ],
        "contiguous_id": "",
    })
    fn = await get_tool(mcp, "list_sc_agents")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_create_sc_agent(httpx_mock: HTTPXMock, test_env, mcp):
    """create_sc_agent returns {success, data, error} on creation."""
    httpx_mock.add_response(json={
        "id": "ag-uuid-5678",
        "type": "SIS",
        "name": "New Agent",
        "description": "",
        "data_plane_url": "",
        "task_count": 0,
        "public_key_1": "",
        "public_key_2": "",
        "created_at": "2024-06-01T12:30:00Z",
        "updated_at": "2024-06-01T12:30:00Z",
    })
    fn = await get_tool(mcp, "create_sc_agent")
    result = await fn(agent_type="SIS", name="New Agent")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── Repos ───────────────────────────────────────────────────────────────

async def test_create_sc_repo(httpx_mock: HTTPXMock, test_env, mcp):
    """create_sc_repo returns {success, data, error} on creation."""
    httpx_mock.add_response(json={
        "name": "my_oracle_db",
        "description": "",
        "hostname": "db.example.com",
        "port": 1521,
        "type": "Oracle",
        "user_count": 0,
        "service_user_count": 0,
        "binding_count": 0,
        "org_id": "org-uuid-1234",
        "created_at": "2024-06-01T12:30:00Z",
        "updated_at": "2024-06-01T12:30:00Z",
    })
    fn = await get_tool(mcp, "create_sc_repo")
    result = await fn(
        name="my_oracle_db",
        repo_type="Oracle",
        hostname="db.example.com",
        port=1521,
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_list_sc_repos(httpx_mock: HTTPXMock, test_env, mcp):
    """list_sc_repos returns {success, data, error} with repo list."""
    httpx_mock.add_response(json={
        "repos": [
            {
                "name": "my_oracle_db",
                "description": "",
                "hostname": "db.example.com",
                "port": 1521,
                "type": "Oracle",
                "user_count": 1,
                "service_user_count": 2,
                "binding_count": 1,
                "org_id": "org-uuid-1234",
                "created_at": "2024-06-01T12:30:00Z",
                "updated_at": "2024-06-01T12:30:00Z",
            }
        ],
        "contiguous_id": "",
    })
    fn = await get_tool(mcp, "list_sc_repos")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── Repo Users ──────────────────────────────────────────────────────────

async def test_get_sc_repo_user(httpx_mock: HTTPXMock, test_env, mcp):
    """get_sc_repo_user returns {success, data, error} for a specific repo user."""
    httpx_mock.add_response(json={
        "username": "dbuser",
        "repo_name": "my_oracle_db",
        "aws_secrets_manager": {"secrets_path": "/prod/db/creds"},
        "azure_key_vault": {},
        "created_at": "2024-06-01T12:30:00Z",
        "updated_at": "2024-06-01T12:30:00Z",
    })
    fn = await get_tool(mcp, "get_sc_repo_user")
    result = await fn(repo_name="my_oracle_db", username="dbuser")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── Service Users ───────────────────────────────────────────────────────

async def test_create_sc_service_user(httpx_mock: HTTPXMock, test_env, mcp):
    """create_sc_service_user returns {success, data, error} on creation."""
    httpx_mock.add_response(json={
        "username": "svc_user_1",
        "repo_name": "my_oracle_db",
        "resource": "arn:aws:iam::123456789012:role/MyRole",
        "aws_secrets_manager": {"secrets_path": "/prod/db/creds"},
        "azure_key_vault": {},
        "created_at": "2024-06-01T12:30:00Z",
        "updated_at": "2024-06-01T12:30:00Z",
    })
    fn = await get_tool(mcp, "create_sc_service_user")
    result = await fn(
        repo_name="my_oracle_db",
        username="svc_user_1",
        resource="arn:aws:iam::123456789012:role/MyRole",
        aws_secrets_manager={"secrets_path": "/prod/db/creds"},
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_list_sc_service_users_no_repo(
        httpx_mock: HTTPXMock, test_env, mcp):
    """list_sc_service_users returns all service users when repo_name is absent."""
    httpx_mock.add_response(json={
        "service_users": [
            {
                "username": "svc_user_1",
                "repo_name": "my_oracle_db",
                "resource": "arn:aws:iam::123456789012:role/MyRole",
                "aws_secrets_manager": {},
                "azure_key_vault": {},
                "created_at": "2024-06-01T12:30:00Z",
                "updated_at": "2024-06-01T12:30:00Z",
            }
        ],
        "contiguous_id": "",
    })
    fn = await get_tool(mcp, "list_sc_service_users")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── Sidecars ────────────────────────────────────────────────────────────

async def test_list_sc_sidecars(httpx_mock: HTTPXMock, test_env, mcp):
    """list_sc_sidecars returns {success, data, error} with sidecar list."""
    httpx_mock.add_response(json={
        "sidecars": [
            {
                "id": "sc-uuid-1234",
                "name": "prod-sidecar",
                "description": "Production sidecar",
                "hostname": "sidecar.example.com",
                "org_id": "org-uuid-1234",
                "data_plane_url": "https://dp.example.com",
                "listener_repo_binding_count": 2,
                "listener_count": 1,
                "public_key_1": "-----BEGIN PUBLIC KEY-----\nMIIBIj...",
                "public_key_2": "",
                "unsupported_query_bypass": False,
                "disable_platform_audits": False,
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-06-01T12:30:00Z",
            }
        ],
        "contiguous_id": "",
    })
    fn = await get_tool(mcp, "list_sc_sidecars")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── Listeners ───────────────────────────────────────────────────────────

async def test_register_sc_sidecar_listener(
        httpx_mock: HTTPXMock, test_env, mcp):
    """register_sc_sidecar_listener returns {success, data, error} on registration."""
    httpx_mock.add_response(status_code=204, content=b"")
    fn = await get_tool(mcp, "register_sc_sidecar_listener")
    result = await fn(
        sidecar_id="sc-1",
        port=3307,
        database_type="Oracle",
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── Sidecar Bindings ────────────────────────────────────────────────────

async def test_create_sc_sidecar_binding(httpx_mock: HTTPXMock, test_env, mcp):
    """create_sc_sidecar_binding returns {success, data, error} on creation."""
    httpx_mock.add_response(status_code=204, content=b"")
    fn = await get_tool(mcp, "create_sc_sidecar_binding")
    result = await fn(
        sidecar_id="sc-1",
        port=3307,
        repo_name="my_oracle_db",
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── agent tasks ────────────────────────────────────────────────────────

async def test_list_sc_agent_tasks(
        httpx_mock: HTTPXMock, test_env, mcp):
    """list_sc_agent_tasks returns task list."""
    httpx_mock.add_response(json={
        "tasks": [
            {
                "id": "task-001",
                "name": "oracle-audit",
                "repo_name": "oracle_db",
                "status": "ACTIVE",
            }
        ],
        "contiguous_id": None,
    })
    fn = await get_tool(mcp, "list_sc_agent_tasks")
    result = await fn(agent_id="agent-001")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_create_sc_agent_task(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_sc_agent_task returns created task."""
    httpx_mock.add_response(status_code=201, json={
        "id": "task-001",
        "name": "oracle-audit",
        "repo_name": "oracle_db",
        "configuration": {},
        "schedule": {
            "type": "CRON",
            "value": "0 2 * * *",
        },
    })
    fn = await get_tool(mcp, "create_sc_agent_task")
    result = await fn(
        agent_id="agent-001",
        name="oracle-audit",
        repo_name="oracle_db",
        configuration='{}',
        schedule='{"type": "CRON", "value": "0 2 * * *"}',
        service_user="adminuser",
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_update_sc_agent_task(
        httpx_mock: HTTPXMock, test_env, mcp):
    """update_sc_agent_task returns updated task."""
    httpx_mock.add_response(json={
        "id": "task-001",
        "name": "oracle-audit-updated",
    })
    fn = await get_tool(mcp, "update_sc_agent_task")
    result = await fn(
        agent_id="agent-001",
        task_id="task-001",
        name="oracle-audit-updated",
    )
    assert result["success"] is True
    assert result["error"] is None


async def test_delete_sc_agent_task(
        httpx_mock: HTTPXMock, test_env, mcp):
    """delete_sc_agent_task returns 204."""
    httpx_mock.add_response(status_code=204)
    fn = await get_tool(mcp, "delete_sc_agent_task")
    result = await fn(
        agent_id="agent-001",
        task_id="task-001",
    )
    assert result["success"] is True
    assert result["error"] is None


# ── error path ──────────────────────────────────────────────────────────

async def test_sc_agent_error_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Sidecar config tools return error data on HTTP failure."""
    httpx_mock.add_response(status_code=404)
    fn = await get_tool(mcp, "get_sc_agent")
    result = await fn(agent_id="nonexistent-agent")
    assert result["success"] is True
    assert result["error"] is None
    inner = result["data"]
    assert inner.get("success") is False
