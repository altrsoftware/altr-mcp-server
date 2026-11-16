"""Integration tests for sidecar config tools (altr_mcp/tools/sidecar_config.py).

Tests tools across each resource type (agents, repos, repo_users,
service_users, sidecars, sidecar_bindings/listeners) using pytest-httpx to
mock HTTP responses. Verifies the {success, data, error} response shape.

The module is largely repetitive CRUD, so the happy-path tests cover one
tool per resource type; the optional-argument tests at the end of the file
cover the parameter-building branches the rest share.
"""
import json

import pytest
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pytest_httpx import HTTPXMock

from altr_mcp.tools.sidecar_config import register
from altr_mcp.utils.scan_requests import CONDITION_TYPES
from tests.integration.conftest import get_tool


PEM = "-----BEGIN PUBLIC KEY-----\nMIIBIj...\n-----END PUBLIC KEY-----"
SC = "https://test-org.sc-control.live.altr.com/v1"


def _sis_agent(httpx_mock, agent_id="agent-001"):
    httpx_mock.add_response(method="GET", url=f"{SC}/agents/{agent_id}",
                            json={"id": agent_id, "type": "SIS"})


def _classifier(httpx_mock, repo_type="Postgres", agent_id="a-1", repo="repo"):
    httpx_mock.add_response(method="GET", url=f"{SC}/agents/{agent_id}",
                            json={"id": agent_id, "type": "CLASSIFIER"})
    if repo_type:
        httpx_mock.add_response(method="GET", url=f"{SC}/repos/{repo}",
                                json={"name": repo, "type": repo_type})


def _sent(httpx_mock, method):
    return json.loads(next(
        r for r in httpx_mock.get_requests() if r.method == method).content)


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
        "public_key_1": {"rsa_key": PEM, "registered_at": "2024-06-01T12:30:00Z"},
        "created_at": "2024-06-01T12:30:00Z",
        "updated_at": "2024-06-01T12:30:00Z",
    })
    fn = await get_tool(mcp, "create_sc_agent")
    result = await fn(agent_type="SIS", name="New Agent", public_key_1=PEM)
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
        advertised_version="19c",
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_register_sc_sidecar_listener_requires_advertised_version(mcp):
    required = (await mcp.get_tool(
        "register_sc_sidecar_listener")).parameters["required"]
    assert "advertised_version" in required


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
    _sis_agent(httpx_mock)
    httpx_mock.add_response(method="POST", status_code=201, json={
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


# ── Agents (remaining) ──────────────────────────────────────────────────

async def test_get_sc_agent_happy(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"id": "ag-1", "type": "SIS", "name": "a"})
    fn = await get_tool(mcp, "get_sc_agent")
    result = await fn(agent_id="ag-1")
    assert result["success"] is True


async def test_update_sc_agent_forwards_only_provided_fields(
        httpx_mock: HTTPXMock, test_env, mcp):
    """update_sc_agent only PATCHes the fields that were provided."""
    httpx_mock.add_response(json={"id": "ag-1"})
    fn = await get_tool(mcp, "update_sc_agent")
    result = await fn(
        agent_id="ag-1",
        name="renamed",
        description="new desc",
        public_key_1="key1",
        public_key_2="key2",
    )
    assert result["success"] is True
    body = json.loads(httpx_mock.get_request().content)
    assert body == {
        "name": "renamed",
        "description": "new desc",
        "public_key_1": "key1",
        "public_key_2": "key2",
    }


async def test_disconnect_sc_agent(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=204)
    fn = await get_tool(mcp, "disconnect_sc_agent")
    result = await fn(agent_id="ag-1")
    assert result["success"] is True


async def test_list_sc_agents_all_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    """list_sc_agents forwards limit/contiguous_id/type/name_starts_with."""
    httpx_mock.add_response(json={"agents": [], "contiguous_id": ""})
    fn = await get_tool(mcp, "list_sc_agents")
    result = await fn(
        limit=10,
        contiguous_id="cur",
        agent_type="SIS",
        name_starts_with="prod-",
    )
    assert result["success"] is True
    url = str(httpx_mock.get_request().url)
    for fragment in ("limit=10", "contiguous_id=cur",
                     "type=SIS", "name_starts_with=prod-"):
        assert fragment in url


async def test_create_sc_agent_all_optional_fields(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_sc_agent forwards description and both public keys."""
    httpx_mock.add_response(json={"id": "ag-x"})
    fn = await get_tool(mcp, "create_sc_agent")
    result = await fn(
        agent_type="CLASSIFIER",
        name="cl",
        description="d",
        public_key_1="k1",
        public_key_2="k2",
    )
    assert result["success"] is True
    body = json.loads(httpx_mock.get_request().content)
    assert body == {
        "type": "CLASSIFIER",
        "name": "cl",
        "description": "d",
        "public_key_1": "k1",
        "public_key_2": "k2",
    }


# ── Repos (remaining) ───────────────────────────────────────────────────

async def test_get_sc_repo(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"name": "r", "type": "Oracle"})
    fn = await get_tool(mcp, "get_sc_repo")
    result = await fn(repo_name="r")
    assert result["success"] is True


async def test_update_sc_repo(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"name": "r"})
    fn = await get_tool(mcp, "update_sc_repo")
    result = await fn(repo_name="r", redact_comments=True)
    assert result["success"] is True
    body = json.loads(httpx_mock.get_request().content)
    assert body == {"audit_properties": {"redact_comments": "*"}}


async def test_disconnect_sc_repo(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=204)
    fn = await get_tool(mcp, "disconnect_sc_repo")
    result = await fn(repo_name="r")
    assert result["success"] is True


async def test_list_sc_repos_with_type_filter(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"repos": [], "contiguous_id": ""})
    fn = await get_tool(mcp, "list_sc_repos")
    result = await fn(limit=20, contiguous_id="c", repo_type="Postgres")
    assert result["success"] is True
    url = str(httpx_mock.get_request().url)
    assert "limit=20" in url
    assert "contiguous_id=c" in url
    assert "type=Postgres" in url


async def test_create_sc_repo_with_description(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"name": "r"})
    fn = await get_tool(mcp, "create_sc_repo")
    result = await fn(
        name="r",
        repo_type="MySQL",
        hostname="h",
        port=3306,
        description="d",
    )
    assert result["success"] is True
    body = json.loads(httpx_mock.get_request().content)
    assert body["description"] == "d"


# ── Repo users ──────────────────────────────────────────────────────────

async def test_list_sc_repo_users(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"users": [], "contiguous_id": ""})
    fn = await get_tool(mcp, "list_sc_repo_users")
    result = await fn(repo_name="r", limit=5, contiguous_id="c")
    assert result["success"] is True


async def test_create_sc_repo_user_aws_dict(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"username": "u"})
    fn = await get_tool(mcp, "create_sc_repo_user")
    result = await fn(
        repo_name="r",
        username="u",
        aws_secrets_manager={"secrets_path": "/p", "iam_role": "arn:..."},
    )
    assert result["success"] is True
    body = json.loads(httpx_mock.get_request().content)
    assert body["aws_secrets_manager"]["secrets_path"] == "/p"


async def test_create_sc_repo_user_aws_json_string(
        httpx_mock: HTTPXMock, test_env, mcp):
    """JSON-string-typed credentials are parsed before sending."""
    httpx_mock.add_response(json={"username": "u"})
    fn = await get_tool(mcp, "create_sc_repo_user")
    result = await fn(
        repo_name="r",
        username="u",
        aws_secrets_manager='{"secrets_path": "/p"}',
    )
    assert result["success"] is True
    body = json.loads(httpx_mock.get_request().content)
    assert body["aws_secrets_manager"] == {"secrets_path": "/p"}


async def test_create_sc_repo_user_azure(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"username": "u"})
    fn = await get_tool(mcp, "create_sc_repo_user")
    result = await fn(
        repo_name="r",
        username="u",
        azure_key_vault={"key_vault_uri": "https://kv", "secret_name": "s"},
    )
    assert result["success"] is True


async def test_update_sc_repo_user(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"username": "u"})
    fn = await get_tool(mcp, "update_sc_repo_user")
    result = await fn(
        repo_name="r",
        username="u",
        aws_secrets_manager={"secrets_path": "/new"},
    )
    assert result["success"] is True


async def test_disconnect_sc_repo_user(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=204)
    fn = await get_tool(mcp, "disconnect_sc_repo_user")
    result = await fn(repo_name="r", username="u")
    assert result["success"] is True


# ── Service users (remaining) ───────────────────────────────────────────

async def test_list_sc_service_users_with_repo(
        httpx_mock: HTTPXMock, test_env, mcp):
    """list_sc_service_users with repo_name + username prefix filter."""
    httpx_mock.add_response(json={"service_users": [], "contiguous_id": ""})
    fn = await get_tool(mcp, "list_sc_service_users")
    result = await fn(
        repo_name="r",
        username_starts_with="svc",
        limit=10,
    )
    assert result["success"] is True


async def test_get_sc_service_user(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"username": "u"})
    fn = await get_tool(mcp, "get_sc_service_user")
    result = await fn(repo_name="r", username="u")
    assert result["success"] is True


async def test_update_sc_service_user(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"username": "u"})
    fn = await get_tool(mcp, "update_sc_service_user")
    result = await fn(
        repo_name="r",
        username="u",
        resource="new-resource",
        azure_key_vault='{"key_vault_uri": "https://kv", "secret_name": "s"}',
    )
    assert result["success"] is True


async def test_disconnect_sc_service_user(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=204)
    fn = await get_tool(mcp, "disconnect_sc_service_user")
    result = await fn(repo_name="r", username="u")
    assert result["success"] is True


# ── Sidecars (remaining) ────────────────────────────────────────────────

async def test_create_sc_sidecar(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"id": "s-1"})
    fn = await get_tool(mcp, "create_sc_sidecar")
    result = await fn(
        name="s",
        hostname="h",
        description="d",
        public_key_1="k1",
        public_key_2="k2",
        unsupported_query_bypass=True,
        disable_platform_audits=True,
    )
    assert result["success"] is True
    body = json.loads(httpx_mock.get_request().content)
    assert body["unsupported_query_bypass"] is True
    assert body["disable_platform_audits"] is True


async def test_get_sc_sidecar(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"id": "s-1"})
    fn = await get_tool(mcp, "get_sc_sidecar")
    result = await fn(sidecar_id="s-1")
    assert result["success"] is True


async def test_update_sc_sidecar(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"id": "s-1"})
    fn = await get_tool(mcp, "update_sc_sidecar")
    result = await fn(
        sidecar_id="s-1",
        name="renamed",
        hostname="h2",
        description="d",
        public_key_1="k1",
        public_key_2="k2",
        unsupported_query_bypass=False,
        disable_platform_audits=False,
    )
    assert result["success"] is True


async def test_disconnect_sc_sidecar(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=204)
    fn = await get_tool(mcp, "disconnect_sc_sidecar")
    result = await fn(sidecar_id="s-1")
    assert result["success"] is True


# ── Listeners (remaining) ───────────────────────────────────────────────

async def test_list_sc_sidecar_listeners(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"listeners": [], "contiguous_id": ""})
    fn = await get_tool(mcp, "list_sc_sidecar_listeners")
    result = await fn(sidecar_id="s-1", limit=10, contiguous_id="c")
    assert result["success"] is True


async def test_deregister_sc_sidecar_listener(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=204)
    fn = await get_tool(mcp, "deregister_sc_sidecar_listener")
    result = await fn(sidecar_id="s-1", port=3307)
    assert result["success"] is True


async def test_register_sc_sidecar_listener_with_version(
        httpx_mock: HTTPXMock, test_env, mcp):
    """register_sc_sidecar_listener forwards advertised_version."""
    httpx_mock.add_response(status_code=204, content=b"")
    fn = await get_tool(mcp, "register_sc_sidecar_listener")
    result = await fn(
        sidecar_id="s-1",
        port=5432,
        database_type="Postgres",
        advertised_version="14.5",
    )
    assert result["success"] is True
    body = json.loads(httpx_mock.get_request().content)
    assert body["advertised_version"] == "14.5"


# ── Bindings (remaining) ────────────────────────────────────────────────

async def test_list_sc_sidecar_bindings(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"bindings": [], "contiguous_id": ""})
    fn = await get_tool(mcp, "list_sc_sidecar_bindings")
    result = await fn(
        sidecar_id="s-1",
        ports="3307,3308",
        repo_names="a,b",
        limit=20,
        contiguous_id="c",
    )
    assert result["success"] is True


async def test_list_sc_repo_bindings(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"bindings": [], "contiguous_id": ""})
    fn = await get_tool(mcp, "list_sc_repo_bindings")
    result = await fn(
        repo_name="r",
        ports="3307",
        sidecar_ids="s-1,s-2",
        limit=15,
    )
    assert result["success"] is True


async def test_get_sc_sidecar_binding(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"port": 3307, "repo_name": "r"})
    fn = await get_tool(mcp, "get_sc_sidecar_binding")
    result = await fn(sidecar_id="s-1", port=3307, repo_name="r")
    assert result["success"] is True


async def test_disconnect_sc_sidecar_binding(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=204)
    fn = await get_tool(mcp, "disconnect_sc_sidecar_binding")
    result = await fn(sidecar_id="s-1", port=3307, repo_name="r")
    assert result["success"] is True


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


# --- Optional-argument coverage -----------------------------------------
#
# The tests above call one tool per resource type with the minimum required
# arguments, which leaves every `if arg is not None` branch half-covered.
# These pass *every* optional argument, so both sides of those branches are
# exercised -- including the `_parse_dict` JSON-string path, which the dict
# form never reaches.

async def test_parse_dict_accepts_a_json_string(
        httpx_mock: HTTPXMock, test_env, mcp):
    """A JSON string is decoded to a dict before being sent."""
    _sis_agent(httpx_mock, "a-1")
    httpx_mock.add_response(method="POST", json={"task_id": "t-1"})
    fn = await get_tool(mcp, "create_sc_agent_task")
    result = await fn(
        agent_id="a-1", name="task", repo_name="repo",
        configuration='{"key": "value"}',
        schedule='{"value": "0 * * * *", "timezone": "America/Chicago"}',
        description="desc", service_user="svc")
    assert result["success"] is True
    body = _sent(httpx_mock, "POST")
    assert body["configuration"] == {"key": "value"}
    assert body["schedule"] == {
        "type": "CRON", "value": "0 * * * *", "timezone": "America/Chicago"}
    assert body["description"] == "desc"
    assert body["service_user"] == "svc"


async def test_create_sc_agent_task_omits_optional_fields(
        httpx_mock: HTTPXMock, test_env, mcp):
    """description and service_user are optional."""
    _sis_agent(httpx_mock, "a-1")
    httpx_mock.add_response(method="POST", json={"task_id": "t-1"})
    fn = await get_tool(mcp, "create_sc_agent_task")
    result = await fn(
        agent_id="a-1", name="task", repo_name="repo",
        configuration={"k": "v"}, schedule={"value": "* * * * *"})
    assert result["success"] is True
    body = _sent(httpx_mock, "POST")
    assert "description" not in body
    assert "service_user" not in body


async def test_update_sc_agent_sends_every_field(
        httpx_mock: HTTPXMock, test_env, mcp):
    """All four optional fields reach the update body."""
    httpx_mock.add_response(json={"agent_id": "a-1"})
    fn = await get_tool(mcp, "update_sc_agent")
    result = await fn(
        agent_id="a-1", name="n", description="d",
        public_key_1="k1", public_key_2="k2")
    assert result["success"] is True
    assert json.loads(httpx_mock.get_requests()[0].content) == {
        "name": "n", "description": "d",
        "public_key_1": "k1", "public_key_2": "k2"}


async def test_update_sc_agent_task_sends_every_field(
        httpx_mock: HTTPXMock, test_env, mcp):
    """name/description/configuration/schedule all reach the body."""
    _sis_agent(httpx_mock, "a-1")
    httpx_mock.add_response(method="GET", url=f"{SC}/agents/a-1/tasks/t-1",
                            json={"schedule": {"type": "CRON", "value": "0 1 * * *"}})
    httpx_mock.add_response(method="PATCH", json={"task_id": "t-1"})
    fn = await get_tool(mcp, "update_sc_agent_task")
    result = await fn(
        agent_id="a-1", task_id="t-1", name="n", description="d",
        configuration={"k": "v"}, schedule={"value": "* * * * *"})
    assert result["success"] is True
    body = _sent(httpx_mock, "PATCH")
    assert set(body) == {"name", "description", "configuration", "schedule"}


async def test_create_sc_sidecar_sends_every_field(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Both bool flags and all optional strings reach the body."""
    httpx_mock.add_response(json={"sidecar_id": "s-1"})
    fn = await get_tool(mcp, "create_sc_sidecar")
    result = await fn(
        name="n", hostname="h", description="d",
        public_key_1="k1", public_key_2="k2",
        unsupported_query_bypass=True, disable_platform_audits=False)
    assert result["success"] is True
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["unsupported_query_bypass"] is True
    # False is a value, not an omission.
    assert body["disable_platform_audits"] is False


async def test_update_sc_sidecar_sends_every_field(
        httpx_mock: HTTPXMock, test_env, mcp):
    """All seven optional fields reach the body."""
    httpx_mock.add_response(json={"sidecar_id": "s-1"})
    fn = await get_tool(mcp, "update_sc_sidecar")
    result = await fn(
        sidecar_id="s-1", name="n", hostname="h", description="d",
        public_key_1="k1", public_key_2="k2",
        unsupported_query_bypass=False, disable_platform_audits=True)
    assert result["success"] is True
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert set(body) == {
        "name", "hostname", "description", "public_key_1",
        "public_key_2", "unsupported_query_bypass",
        "disable_platform_audits"}


async def test_update_sc_sidecar_with_no_fields_sends_an_empty_body(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Every field is optional, so the body can legitimately be empty."""
    httpx_mock.add_response(json={"sidecar_id": "s-1"})
    fn = await get_tool(mcp, "update_sc_sidecar")
    result = await fn(sidecar_id="s-1")
    assert result["success"] is True
    assert json.loads(httpx_mock.get_requests()[0].content) == {}


AZURE = {"key_vault_uri": "https://kv.vault.azure.net/", "secret_name": "s"}


async def test_update_sc_repo_user_parses_a_json_string_source(
        httpx_mock: HTTPXMock, test_env, mcp):
    """A credential source given as a JSON string is sent as an object."""
    httpx_mock.add_response(json={"username": "u"})
    fn = await get_tool(mcp, "update_sc_repo_user")
    result = await fn(
        repo_name="repo", username="u", azure_key_vault=json.dumps(AZURE))
    assert result["success"] is True
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["azure_key_vault"] == AZURE


async def test_create_sc_service_user_sends_azure_key_vault(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"username": "u"})
    fn = await get_tool(mcp, "create_sc_service_user")
    result = await fn(
        repo_name="repo", username="u", resource="res",
        azure_key_vault=AZURE)
    assert result["success"] is True
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["azure_key_vault"] == AZURE


async def test_update_sc_service_user_sends_every_field(
        httpx_mock: HTTPXMock, test_env, mcp):
    """resource and one credential source reach the body."""
    httpx_mock.add_response(json={"username": "u"})
    fn = await get_tool(mcp, "update_sc_service_user")
    result = await fn(
        repo_name="repo", username="u", resource="res",
        aws_secrets_manager={"secrets_path": "/p"})
    assert result["success"] is True
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert set(body) == {"resource", "aws_secrets_manager"}


@pytest.mark.parametrize("tool,extra", [
    ("create_sc_repo_user", {}),
    ("update_sc_repo_user", {}),
    ("create_sc_service_user", {"resource": "res"}),
    ("update_sc_service_user", {}),
])
async def test_user_tools_refuse_two_credential_sources(
        tool, extra, httpx_mock: HTTPXMock, test_env, mcp):
    """The API rejects a second source, so nothing is sent."""
    fn = await get_tool(mcp, tool)
    with pytest.raises(Exception, match="only one credential source"):
        await fn(repo_name="repo", username="u",
                 aws_secrets_manager={"secrets_path": "/p"},
                 azure_key_vault=AZURE, **extra)
    assert not httpx_mock.get_requests()


@pytest.mark.parametrize("tool,extra", [
    ("create_sc_repo_user", {}),
    ("update_sc_repo_user", {}),
    ("create_sc_service_user", {"resource": "res"}),
])
async def test_user_tools_refuse_no_credential_source(
        tool, extra, httpx_mock: HTTPXMock, test_env, mcp):
    """These calls need one source, so nothing is sent without it."""
    fn = await get_tool(mcp, tool)
    with pytest.raises(Exception, match="Give one credential source"):
        await fn(repo_name="repo", username="u", **extra)
    assert not httpx_mock.get_requests()


async def test_update_sc_service_user_refuses_an_empty_update(
        httpx_mock: HTTPXMock, test_env, mcp):
    fn = await get_tool(mcp, "update_sc_service_user")
    with pytest.raises(Exception, match="Give resource or one credential"):
        await fn(repo_name="repo", username="u")
    assert not httpx_mock.get_requests()


async def test_update_sc_service_user_needs_no_credential_source(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"username": "u"})
    fn = await get_tool(mcp, "update_sc_service_user")
    result = await fn(repo_name="repo", username="u", resource="res")
    assert result["success"] is True
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body == {"resource": "res"}


# --- list tools: pagination and filter arguments ------------------------

async def test_list_sc_sidecars_with_pagination(
        httpx_mock: HTTPXMock, test_env, mcp):
    """limit and contiguous_id are forwarded as query params."""
    httpx_mock.add_response(json={"sidecars": []})
    fn = await get_tool(mcp, "list_sc_sidecars")
    result = await fn(limit=10, contiguous_id="tok")
    assert result["success"] is True
    url = str(httpx_mock.get_requests()[0].url)
    assert "limit=10" in url and "contiguous_id=tok" in url


async def test_list_sc_agent_tasks_with_pagination(
        httpx_mock: HTTPXMock, test_env, mcp):
    """limit and contiguous_id are forwarded as query params."""
    httpx_mock.add_response(json={"tasks": []})
    fn = await get_tool(mcp, "list_sc_agent_tasks")
    result = await fn(agent_id="a-1", limit=10, contiguous_id="tok")
    assert result["success"] is True
    url = str(httpx_mock.get_requests()[0].url)
    assert "limit=10" in url and "contiguous_id=tok" in url


async def test_list_sc_repo_users_with_pagination(
        httpx_mock: HTTPXMock, test_env, mcp):
    """limit and contiguous_id are forwarded as query params."""
    httpx_mock.add_response(json={"users": []})
    fn = await get_tool(mcp, "list_sc_repo_users")
    result = await fn(repo_name="repo", limit=10, contiguous_id="tok")
    assert result["success"] is True
    url = str(httpx_mock.get_requests()[0].url)
    assert "limit=10" in url and "contiguous_id=tok" in url


async def test_list_sc_service_users_with_repo_uses_repo_endpoint(
        httpx_mock: HTTPXMock, test_env, mcp):
    """repo_name selects the per-repo endpoint, so it is a path segment.

    Passing it routes to list_repo_service_users instead of
    list_service_users; together with test_list_sc_service_users_no_repo
    above, both sides of that branch are covered.
    """
    httpx_mock.add_response(json={"service_users": []})
    fn = await get_tool(mcp, "list_sc_service_users")
    result = await fn(
        repo_name="repo", limit=10, contiguous_id="tok",
        username_starts_with="svc")
    assert result["success"] is True
    url = httpx_mock.get_requests()[0].url
    assert url.path.endswith("/repos/repo/serviceusers")
    for expected in ("limit=10", "contiguous_id=tok",
                     "username_starts_with=svc"):
        assert expected in str(url)


async def test_list_sc_sidecar_listeners_with_pagination(
        httpx_mock: HTTPXMock, test_env, mcp):
    """limit and contiguous_id are forwarded as query params."""
    httpx_mock.add_response(json={"listeners": []})
    fn = await get_tool(mcp, "list_sc_sidecar_listeners")
    result = await fn(sidecar_id="s-1", limit=10, contiguous_id="tok")
    assert result["success"] is True
    url = str(httpx_mock.get_requests()[0].url)
    assert "limit=10" in url and "contiguous_id=tok" in url


async def test_list_sc_sidecar_bindings_with_every_filter(
        httpx_mock: HTTPXMock, test_env, mcp):
    """ports, repo_names and pagination are all forwarded."""
    httpx_mock.add_response(json={"bindings": []})
    fn = await get_tool(mcp, "list_sc_sidecar_bindings")
    result = await fn(
        sidecar_id="s-1", ports="5432", repo_names="repo",
        limit=10, contiguous_id="tok")
    assert result["success"] is True
    url = str(httpx_mock.get_requests()[0].url)
    for expected in ("ports=5432", "repo_names=repo",
                     "limit=10", "contiguous_id=tok"):
        assert expected in url


async def test_list_sc_repo_bindings_with_every_filter(
        httpx_mock: HTTPXMock, test_env, mcp):
    """ports, sidecar_ids and pagination are all forwarded."""
    httpx_mock.add_response(json={"bindings": []})
    fn = await get_tool(mcp, "list_sc_repo_bindings")
    result = await fn(
        repo_name="repo", ports="5432", sidecar_ids="s-1",
        limit=10, contiguous_id="tok")
    assert result["success"] is True
    url = str(httpx_mock.get_requests()[0].url)
    for expected in ("ports=5432", "sidecar_ids=s-1",
                     "limit=10", "contiguous_id=tok"):
        assert expected in url


# ── Repo properties, credential sources, task lookup ────────────────────

async def test_get_sc_agent_task(httpx_mock: HTTPXMock, test_env, mcp):
    """get_sc_agent_task reads one task by agent and task ID."""
    httpx_mock.add_response(json={"id": "t-1", "agent_id": "a-1"})
    fn = await get_tool(mcp, "get_sc_agent_task")
    result = await fn(agent_id="a-1", task_id="t-1")
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert request.method == "GET"
    assert request.url.path.endswith("/v1/agents/a-1/tasks/t-1")


async def test_list_sc_repos_with_name_filter(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"repos": [], "contiguous_id": ""})
    fn = await get_tool(mcp, "list_sc_repos")
    result = await fn(repo_type="S3", name_starts_with="raw")
    assert result["success"] is True
    params = httpx_mock.get_request().url.params
    assert params["repo_type"] == "S3"
    assert params["name_starts_with"] == "raw"


async def test_create_sc_repo_for_a_file_store_omits_hostname_and_port(
        httpx_mock: HTTPXMock, test_env, mcp):
    """S3 and FILESYSTEM repos reject hostname and port, so none is sent."""
    httpx_mock.add_response(json={"name": "landing"})
    fn = await get_tool(mcp, "create_sc_repo")
    result = await fn(
        name="landing", repo_type="S3",
        connection_properties='{"bucket": "b", "region": "us-east-1"}',
        audit_properties={"redact_comments": "*"})
    assert result["success"] is True
    body = json.loads(httpx_mock.get_request().content)
    assert body == {
        "name": "landing",
        "type": "S3",
        "connection_properties": {"bucket": "b", "region": "us-east-1"},
        "audit_properties": {"redact_comments": "*"},
    }


async def test_update_sc_repo_sends_only_given_fields(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"name": "landing"})
    fn = await get_tool(mcp, "update_sc_repo")
    result = await fn(repo_name="landing", redact_comments=False)
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert request.method == "PATCH"
    assert json.loads(request.content) == {
        "audit_properties": {"redact_comments": ""}}


async def test_create_sc_repo_user_sends_environment_variable(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"username": "u"})
    fn = await get_tool(mcp, "create_sc_repo_user")
    result = await fn(
        repo_name="repo", username="u",
        environment_variable='{"variable_name": "DB_PASSWORD"}')
    assert result["success"] is True
    body = json.loads(httpx_mock.get_request().content)
    assert body == {
        "username": "u",
        "environment_variable": {"variable_name": "DB_PASSWORD"},
    }


async def test_update_sc_service_user_sends_secret_file(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"username": "u"})
    fn = await get_tool(mcp, "update_sc_service_user")
    result = await fn(
        repo_name="repo", username="u",
        secret_file={"path": "db_password"})
    assert result["success"] is True
    body = json.loads(httpx_mock.get_request().content)
    assert body == {"secret_file": {"path": "db_password"}}


# --- Console parity and API rules -----------------------------------------

@pytest.mark.parametrize("tool", ["create_sc_agent", "create_sc_sidecar"])
async def test_a_create_without_a_public_key_is_refused(
        httpx_mock: HTTPXMock, test_env, mcp, tool):
    """The API needs at least one PEM key; the spec doesn't say so."""
    kwargs = ({"agent_type": "SIS", "name": "a"} if tool == "create_sc_agent"
              else {"name": "s", "hostname": "h"})
    with pytest.raises(ToolError, match="at least one PEM public key"):
        await (await get_tool(mcp, tool))(**kwargs)
    assert not httpx_mock.get_requests()


async def test_a_classifier_task_is_built_as_the_console_builds_it(
        httpx_mock: HTTPXMock, test_env, mcp):
    _classifier(httpx_mock)
    httpx_mock.add_response(method="POST", json={"id": "t-1"})
    fn = await get_tool(mcp, "create_sc_agent_task")
    await fn(agent_id="a-1", name="scan", repo_name="repo",
             configuration={"collection_name": "pii"},
             schedule={"value": "0 2 * * *"}, service_user="svc")
    assert _sent(httpx_mock, "POST")["configuration"] == {
        "collection_name": "pii",
        "classification_type": 5,
        "sample_strategy": "ROWS",
        "condition_types": CONDITION_TYPES,
        "sample_type": "ROWS",
        "sample_size": 1000,
    }


async def test_a_percent_sample_defaults_to_five(
        httpx_mock: HTTPXMock, test_env, mcp):
    _classifier(httpx_mock)
    httpx_mock.add_response(method="POST", json={"id": "t-1"})
    fn = await get_tool(mcp, "create_sc_agent_task")
    await fn(agent_id="a-1", name="scan", repo_name="repo",
             configuration={"collection_name": "pii", "sample_type": "percent"},
             schedule={"value": "0 2 * * *"}, service_user="svc")
    config = _sent(httpx_mock, "POST")["configuration"]
    assert (config["sample_type"], config["sample_size"]) == ("PERCENT", 5)


async def test_a_file_repo_task_gets_hashed_metadata_and_no_sample(
        httpx_mock: HTTPXMock, test_env, mcp):
    _classifier(httpx_mock, repo_type="S3")
    httpx_mock.add_response(method="POST", json={"id": "t-1"})
    fn = await get_tool(mcp, "create_sc_agent_task")
    await fn(agent_id="a-1", name="scan", repo_name="repo",
             configuration={"collection_name": "pii"},
             schedule={"value": "0 2 * * *"}, service_user="svc")
    config = _sent(httpx_mock, "POST")["configuration"]
    assert config["metadata_map"] == {"default": "hashed"}
    assert "sample_type" not in config and "sample_size" not in config


@pytest.mark.parametrize("key, value", [
    ("classification_type", 6), ("sample_strategy", "METADATA"),
    ("condition_types", ["ROW_DATA"])])
async def test_classifier_settings_the_console_fixes_are_refused(
        httpx_mock: HTTPXMock, test_env, mcp, key, value):
    _classifier(httpx_mock)
    fn = await get_tool(mcp, "create_sc_agent_task")
    with pytest.raises(ToolError, match=key):
        await fn(agent_id="a-1", name="scan", repo_name="repo",
                 configuration={"collection_name": "pii", key: value},
                 schedule={"value": "0 2 * * *"}, service_user="svc")
    assert not [r for r in httpx_mock.get_requests() if r.method == "POST"]


async def test_a_classifier_task_update_resets_the_console_settings(
        httpx_mock: HTTPXMock, test_env, mcp):
    _classifier(httpx_mock, repo_type=None)
    httpx_mock.add_response(method="PATCH", json={"id": "t-1"})
    fn = await get_tool(mcp, "update_sc_agent_task")
    await fn(agent_id="a-1", task_id="t-1",
             configuration={"requires_review": True})
    assert _sent(httpx_mock, "PATCH")["configuration"] == {
        "requires_review": True,
        "classification_type": 5,
        "sample_strategy": "ROWS",
        "condition_types": CONDITION_TYPES,
    }


async def test_a_schedule_update_keeps_the_stored_timezone_and_duration(
        httpx_mock: HTTPXMock, test_env, mcp):
    """The API replaces the schedule whole; leaving timezone out resets it."""
    httpx_mock.add_response(
        method="GET", url=f"{SC}/agents/a-1/tasks/t-1",
        json={"schedule": {"type": "CRON", "value": "0 1 * * *",
                           "timezone": "Europe/Berlin", "max_duration": "PT2H"}})
    httpx_mock.add_response(method="PATCH", json={"id": "t-1"})
    fn = await get_tool(mcp, "update_sc_agent_task")
    await fn(agent_id="a-1", task_id="t-1", schedule={"value": "30 4 * * 1"})
    assert _sent(httpx_mock, "PATCH") == {"schedule": {
        "type": "CRON", "value": "30 4 * * 1",
        "timezone": "Europe/Berlin", "max_duration": "PT2H"}}


@pytest.mark.parametrize("schedule, message", [
    ({"value": "0 0 2 * * ?"}, "5-field cron"),
    ({"value": "@daily"}, "5-field cron"),
    ({"type": "INTERVAL", "value": "0 2 * * *"}, "CRON"),
])
async def test_a_schedule_the_agent_cannot_run_is_refused(
        httpx_mock: HTTPXMock, test_env, mcp, schedule, message):
    fn = await get_tool(mcp, "create_sc_agent_task")
    with pytest.raises(ToolError, match=message):
        await fn(agent_id="a-1", name="t", repo_name="repo",
                 configuration={}, schedule=schedule)
    assert not httpx_mock.get_requests()


async def test_a_repo_service_user_list_drops_other_repos(
        httpx_mock: HTTPXMock, test_env, mcp):
    """The API also returns users of repos whose names start with this one."""
    httpx_mock.add_response(json={"service_users": [
        {"username": "a", "repo_name": "sales"},
        {"username": "b", "repo_name": "sales_eu"}], "contiguous_id": "x"})
    fn = await get_tool(mcp, "list_sc_service_users")
    result = await fn(repo_name="sales")
    assert result["data"] == {
        "service_users": [{"username": "a", "repo_name": "sales"}],
        "contiguous_id": "x"}


@pytest.mark.parametrize("failing", ["agent", "repo"])
async def test_a_failed_read_stops_the_task_create(
        httpx_mock: HTTPXMock, test_env, mcp, failing):
    if failing == "repo":
        httpx_mock.add_response(method="GET", url=f"{SC}/agents/a-1",
                                json={"id": "a-1", "type": "CLASSIFIER"})
    url = f"{SC}/agents/a-1" if failing == "agent" else f"{SC}/repos/repo"
    httpx_mock.add_response(method="GET", url=url, status_code=404,
                            text="not found")
    fn = await get_tool(mcp, "create_sc_agent_task")
    with pytest.raises(ToolError, match=f"Could not read {failing} .*HTTP 404: not found"):
        await fn(agent_id="a-1", name="t", repo_name="repo",
                 configuration={"collection_name": "pii"},
                 schedule={"value": "0 2 * * *"})
    assert not [r for r in httpx_mock.get_requests() if r.method == "POST"]


async def test_a_failed_task_read_stops_the_schedule_update(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", url=f"{SC}/agents/a-1/tasks/t-1",
                            status_code=404, text="not found")
    fn = await get_tool(mcp, "update_sc_agent_task")
    with pytest.raises(ToolError, match="Could not read task t-1"):
        await fn(agent_id="a-1", task_id="t-1", schedule={"value": "0 2 * * *"})
    assert not [r for r in httpx_mock.get_requests() if r.method == "PATCH"]


@pytest.mark.parametrize("stored, sent, size", [
    ({"sample_type": "ROWS", "sample_size": 1000}, "percent", 5),
    ({"sample_type": "PERCENT", "sample_size": 20}, "PERCENT", None),
    ({}, "rows", 1000),
])
async def test_a_sample_type_update_gets_a_size_only_when_it_changes(
        httpx_mock: HTTPXMock, test_env, mcp, stored, sent, size):
    """The API merges the stored size; PERCENT can't keep 1000 rows."""
    _classifier(httpx_mock, repo_type=None)
    httpx_mock.add_response(method="GET", url=f"{SC}/agents/a-1/tasks/t-1",
                            json={"configuration": stored})
    httpx_mock.add_response(method="PATCH", json={"id": "t-1"})
    fn = await get_tool(mcp, "update_sc_agent_task")
    await fn(agent_id="a-1", task_id="t-1",
             configuration={"sample_type": sent})
    config = _sent(httpx_mock, "PATCH")["configuration"]
    assert config["sample_type"] == sent.upper()
    assert config.get("sample_size") == size


async def test_a_failed_agent_read_stops_the_configuration_update(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(method="GET", url=f"{SC}/agents/a-1",
                            status_code=404, text="not found")
    fn = await get_tool(mcp, "update_sc_agent_task")
    with pytest.raises(ToolError, match="Could not read agent a-1"):
        await fn(agent_id="a-1", task_id="t-1",
                 configuration={"collection_name": "pii"})
    assert not [r for r in httpx_mock.get_requests() if r.method == "PATCH"]


async def test_a_timezone_update_keeps_a_stored_value_it_wouldnt_accept(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Only a value the caller sends is checked; the API never checked it."""
    httpx_mock.add_response(
        method="GET", url=f"{SC}/agents/a-1/tasks/t-1",
        json={"schedule": {"type": "CRON", "value": "0 0 2 * * ?"}})
    httpx_mock.add_response(method="PATCH", json={"id": "t-1"})
    fn = await get_tool(mcp, "update_sc_agent_task")
    await fn(agent_id="a-1", task_id="t-1", schedule={"timezone": "Europe/Berlin"})
    assert _sent(httpx_mock, "PATCH")["schedule"] == {
        "type": "CRON", "value": "0 0 2 * * ?", "timezone": "Europe/Berlin"}
