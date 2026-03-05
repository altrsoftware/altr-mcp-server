from altr_mcp.utils import api


async def _get_databases(params: dict, auth):
    method = "GET"
    url = "https://api.live.altr.com/v1/dis/classification/v2/listDBs"
    return await api.request(method, url, auth, params)


async def _get_database_id(database_name, auth):
    params = {
            "friendlyDatabaseName": database_name
    }
    method = "GET"
    url = "https://altrnet.live.altr.com/api/databases"
    return await api.request(method, url, auth, params)
