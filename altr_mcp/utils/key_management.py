from altr_mcp.utils import api
from altr_mcp.settings import get_settings


def _base():
    return get_settings().kma_base_url


# ── Tweaks ───────────────────────────────────────────────────────────────────

async def list_tweaks(auth, params: dict) -> dict:
    url = f"{_base()}/tweaks"
    return await api.request("GET", url, auth, params)


async def get_tweak(auth, name: str, params: dict) -> dict:
    url = f"{_base()}/tweaks/{name}"
    return await api.request("GET", url, auth, params)


async def create_tweak(auth, data: dict) -> dict:
    url = f"{_base()}/tweaks"
    return await api.request("POST", url, auth, {}, data)


async def deactivate_tweak(auth, name: str, sequence: str) -> dict:
    url = f"{_base()}/tweaks/{name}/sequence/{sequence}/deactivate"
    return await api.request("PATCH", url, auth, {})


# ── Keys ─────────────────────────────────────────────────────────────────────

async def list_keys(auth, namespace: str, params: dict) -> dict:
    url = f"{_base()}/keys/{namespace}"
    return await api.request("GET", url, auth, params)


async def get_key(auth, namespace: str, name: str, params: dict) -> dict:
    url = f"{_base()}/keys/{namespace}/{name}"
    return await api.request("GET", url, auth, params)


async def create_key(auth, data: dict) -> dict:
    url = f"{_base()}/keys"
    return await api.request("POST", url, auth, {}, data)


async def deactivate_key(
        auth, namespace: str, name: str, sequence: str) -> dict:
    url = f"{_base()}/keys/{namespace}/{name}/sequence/{sequence}/deactivate"
    return await api.request("PATCH", url, auth, {})


async def rotate_key(
        auth, namespace: str, name: str, sequence: str) -> dict:
    url = f"{_base()}/keys/{namespace}/{name}/sequence/{sequence}/rotate"
    return await api.request("PATCH", url, auth, {})
