from altr_mcp.utils import api
from altr_mcp.utils import database
from altr_mcp.settings import get_settings


async def _paginate_altr_tag_request(url: str, params: dict, auth) -> list:
    method = "GET"
    has_more = True
    response = {"items": []}
    while has_more:
        temp_response = await api.request(method, url, auth, params)
        response["items"] += temp_response.get("items", [])
        has_more = temp_response.get("has_more", False)
    return response


async def make_altr_tag_request(params: dict, auth):
    url = f"{get_settings().altr_api_base_url}/v1/tag/masking"
    return await _paginate_altr_tag_request(url, params, auth)


async def delete_altr_tag(tag_group_id: str, params: dict, auth):
    url = (
        f"{get_settings().altr_api_base_url}"
        f"/v1/tag/masking/tag/{tag_group_id}"
    )
    method = "DELETE"
    return await api.request(method, url, auth, params)


async def _paginate_altr_tag_values_request(
        url: str, params: dict, auth) -> list:
    method = "GET"
    totals = 1
    count = 0
    response = {"tags": []}
    while count < totals:
        temp_response = await api.request(method, url, auth, params)
        count += len(temp_response.get("tags", []))
        if count == 0:
            break
        response["tags"] += temp_response.get("tags", [])
        totals = temp_response.get("totals", {}).get("tagCount", 0)
    return response


async def connect_tag_request(database_name, schema_name, tag_name, auth):
    url = f"{get_settings().altr_api_base_url}/v1/tag/masking/"
    method = "PUT"
    database_response = await database._get_database_id(database_name, auth)
    database_data = database_response.get("data", {})
    databases = database_data.get("databases", [])
    if not databases:
        return {
            "success": False,
            "message": f"Database '{database_name}' not found in ALTR.",
        }
    db_record = databases[0]
    database_id = db_record.get("id")
    snowflake_name = db_record.get("databaseName", database_name)
    tag_data = {
        "database_id": database_id,
        "database_name": snowflake_name,
        "schema_name": schema_name,
        "tag_name": tag_name,
        "friendly_name": tag_name,
        "masking": {
            "custom_role_provider": {
                "enabled": False
            },
            "protection_type": "governed"
        }
    }
    response = await api.request(method, url, auth, {}, tag_data)

    if (response and isinstance(response, dict)
            and response.get("success") is False):
        return response

    # API returns status of PENDING | SUCCESS | FAILED
    if response and isinstance(response, dict):
        status = response.get("status", "").upper()
        if status == "SUCCESS":
            return {
                "success": True,
                "message": (
                    f"Tag '{tag_name}' successfully connected "
                    f"to database '{database_name}', "
                    f"schema '{schema_name}'"
                ),
                "job_id": response.get("job_id"),
                "details": response.get("details", {})
            }
        elif status == "PENDING":
            return {
                "success": True,
                "message": (
                    f"Tag '{tag_name}' connection is pending "
                    f"for database '{database_name}', "
                    f"schema '{schema_name}'. "
                    f"Job ID: {response.get('job_id', 'N/A')}"
                ),
                "job_id": response.get("job_id"),
                "status": "PENDING",
                "details": response.get("details", {})
            }
        elif status == "FAILED":
            details_msg = response.get("details", {})
            error_msg = details_msg.get("error_message", "Unknown error")
            return {
                "success": False,
                "message": f"Tag connection failed: {error_msg}",
                "job_id": response.get("job_id"),
                "details": response.get("details", {})
            }

    return response


async def get_tag_by_group_id(tag_group_id: str, auth) -> dict:
    url = (
        f"{get_settings().altr_api_base_url}"
        f"/v1/tag/masking/tag/{tag_group_id}"
    )
    method = "GET"
    return await api.request(method, url, auth, {})


async def get_tag_by_details(
        db_id: int, database_name: str,
        tag_name: str, schema_name: str, auth,
        protection_type: str = None) -> dict:
    url = (
        f"{get_settings().altr_api_base_url}/v1/tag/masking"
        f"/database/{db_id}"
        f"/database-name/{database_name}"
        f"/tag-name/{tag_name}"
        f"/schema-name/{schema_name}"
    )
    method = "GET"
    params = {}
    if protection_type is not None:
        params["protection-type"] = protection_type
    return await api.request(method, url, auth, params)


async def create_tag_by_group_id(
        tag_group_id: str, auth, data: dict) -> dict:
    url = (
        f"{get_settings().altr_api_base_url}"
        f"/v1/tag/masking/tag/{tag_group_id}"
    )
    method = "PUT"
    return await api.request(method, url, auth, {}, data)


async def delete_tag_by_details(auth, data: dict,
                                ignore_errors: bool = False) -> dict:
    url = f"{get_settings().altr_api_base_url}/v1/tag/masking/"
    method = "DELETE"
    params = {"ignore_errors": ignore_errors}
    return await api.request(method, url, auth, params, data)


async def make_altr_tag_values_request(params: dict, auth):
    url = f"{get_settings().altr_api_base_url}/v1/dis/tags/v2/tags/list"
    return await _paginate_altr_tag_values_request(url, params, auth)
