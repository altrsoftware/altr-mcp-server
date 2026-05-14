import structlog
from altr_mcp.utils import api
from altr_mcp.settings import get_settings

logger = structlog.get_logger(__name__)


def _base(org_id: str):
    return f"{get_settings().sc_control_base_url}/v1"


# --- Agent instances ---

async def get_agent_instances(
        auth, org_id: str, agent_id: str, params: dict) -> dict:
    url = f"{_base(org_id)}/agents/{agent_id}/instances"
    return await api.request("GET", url, auth, params)


async def get_agent_instance(
        auth, org_id: str, agent_id: str, instance_id: str) -> dict:
    url = f"{_base(org_id)}/agents/{agent_id}/instances/{instance_id}"
    return await api.request("GET", url, auth, {})


async def delete_agent_instance(
        auth, org_id: str, agent_id: str, instance_id: str) -> dict:
    url = f"{_base(org_id)}/agents/{agent_id}/instances/{instance_id}"
    return await api.request("DELETE", url, auth, {})


# --- Agent task telemetry ---

async def get_agent_task_telemetry(
        auth, org_id: str, agent_id: str, params: dict) -> dict:
    url = f"{_base(org_id)}/agents/{agent_id}/task-telemetry"
    return await api.request("GET", url, auth, params)


# --- Sidecar instances ---

async def get_sidecar_instances(
        auth, org_id: str, sidecar_id: str, params: dict) -> dict:
    url = f"{_base(org_id)}/sidecars/{sidecar_id}/instances"
    return await api.request("GET", url, auth, params)


async def get_sidecar_instance(
        auth, org_id: str, sidecar_id: str, instance_id: str) -> dict:
    url = f"{_base(org_id)}/sidecars/{sidecar_id}/instances/{instance_id}"
    return await api.request("GET", url, auth, {})


async def delete_sidecar_instance(
        auth, org_id: str, sidecar_id: str, instance_id: str) -> dict:
    url = f"{_base(org_id)}/sidecars/{sidecar_id}/instances/{instance_id}"
    return await api.request("DELETE", url, auth, {})


# --- Task telemetry ---

async def get_task_telemetry(
        auth, org_id: str, task_id: str) -> dict:
    url = f"{_base(org_id)}/tasks/{task_id}/task-telemetry"
    return await api.request("GET", url, auth, {})


async def delete_task_telemetry(
        auth, org_id: str, task_id: str) -> dict:
    url = f"{_base(org_id)}/tasks/{task_id}/task-telemetry"
    return await api.request("DELETE", url, auth, {})
