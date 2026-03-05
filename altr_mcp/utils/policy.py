from altr_mcp.utils import api
import urllib.parse
import re


async def _paginate_altr_policy_request(url: str, params: dict, auth) -> dict:
    method = "GET"
    last_evalutated_key = {}
    response = {"data": {"policies": []}}
    while last_evalutated_key is not None:
        temp_response = await api.request(method, url, auth, params)
        last_evalutated_key = temp_response.get(
                "data", {}).get("last_evalutated_key", None)
        params["exclusive_start_key"] = last_evalutated_key
        response["data"]["policies"] += temp_response["data"]["policies"]
    return response


async def _paginate_altr_rule_request(url: str, params: dict, auth) -> dict:
    method = "GET"
    last_evalutated_key = {}
    response = {"data": {"items": {}}}
    while last_evalutated_key is not None:
        temp_response = await api.request(method, url, auth, params)
        last_evalutated_key = temp_response.get(
                "data", {}).get("last_evalutated_key", None)
        params["exclusive_start_key"] = last_evalutated_key
        temp_items = temp_response.get("data", {}).get("items", {})
        if temp_items:
            response["data"]["items"] = (
                response["data"]["items"] | temp_items
            )
    return response


async def make_altr_policy_request(params: dict, auth) -> dict:
    url = "https://api.live.altr.com/v1/unified-policy/management/policy"
    response = await _paginate_altr_policy_request(url, params, auth)
    return response


async def make_altr_rules_request(params: dict, policy_id: str, auth) -> dict:
    decoded_policy_id = urllib.parse.unquote(policy_id)
    encoded_policy_id = urllib.parse.quote(decoded_policy_id, safe='')
    url = (
        "https://api.live.altr.com"
        f"/v1/unified-policy/management/policy/{encoded_policy_id}/rules"
    )
    policy_response = await _paginate_altr_rule_request(url, params, auth)
    return policy_response


def format_policies(policies: dict) -> list:
    formatted_strs = []
    for policy in policies.get("data", {}).get("policies"):
        policy_id = urllib.parse.quote(policy["policy_id"])
        policy_type = re.search(f"^[^{'#'}]*", policy["policy_id"]).group(0)
        formatted_strs.append(
            f"Type: {policy_type}\n" +
            f"Name: {policy['name']}\n" +
            f"Status: {policy['this_status']}\n" +
            f"ID: {policy_id}"
        )
    return formatted_strs


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
            masking_string = success_rule.get('masking_policy', 'Failed')
            rule_string += (
                f"Role: {rule.get('role', 'N/A')}\n" +
                f"Masking: {masking_string}"
            )
            formatted_strs.append(rule_string)
    return formatted_strs


async def create_altr_policy(params: dict, auth, tag: str):
    url = "https://api.live.altr.com/v1/unified-policy/management/policy"
    method = "POST"
    data = {"identifier": tag, "type": "TAG"}
    response = await api.request(method, url, auth, params, data)
    return response.get("data", {}).get("policy_id", "FAILED")


async def delete_altr_policy(params: dict, auth, policy_id: str):
    decoded_policy_id = urllib.parse.unquote(policy_id)
    encoded_policy_id = urllib.parse.quote(decoded_policy_id, safe='')
    url = (
        f"https://api.live.altr.com"
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
    url = "https://altrnet.live.altr.com/api/userGroups"
    return await _paginate_altr_user_groups_request(url, params, auth)


async def create_altr_rule(
        params: dict,
        auth,
        policy_id: str,
        masking_policy: int,
        role: str,
        tag_value: str
        ) -> dict:
    decoded_policy_id = urllib.parse.unquote(policy_id)
    encoded_policy_id = urllib.parse.quote(decoded_policy_id, safe='')
    url = (
        f"https://api.live.altr.com"
        f"/v1/unified-policy/management/policy/{encoded_policy_id}/rules"
    )
    method = "POST"
    data = {
        "masking_policy": masking_policy,
        "role": role,
        "tag_value": tag_value
    }
    response = await api.request(method, url, auth, params, data)
    return response


async def delete_altr_rule(
        params: dict, auth, policy_id: str, rule_id: str) -> dict:
    decoded_policy_id = urllib.parse.unquote(policy_id)
    encoded_policy_id = urllib.parse.quote(decoded_policy_id, safe='')

    decoded_rule_id = urllib.parse.unquote(rule_id)
    encoded_rule_id = urllib.parse.quote(decoded_rule_id, safe='')

    url = (
        f"https://api.live.altr.com"
        f"/v1/unified-policy/management/policy/"
        f"{encoded_policy_id}/rules/{encoded_rule_id}"
    )
    method = "DELETE"

    return await api.request(method, url, auth, {})
