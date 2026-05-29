from altr_mcp.utils import api
from altr_mcp.settings import get_settings


# ── Audit Report definitions ─────────────────────────────────────────────────

def _base():
    return f"{get_settings().audit_report_base_url}/audit-reports/definitions"


async def list_definitions(auth, params: dict) -> dict:
    url = _base() + "/"
    return await api.request("GET", url, auth, params)


async def create_definition(auth, data: dict) -> dict:
    url = _base() + "/"
    return await api.request("POST", url, auth, {}, data)


async def get_definition(auth, definition_id: str) -> dict:
    url = f"{_base()}/{definition_id}"
    return await api.request("GET", url, auth, {})


async def update_definition(auth, definition_id: str, data: dict) -> dict:
    url = f"{_base()}/{definition_id}"
    return await api.request("PUT", url, auth, {}, data)


async def archive_definition(auth, definition_id: str) -> dict:
    url = f"{_base()}/{definition_id}"
    return await api.request("DELETE", url, auth, {})


async def restore_definition(auth, definition_id: str) -> dict:
    url = f"{_base()}/{definition_id}/restore"
    return await api.request("POST", url, auth, {})


async def trigger_definition(auth, definition_id: str) -> dict:
    url = f"{_base()}/{definition_id}/trigger"
    return await api.request("POST", url, auth, {})


# ── Audit Report instances ────────────────────────────────────────────────────

def _instances_base(definition_id: str):
    return f"{_base()}/{definition_id}/instances"


async def list_instances(auth, definition_id: str, params: dict) -> dict:
    url = _instances_base(definition_id) + "/"
    return await api.request("GET", url, auth, params)


async def get_instance(
        auth, definition_id: str, instance_id: str) -> dict:
    url = f"{_instances_base(definition_id)}/{instance_id}"
    return await api.request("GET", url, auth, {})


async def get_instance_download_url(
        auth, definition_id: str, instance_id: str,
        params: dict) -> dict:
    url = f"{_instances_base(definition_id)}/{instance_id}/download"
    return await api.request("GET", url, auth, params)


# ── Audit Report instance comments ───────────────────────────────────────────

def _comments_base(definition_id: str, instance_id: str):
    return (
        f"{_instances_base(definition_id)}/{instance_id}/comments"
    )


async def list_comments(
        auth, definition_id: str, instance_id: str,
        params: dict) -> dict:
    url = _comments_base(definition_id, instance_id) + "/"
    return await api.request("GET", url, auth, params)


async def create_comment(
        auth, definition_id: str, instance_id: str,
        data: dict) -> dict:
    url = _comments_base(definition_id, instance_id) + "/"
    return await api.request("POST", url, auth, {}, data)


async def pin_comment(
        auth, definition_id: str, instance_id: str,
        comment_id: str) -> dict:
    url = (
        f"{_comments_base(definition_id, instance_id)}"
        f"/{comment_id}/pin"
    )
    return await api.request("POST", url, auth, {})


async def unpin_comment(
        auth, definition_id: str, instance_id: str,
        comment_id: str) -> dict:
    url = (
        f"{_comments_base(definition_id, instance_id)}"
        f"/{comment_id}/unpin"
    )
    return await api.request("POST", url, auth, {})


# ── Audit Report instance sign-offs ──────────────────────────────────────────

def _sign_off_base(definition_id: str, instance_id: str):
    return (
        f"{_instances_base(definition_id)}/{instance_id}/sign_off"
    )


async def get_sign_off(
        auth, definition_id: str, instance_id: str) -> dict:
    url = _sign_off_base(definition_id, instance_id)
    return await api.request("GET", url, auth, {})


async def create_sign_off(
        auth, definition_id: str, instance_id: str,
        data: dict) -> dict:
    url = _sign_off_base(definition_id, instance_id)
    return await api.request("POST", url, auth, {}, data)


async def list_sign_offs(
        auth, definition_id: str, instance_id: str,
        params: dict) -> dict:
    url = (
        f"{_instances_base(definition_id)}/{instance_id}/sign_offs"
    )
    return await api.request("GET", url, auth, params)
