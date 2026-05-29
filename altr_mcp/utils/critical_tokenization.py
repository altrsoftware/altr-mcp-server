from altr_mcp.utils import api
from altr_mcp.settings import get_settings


def _base():
    return get_settings().critical_base_url


async def tokenize(auth, data: dict, deterministic: bool = False) -> dict:
    url = f"{_base()}/batch"
    headers = {"X-ALTR-DETERMINISM": str(deterministic).lower()}
    return await api.request("POST", url, auth, {}, data, headers)


async def detokenize(auth, data: dict) -> dict:
    url = f"{_base()}/batch"
    return await api.request("PUT", url, auth, {}, data)


async def partial_detokenize(auth, data: dict) -> dict:
    url = f"{_base()}/batch/partial"
    return await api.request("PUT", url, auth, {}, data)


async def delete_tokens(auth, data: dict) -> dict:
    url = f"{_base()}/batch/delete"
    return await api.request("PUT", url, auth, {}, data)
