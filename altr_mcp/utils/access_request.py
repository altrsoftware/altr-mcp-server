import structlog
from altr_mcp.utils import api
from altr_mcp.settings import get_settings
import urllib.parse

logger = structlog.get_logger(__name__)


BASE_PATH = "/v1/unified-policy/management/accessRequest"


async def create_access_request(auth, data: dict) -> dict:
    url = f"{get_settings().altr_api_base_url}{BASE_PATH}"
    method = "POST"
    return await api.request(method, url, auth, {}, data)


async def get_access_requests(auth, params: dict) -> dict:
    url = f"{get_settings().altr_api_base_url}{BASE_PATH}"
    method = "GET"
    return await api.request(method, url, auth, params)


async def get_access_request(auth, request_id: str) -> dict:
    encoded = urllib.parse.quote(request_id, safe='')
    url = f"{get_settings().altr_api_base_url}{BASE_PATH}/{encoded}"
    method = "GET"
    return await api.request(method, url, auth, {})


async def approve_access_request(
        auth, request_id: str, justification: str) -> dict:
    encoded = urllib.parse.quote(request_id, safe='')
    url = f"{get_settings().altr_api_base_url}{BASE_PATH}/{encoded}/approve"
    method = "PUT"
    data = {"justification": justification}
    return await api.request(method, url, auth, {}, data)


async def deny_access_request(
        auth, request_id: str, justification: str) -> dict:
    encoded = urllib.parse.quote(request_id, safe='')
    url = f"{get_settings().altr_api_base_url}{BASE_PATH}/{encoded}/deny"
    method = "PUT"
    data = {"justification": justification}
    return await api.request(method, url, auth, {}, data)


async def cancel_access_request(
        auth, request_id: str, justification: str) -> dict:
    encoded = urllib.parse.quote(request_id, safe='')
    url = f"{get_settings().altr_api_base_url}{BASE_PATH}/{encoded}/cancel"
    method = "PUT"
    data = {"justification": justification}
    return await api.request(method, url, auth, {}, data)
