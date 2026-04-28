import structlog
from altr_mcp.utils import api
from altr_mcp.settings import get_settings

logger = structlog.get_logger(__name__)


async def _get_databases(params: dict, auth):
    method = "GET"
    url = f"{get_settings().altr_altrnet_base_url}/api/databases"
    return await api.request(method, url, auth, params)


async def _get_database_id(database_name, auth):
    params = {
            "friendlyDatabaseName": database_name
    }
    method = "GET"
    url = f"{get_settings().altr_altrnet_base_url}/api/databases"
    return await api.request(method, url, auth, params)


async def _get_service_users(auth):
    url = (
        f"{get_settings().service_user_base_url}"
        f"/v1/services/snowflake/users"
    )
    return await api.request("GET", url, auth, {})


async def _create_database(data: dict, auth):
    url = f"{get_settings().altr_altrnet_base_url}/api/databases"
    return await api.request("POST", url, auth, {}, data=data)


async def _update_database(database_id: int, data: dict, auth):
    url = f"{get_settings().altr_altrnet_base_url}/api/databases/{database_id}"
    return await api.request("PATCH", url, auth, {}, data=data)


async def _trigger_database_status_sync(database_id: int, auth):
    url = (
        f"{get_settings().altr_altrnet_base_url}"
        f"/api/databases/{database_id}/status"
    )
    return await api.request("PATCH", url, auth, {})


async def _delete_database(
        database_id: int, auth, ignore_errors: bool = False):
    url = f"{get_settings().altr_altrnet_base_url}/api/databases/{database_id}"
    params = {}
    if ignore_errors:
        params["ignoreErrors"] = True
    return await api.request("DELETE", url, auth, params)
