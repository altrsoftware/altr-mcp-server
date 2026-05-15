from altr_mcp.utils import api
from altr_mcp.settings import get_settings


# ── Sidecar audits (sc-control) ─────────────────────────────────────────────

def _base():
    return f"{get_settings().sc_control_base_url}/v1/audits"


async def search_audits(auth, params: dict) -> dict:
    url = _base()
    return await api.request("POST", url, auth, params)


async def get_audit_results(auth, search_uuid: str, params: dict) -> dict:
    url = f"{_base()}/{search_uuid}"
    return await api.request("GET", url, auth, params)


# ── System audits (MAPI) ─────────────────────────────────────────────────────

def _system_audits_base():
    return f"{get_settings().altr_altrnet_base_url}/api/systemaudits/query"


async def search_system_audits(auth, params: dict) -> dict:
    url = f"{_system_audits_base()}/start"
    return await api.request("POST", url, auth, params)


async def get_system_audit_results(auth, token: str) -> dict:
    import urllib.parse
    encoded_token = urllib.parse.quote(token, safe='')
    url = f"{_system_audits_base()}/result/{encoded_token}"
    return await api.request("GET", url, auth, {})


# ── Query audits (Snowflake tag/column masking) ─────────────────────────────

def _query_audits_base():
    return f"{get_settings().altr_api_base_url}/v1/query-audits"


async def search_query_audits(auth, params: dict) -> dict:
    url = f"{_query_audits_base()}/search"
    return await api.request("POST", url, auth, params)


async def get_query_audit_results(
        auth, search_uuid: str, params: dict) -> dict:
    url = f"{_query_audits_base()}/results/{search_uuid}"
    return await api.request("GET", url, auth, params)
