import structlog
from altr_mcp.utils import api
from altr_mcp.settings import get_settings
import urllib.parse
import re

logger = structlog.get_logger(__name__)


async def _paginate_altr_policy_request(url: str, params: dict, auth) -> dict:
    method = "GET"
    last_evalutated_key = {}
    response = {"data": {"policies": []}}
    while last_evalutated_key is not None:
        temp_response = await api.request(method, url, auth, params)
        last_evalutated_key = temp_response.get(
                "data", {}).get("last_evaluated_key", None)
        params["exclusive_start_key"] = last_evalutated_key
        response["data"]["policies"] += temp_response.get(
                "data", {}).get("policies", [])
    return response


async def _paginate_altr_rule_request(url: str, params: dict, auth) -> dict:
    method = "GET"
    last_evalutated_key = {}
    response = {"data": {"items": {}}}
    while last_evalutated_key is not None:
        temp_response = await api.request(method, url, auth, params)
        last_evalutated_key = temp_response.get(
                "data", {}).get("last_evaluated_key", None)
        params["exclusive_start_key"] = last_evalutated_key
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


def format_policies(policies: dict) -> list:
    formatted_strs = []
    for policy in policies.get("data", {}).get("policies"):
        policy_id = policy["policy_id"]
        policy_type = re.search(f"^[^{'#'}]*", policy["policy_id"]).group(0)
        formatted_strs.append(
            f"Type: {policy_type}\n" +
            f"Name: {policy['name']}\n" +
            f"Status: {policy['this_status']}\n" +
            f"ID: {policy_id}"
        )
    return formatted_strs


MASKING_LABELS = {
    10000: "No Mask",
    10001: "Full Mask",
    10002: "Email Mask",
    10003: "Show Last Four",
    10004: "Constant Mask",
    10005: "Null",
    10006: "Full Mask Hash",
    10007: "Email Hash",
    10008: "Show Last Four Hash",
    10009: "Constant Date",
}


def format_rules(rules: dict) -> list:
    formatted_strs = []
    items = rules.get("data", {}).get("items", {})
    if not items:
        return formatted_strs
    keys = items.keys()
    for key in keys:
        for rule in items.get(key, {}):
            policy_type = re.search(
                    f"^[^{'#'}]*", rule.get('policy_id', '')).group(0)

            rule_string = (
                f"Type: {policy_type}\n" +
                f"Rule ID: {rule.get('rule_id', 'N/A')}\n"
            )
            if "tag_value_regex" in rule:
                rule_string += "Value: *\n"
            elif "tag_value" in rule:
                rule_string += f"Value: {rule.get('tag_value', 'N/A')}\n"
            success_rule = rule.get('success_rule_json', {})
            masking_code = success_rule.get('masking_policy', 'Failed')
            masking_label = MASKING_LABELS.get(masking_code, "Unknown")
            rule_string += (
                f"Role: {rule.get('role', 'N/A')}\n" +
                f"Masking: {masking_code} ({masking_label})"
            )
            formatted_strs.append(rule_string)
    return formatted_strs


async def create_altr_policy(params: dict, auth, tag: str):
    url = (
        f"{get_settings().altr_api_base_url}"
        "/v1/unified-policy/management/policy"
    )
    method = "POST"
    data = {"identifier": tag, "type": "TAG"}
    response = await api.request(method, url, auth, params, data)
    return response.get("data", {}).get("policy_id", "FAILED")


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
