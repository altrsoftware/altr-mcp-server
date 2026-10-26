from altr_mcp.utils import api
from altr_mcp.settings import get_settings
import urllib.parse

import structlog

logger = structlog.get_logger(__name__)

# Supported masks per (policy_type, database_type), fetched once per process.
_supported_masks: dict[tuple[str, str | None], frozenset[int]] = {}


async def _paginate_altr_policy_request(url: str, params: dict, auth) -> dict:
    method = "GET"
    last_evaluated_key = {}
    response = {"data": {"policies": []}}
    while last_evaluated_key is not None:
        temp_response = await api.request(method, url, auth, params)
        last_evaluated_key = temp_response.get(
                "data", {}).get("last_evaluated_key", None)
        params["exclusive_start_key"] = last_evaluated_key
        response["data"]["policies"] += temp_response.get(
                "data", {}).get("policies", [])
    return response


async def _paginate_altr_rule_request(url: str, params: dict, auth) -> dict:
    method = "GET"
    last_evaluated_key = {}
    response = {"data": {"items": {}}}
    while last_evaluated_key is not None:
        temp_response = await api.request(method, url, auth, params)
        last_evaluated_key = temp_response.get(
                "data", {}).get("last_evaluated_key", None)
        params["exclusive_start_key"] = last_evaluated_key
        temp_items = temp_response.get("data", {}).get("items", {})
        if temp_items:
            response["data"]["items"] = (
                response["data"]["items"] | temp_items
            )
    return response


async def make_altr_policy_request(params: dict, auth) -> dict:
    url = (
        f"{get_settings().altr_api_base_url}"
        "/v1/unified-policy/management/policy"
    )
    response = await _paginate_altr_policy_request(url, params, auth)
    return response


async def make_altr_rules_request(params: dict, policy_id: str, auth) -> dict:
    decoded_policy_id = urllib.parse.unquote(policy_id)
    encoded_policy_id = urllib.parse.quote(decoded_policy_id, safe='')
    url = (
        f"{get_settings().altr_api_base_url}"
        f"/v1/unified-policy/management/policy/{encoded_policy_id}/rules"
    )
    policy_response = await _paginate_altr_rule_request(url, params, auth)
    return policy_response


async def create_altr_policy(
        params: dict,
        auth,
        tag: str,
        policy_type: str = "TAG",
        database_ids: list[int] | None = None):
    url = (
        f"{get_settings().altr_api_base_url}"
        "/v1/unified-policy/management/policy"
    )
    data: dict = {"identifier": tag, "type": policy_type}
    if database_ids is not None:
        data["database_ids"] = database_ids
    response = await api.request("POST", url, auth, params, data)
    policy_id = response.get("data", {}).get("policy_id")
    if policy_id is None:
        return {"error": response}
    return policy_id


async def delete_altr_policy(params: dict, auth, policy_id: str):
    decoded_policy_id = urllib.parse.unquote(policy_id)
    encoded_policy_id = urllib.parse.quote(decoded_policy_id, safe='')
    url = (
        f"{get_settings().altr_api_base_url}"
        f"/v1/unified-policy/management/policy/{encoded_policy_id}"
    )
    method = "DELETE"
    return await api.request(method, url, auth, {})


async def _paginate_altr_user_groups_request(
        url: str, params: dict, auth) -> list:
    method = "GET"
    all_user_groups = []
    offset = 0

    while True:
        params_with_pagination = {**params, "offset": offset}
        temp_response = await api.request(
                method, url, auth, params_with_pagination)

        if not temp_response or not temp_response.get("success"):
            break

        user_groups = temp_response.get("data", {}).get("userGroups", [])
        if not user_groups:
            break

        all_user_groups.extend(
                [group["userGroupName"] for group in user_groups])

        # Check if we've fetched all items
        total_count = temp_response.get("data", {}).get("count", 0)
        if len(all_user_groups) >= total_count:
            break

        offset += len(user_groups)

    return all_user_groups


async def get_user_group_names(params: dict, auth) -> list:
    url = f"{get_settings().altr_altrnet_base_url}/api/userGroups"
    return await _paginate_altr_user_groups_request(url, params, auth)


async def batch_add_rules(
        auth,
        policy_id: str,
        rules: list[dict]
        ) -> list[dict]:
    """Add rules in batches of up to 99 via the PATCH batch endpoint.

    Args:
        auth: Authentication credentials.
        policy_id: Raw (unencoded) policy ID.
        rules: List of rule dicts, each with 'masking_policy', 'role',
               'tag_value'.

    Returns:
        List of response dicts, one per batch.
    """
    decoded_policy_id = urllib.parse.unquote(policy_id)
    encoded_policy_id = urllib.parse.quote(decoded_policy_id, safe='')
    url = (
        f"{get_settings().altr_api_base_url}"
        f"/v1/unified-policy/management/policy/"
        f"{encoded_policy_id}/rules/batch"
    )
    method = "PATCH"
    batch_size = 99
    results = []

    for i in range(0, len(rules), batch_size):
        batch = rules[i:i + batch_size]
        data = {
            "rules": [
                {
                    "action": "PUT",
                    "rule": rule,
                }
                for rule in batch
            ]
        }
        response = await api.request(method, url, auth, {}, data)
        results.append(response)

    return results


async def delete_altr_rule(
        params: dict, auth, policy_id: str, rule_id: str) -> dict:
    decoded_policy_id = urllib.parse.unquote(policy_id)
    encoded_policy_id = urllib.parse.quote(decoded_policy_id, safe='')

    decoded_rule_id = urllib.parse.unquote(rule_id)
    encoded_rule_id = urllib.parse.quote(decoded_rule_id, safe='')

    url = (
        f"{get_settings().altr_api_base_url}"
        f"/v1/unified-policy/management/policy/"
        f"{encoded_policy_id}/rules/{encoded_rule_id}"
    )
    method = "DELETE"

    return await api.request(method, url, auth, {})


async def update_altr_rule(
        auth, policy_id: str, rule_id: str, data: dict) -> dict:
    decoded_policy_id = urllib.parse.unquote(policy_id)
    encoded_policy_id = urllib.parse.quote(decoded_policy_id, safe='')

    decoded_rule_id = urllib.parse.unquote(rule_id)
    encoded_rule_id = urllib.parse.quote(decoded_rule_id, safe='')

    url = (
        f"{get_settings().altr_api_base_url}"
        f"/v1/unified-policy/management/policy/"
        f"{encoded_policy_id}/rules/{encoded_rule_id}"
    )
    method = "PATCH"

    return await api.request(method, url, auth, {}, data)


async def get_supported_masking_types(params: dict, auth) -> dict:
    url = (
        f"{get_settings().altr_api_base_url}"
        "/v1/unified-policy/management/policy/rules/supportedMaskingTypes"
    )
    return await api.request("GET", url, auth, params)


async def get_supported_masks(
        policy_type: str, auth,
        database_type: str | None = None) -> frozenset[int] | None:
    """Masks the API supports for a policy type, or None if the lookup fails.

    A successful answer is kept for the life of the process; a failure is not.
    """
    key = (policy_type, database_type)
    if key in _supported_masks:
        return _supported_masks[key]
    params = {"policy_type": policy_type}
    if database_type is not None:
        params["database_type"] = database_type
    response = await get_supported_masking_types(params, auth)
    reason = None
    try:
        masks = frozenset(
            int(item["masking_type"]) for item in response.get("data"))
    except (KeyError, TypeError, ValueError) as e:
        masks = frozenset()
        reason = type(e).__name__
    if not masks:
        logger.warning(
            "supported_masks_unavailable",
            policy_type=policy_type, database_type=database_type,
            status_code=response.get("status_code"),
            message=response.get("message"), reason=reason)
        return None
    _supported_masks[key] = masks
    return masks


def forget_supported_masks() -> None:
    _supported_masks.clear()
