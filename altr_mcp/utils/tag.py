from altr_mcp.utils import api
from altr_mcp.utils import database


async def _paginate_altr_tag_request(url: str, params: dict, auth) -> list:
    method = "GET"
    has_more = True
    response = {"items": []}
    while has_more:
        temp_response = await api.request(method, url, auth, params)
        response["items"] += temp_response.get("items", [])
        has_more = temp_response.get("has_more", False)
    return response


def format_tags(tags: dict) -> list:
    formatted_tags = []
    for item in tags["items"]:
        formatted_tags.append(
            f"Tag: {item['friendly_name']}, "
            f"Tag_group_id: {item['tag_group_id']}"
        )
    return formatted_tags


async def make_altr_tag_request(params: dict, auth):
    url = "https://api.live.altr.com/v1/tag/masking"
    return await _paginate_altr_tag_request(url, params, auth)


async def delete_altr_tag(tag_group_id: str, params: dict, auth):
    url = f"https://api.live.altr.com/v1/tag/masking/tag/{tag_group_id}"
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
        totals = temp_response.get("totals", {}).get("tagGroupCount", 0)
    return response


async def connect_tag_request(database_name, schema_name, tag_name, auth):
    url = "https://api.live.altr.com/v1/tag/masking/"
    method = "PUT"
    database_response = await database._get_database_id(database_name, auth)
    database_data = database_response.get("data", {})
    database_id = database_data.get("databases", [{}])[0].get("id")
    tag_data = {
        "database_id": database_id,
        "database_name": database_name,
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

    # Check if the API request returned an error
    # (from api.request error handling)
    if (response and isinstance(response, dict)
            and response.get("success") is False):
        return response

    # Handle the actual API response format which has status:
    # "PENDING" | "SUCCESS" | "FAILED"
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

    # If response doesn't match expected format,
    # return as-is (might be empty dict or different structure)
    return response


async def make_altr_tag_values_request(params: dict, auth):
    url = "https://api.live.altr.com/v1/dis/tags/v2/tags/list"
    return await _paginate_altr_tag_values_request(url, params, auth)
