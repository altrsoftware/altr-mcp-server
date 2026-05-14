import structlog
from altr_mcp.utils import api
from altr_mcp.settings import get_settings
import urllib.parse

logger = structlog.get_logger(__name__)


def _base(org_id: str):
    return f"{get_settings().sc_control_base_url}/v1"


# --- Agents ---

async def list_agents(auth, org_id: str, params: dict) -> dict:
    url = f"{_base(org_id)}/agents"
    return await api.request("GET", url, auth, params)


async def create_agent(auth, org_id: str, data: dict) -> dict:
    url = f"{_base(org_id)}/agents"
    return await api.request("POST", url, auth, {}, data)


async def get_agent(auth, org_id: str, agent_id: str) -> dict:
    url = f"{_base(org_id)}/agents/{agent_id}"
    return await api.request("GET", url, auth, {})


async def update_agent(auth, org_id: str, agent_id: str, data: dict) -> dict:
    url = f"{_base(org_id)}/agents/{agent_id}"
    return await api.request("PATCH", url, auth, {}, data)


async def delete_agent(auth, org_id: str, agent_id: str) -> dict:
    url = f"{_base(org_id)}/agents/{agent_id}"
    return await api.request("DELETE", url, auth, {})


# --- Agent Tasks ---

async def list_agent_tasks(
        auth, org_id: str, agent_id: str, params: dict) -> dict:
    url = f"{_base(org_id)}/agents/{agent_id}/tasks"
    return await api.request("GET", url, auth, params)


async def create_agent_task(
        auth, org_id: str, agent_id: str, data: dict) -> dict:
    url = f"{_base(org_id)}/agents/{agent_id}/tasks"
    return await api.request("POST", url, auth, {}, data)


async def update_agent_task(
        auth, org_id: str, agent_id: str,
        task_id: str, data: dict) -> dict:
    task_enc = urllib.parse.quote(task_id, safe='')
    url = (
        f"{_base(org_id)}/agents/{agent_id}"
        f"/tasks/{task_enc}"
    )
    return await api.request("PATCH", url, auth, {}, data)


async def delete_agent_task(
        auth, org_id: str, agent_id: str, task_id: str) -> dict:
    task_enc = urllib.parse.quote(task_id, safe='')
    url = (
        f"{_base(org_id)}/agents/{agent_id}"
        f"/tasks/{task_enc}"
    )
    return await api.request("DELETE", url, auth, {})


# --- Repos ---

async def list_repos(auth, org_id: str, params: dict) -> dict:
    url = f"{_base(org_id)}/repos"
    return await api.request("GET", url, auth, params)


async def create_repo(auth, org_id: str, data: dict) -> dict:
    url = f"{_base(org_id)}/repos"
    return await api.request("POST", url, auth, {}, data)


async def get_repo(auth, org_id: str, repo_name: str) -> dict:
    encoded = urllib.parse.quote(repo_name, safe='')
    url = f"{_base(org_id)}/repos/{encoded}"
    return await api.request("GET", url, auth, {})


async def update_repo(
        auth, org_id: str, repo_name: str, data: dict) -> dict:
    encoded = urllib.parse.quote(repo_name, safe='')
    url = f"{_base(org_id)}/repos/{encoded}"
    return await api.request("PATCH", url, auth, {}, data)


async def delete_repo(auth, org_id: str, repo_name: str) -> dict:
    encoded = urllib.parse.quote(repo_name, safe='')
    url = f"{_base(org_id)}/repos/{encoded}"
    return await api.request("DELETE", url, auth, {})


# --- Repo Users ---

async def list_repo_users(
        auth, org_id: str, repo_name: str, params: dict) -> dict:
    encoded = urllib.parse.quote(repo_name, safe='')
    url = f"{_base(org_id)}/repos/{encoded}/users"
    return await api.request("GET", url, auth, params)


async def create_repo_user(
        auth, org_id: str, repo_name: str, data: dict) -> dict:
    encoded = urllib.parse.quote(repo_name, safe='')
    url = f"{_base(org_id)}/repos/{encoded}/users"
    return await api.request("POST", url, auth, {}, data)


async def get_repo_user(
        auth, org_id: str, repo_name: str, username: str) -> dict:
    repo_enc = urllib.parse.quote(repo_name, safe='')
    user_enc = urllib.parse.quote(username, safe='')
    url = f"{_base(org_id)}/repos/{repo_enc}/users/{user_enc}"
    return await api.request("GET", url, auth, {})


async def update_repo_user(
        auth, org_id: str, repo_name: str,
        username: str, data: dict) -> dict:
    repo_enc = urllib.parse.quote(repo_name, safe='')
    user_enc = urllib.parse.quote(username, safe='')
    url = f"{_base(org_id)}/repos/{repo_enc}/users/{user_enc}"
    return await api.request("PATCH", url, auth, {}, data)


async def delete_repo_user(
        auth, org_id: str, repo_name: str, username: str) -> dict:
    repo_enc = urllib.parse.quote(repo_name, safe='')
    user_enc = urllib.parse.quote(username, safe='')
    url = f"{_base(org_id)}/repos/{repo_enc}/users/{user_enc}"
    return await api.request("DELETE", url, auth, {})


# --- Service Users ---

async def list_service_users(auth, org_id: str, params: dict) -> dict:
    url = f"{_base(org_id)}/serviceusers"
    return await api.request("GET", url, auth, params)


async def list_repo_service_users(
        auth, org_id: str, repo_name: str, params: dict) -> dict:
    encoded = urllib.parse.quote(repo_name, safe='')
    url = f"{_base(org_id)}/repos/{encoded}/serviceusers"
    return await api.request("GET", url, auth, params)


async def create_service_user(
        auth, org_id: str, repo_name: str, data: dict) -> dict:
    encoded = urllib.parse.quote(repo_name, safe='')
    url = f"{_base(org_id)}/repos/{encoded}/serviceusers"
    return await api.request("POST", url, auth, {}, data)


async def get_service_user(
        auth, org_id: str, repo_name: str, username: str) -> dict:
    repo_enc = urllib.parse.quote(repo_name, safe='')
    user_enc = urllib.parse.quote(username, safe='')
    url = f"{_base(org_id)}/repos/{repo_enc}/serviceusers/{user_enc}"
    return await api.request("GET", url, auth, {})


async def update_service_user(
        auth, org_id: str, repo_name: str,
        username: str, data: dict) -> dict:
    repo_enc = urllib.parse.quote(repo_name, safe='')
    user_enc = urllib.parse.quote(username, safe='')
    url = f"{_base(org_id)}/repos/{repo_enc}/serviceusers/{user_enc}"
    return await api.request("PATCH", url, auth, {}, data)


async def delete_service_user(
        auth, org_id: str, repo_name: str, username: str) -> dict:
    repo_enc = urllib.parse.quote(repo_name, safe='')
    user_enc = urllib.parse.quote(username, safe='')
    url = f"{_base(org_id)}/repos/{repo_enc}/serviceusers/{user_enc}"
    return await api.request("DELETE", url, auth, {})


# --- Sidecars ---

async def list_sidecars(auth, org_id: str, params: dict) -> dict:
    url = f"{_base(org_id)}/sidecars"
    return await api.request("GET", url, auth, params)


async def create_sidecar(auth, org_id: str, data: dict) -> dict:
    url = f"{_base(org_id)}/sidecars"
    return await api.request("POST", url, auth, {}, data)


async def get_sidecar(auth, org_id: str, sidecar_id: str) -> dict:
    url = f"{_base(org_id)}/sidecars/{sidecar_id}"
    return await api.request("GET", url, auth, {})


async def update_sidecar(
        auth, org_id: str, sidecar_id: str, data: dict) -> dict:
    url = f"{_base(org_id)}/sidecars/{sidecar_id}"
    return await api.request("PATCH", url, auth, {}, data)


async def delete_sidecar(auth, org_id: str, sidecar_id: str) -> dict:
    url = f"{_base(org_id)}/sidecars/{sidecar_id}"
    return await api.request("DELETE", url, auth, {})


# --- Sidecar Listeners ---

async def list_sidecar_listeners(
        auth, org_id: str, sidecar_id: str, params: dict) -> dict:
    url = f"{_base(org_id)}/sidecars/{sidecar_id}/ports"
    return await api.request("GET", url, auth, params)


async def register_sidecar_listener(
        auth, org_id: str, sidecar_id: str, data: dict) -> dict:
    url = f"{_base(org_id)}/sidecars/{sidecar_id}/ports"
    return await api.request("POST", url, auth, {}, data)


async def deregister_sidecar_listener(
        auth, org_id: str, sidecar_id: str, port: int) -> dict:
    url = f"{_base(org_id)}/sidecars/{sidecar_id}/ports/{port}"
    return await api.request("DELETE", url, auth, {})


# --- Repo Sidecar Bindings ---

async def list_sidecar_bindings(
        auth, org_id: str, sidecar_id: str, params: dict) -> dict:
    url = f"{_base(org_id)}/sidecars/{sidecar_id}/bindings"
    return await api.request("GET", url, auth, params)


async def list_repo_bindings(
        auth, org_id: str, repo_name: str, params: dict) -> dict:
    encoded = urllib.parse.quote(repo_name, safe='')
    url = f"{_base(org_id)}/repos/{encoded}/bindings"
    return await api.request("GET", url, auth, params)


async def get_sidecar_binding(
        auth, org_id: str, sidecar_id: str,
        port: int, repo_name: str) -> dict:
    repo_enc = urllib.parse.quote(repo_name, safe='')
    url = (
        f"{_base(org_id)}/sidecars/{sidecar_id}"
        f"/bindings/ports/{port}/repos/{repo_enc}"
    )
    return await api.request("GET", url, auth, {})


async def create_sidecar_binding(
        auth, org_id: str, sidecar_id: str,
        port: int, repo_name: str) -> dict:
    repo_enc = urllib.parse.quote(repo_name, safe='')
    url = (
        f"{_base(org_id)}/sidecars/{sidecar_id}"
        f"/bindings/ports/{port}/repos/{repo_enc}"
    )
    return await api.request("POST", url, auth, {})


async def delete_sidecar_binding(
        auth, org_id: str, sidecar_id: str,
        port: int, repo_name: str) -> dict:
    repo_enc = urllib.parse.quote(repo_name, safe='')
    url = (
        f"{_base(org_id)}/sidecars/{sidecar_id}"
        f"/bindings/ports/{port}/repos/{repo_enc}"
    )
    return await api.request("DELETE", url, auth, {})
