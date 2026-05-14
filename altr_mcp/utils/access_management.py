import structlog
from altr_mcp.utils import api
from altr_mcp.settings import get_settings
import urllib.parse

logger = structlog.get_logger(__name__)


async def create_snowflake_access_policy(auth, data: dict) -> dict:
    url = (
        f"{get_settings().altr_api_base_url}/v1/unified-policy"
        "/management/policy/accessManagement/snowflake"
    )
    method = "POST"
    return await api.request(method, url, auth, {}, data)


async def create_oltp_access_policy(auth, data: dict) -> dict:
    url = (
        f"{get_settings().altr_api_base_url}/v1/unified-policy"
        "/management/policy/accessManagement/oltp"
    )
    method = "POST"
    return await api.request(method, url, auth, {}, data)


async def update_snowflake_access_policy(
        auth, policy_id: str, data: dict) -> dict:
    decoded = urllib.parse.unquote(policy_id)
    encoded = urllib.parse.quote(decoded, safe='')
    url = (
        f"{get_settings().altr_api_base_url}"
        f"/v1/unified-policy/management/policy/accessManagement"
        f"/snowflake/{encoded}"
    )
    method = "PUT"
    return await api.request(method, url, auth, {}, data)


async def trigger_access_policy_check(auth, policy_id: str) -> dict:
    decoded = urllib.parse.unquote(policy_id)
    encoded = urllib.parse.quote(decoded, safe='')
    url = (
        f"{get_settings().altr_api_base_url}"
        f"/v1/unified-policy/management/policy/accessManagement"
        f"/triggerCheck/{encoded}"
    )
    method = "PUT"
    return await api.request(method, url, auth, {})
