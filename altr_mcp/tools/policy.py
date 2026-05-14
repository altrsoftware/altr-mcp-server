from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from altr_mcp.models import validate_masking_rules
from altr_mcp.settings import get_settings
from altr_mcp.utils import policy
from altr_mcp.utils.logging import log_tool


def register(mcp: FastMCP) -> None:

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_policies(policy_type: str | None = None) -> dict:
        """List masking policies configured in your ALTR organization.

        Returns each policy's tag, policy ID, and current rule count. Use the
        policy_id from results when calling `add_rules`, `get_rules`, or
        `delete_policy`.

        Masking levels reference:
        - 10000: No mask (show raw value)
        - 10001: Full mask (replace with * matching data length)
        - 10002: Email mask (show domain only)
        - 10003: Show last four
        - 10004: Constant mask (1 for numbers,
          * for strings, 1/1/2000 for dates)
        - 10005: Null (replace with NULL)
        - 10006: Full mask hash (replace with hashed value)
        - 10007: Email hash (show domain, hash local part)
        - 10008: Show last four hash (hash prefix, show last 4)
        - 10009: Constant date (replace with 12/31/9999)

        Args:
            policy_type: Filter by policy type. Values: TAG, COLUMN, PUSHDOWN,
                IMPERSONATION, GRANT, ROW, OLTP. If omitted, queries all
                types and merges results.
        """
        settings = get_settings()
        if policy_type is not None:
            params = {"policy_type": policy_type}
            policies = await policy.make_altr_policy_request(
                params, settings.auth)
            return {"success": True, "data": policies, "error": None}
        # API requires policy_type — query all types and merge
        all_policies = []
        for pt in ("TAG", "COLUMN", "PUSHDOWN",
                   "IMPERSONATION", "GRANT", "ROW", "OLTP"):
            params = {"policy_type": pt}
            result = await policy.make_altr_policy_request(
                params, settings.auth)
            all_policies += result.get("data", {}).get("policies", [])
        return {
            "success": True,
            "data": {"data": {"policies": all_policies}},
            "error": None,
        }

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_rules(policy_id: str) -> dict:
        """View all masking rules configured for a specific policy.

        Shows which roles have what masking levels for which tag values.

        Masking levels reference:
        - 10000: No mask (show raw value)
        - 10001: Full mask (replace with * matching data length)
        - 10002: Email mask (show domain only)
        - 10003: Show last four
        - 10004: Constant mask (1 for numbers,
          * for strings, 1/1/2000 for dates)
        - 10005: Null (replace with NULL)
        - 10006: Full mask hash (replace with hashed value)
        - 10007: Email hash (show domain, hash local part)
        - 10008: Show last four hash (hash prefix, show last 4)
        - 10009: Constant date (replace with 12/31/9999)

        Args:
            policy_id: Raw policy ID as returned by
                `get_policies`. Do not URL-encode.
        """
        settings = get_settings()
        rules = await policy.make_altr_rules_request(
            {}, policy_id, settings.auth)
        return {"success": True, "data": rules, "error": None}

    @mcp.tool()
    @log_tool
    async def create_policy(
            tag: str,
            policy_type: str | None = None,
            database_ids: list[int] | None = None) -> dict:
        """Create an empty masking policy for a specific tag.

        Creates a masking policy that controls how data tagged with the
        specified tag is masked. Until you add rules with `add_rules`, all
        users will see NULL for tagged columns.

        Each tag can only have one policy — check `get_policies` first to
        avoid conflicts.

        After creating a policy, use `add_rules` to define masking behavior.

        PLATFORM DIFFERENCES — TAG HANDLING:

        Snowflake and Databricks tags are FUNDAMENTALLY DIFFERENT in ALTR:

        - A Snowflake tag is a connected ALTR object — it has been
          registered with `connect_tag`, owns a `tag_group_id`, a masking
          configuration, and shows up in `get_tags`. You reference it here
          by its UPPERCASE name.
        - A Databricks tag is NOT an ALTR object — it is just a raw
          string referenced at policy-creation time. There is no
          `connect_tag` step, no `tag_group_id`, and it will never appear
          in `get_tags`. The string you pass here is what gets stored on
          the policy.

        **Snowflake:** The `tag` param must be the UPPERCASE tag name as
        returned by `get_tags`. The tag MUST already be connected to ALTR via
        `connect_tag` before creating a policy. Do NOT pass `database_ids` for
        Snowflake — the API will reject it.

        **Databricks:** The `tag` param is any raw tag name string (e.g.,
        "pac_access_level") — case-insensitive, no connection step required.
        Do NOT call `connect_tag` and do NOT look the tag up in `get_tags`;
        Databricks tags will not be there. You MUST set `policy_type` to
        "PUSHDOWN" — the API rejects "TAG" for Databricks metastores.
        You MUST also pass `database_ids` as a list of ALTR database IDs
        for the target Databricks metastore(s) (from `get_databases`).
        `database_ids` is required for Databricks, and it is ALWAYS a
        list — even when targeting a single database, wrap the ID in a
        list (e.g., `database_ids=[2167]`, not `database_ids=2167`).
        Omitting `database_ids` will be rejected by the API.

        Available masking levels:
        - 10000: No mask (show raw value)
        - 10001: Full mask (replace with * matching data length)
        - 10002: Email mask (show domain only)
        - 10003: Show last four
        - 10004: Constant mask (1 for numbers,
          * for strings, 1/1/2000 for dates)
        - 10005: Null (replace with NULL)
        - 10006: Full mask hash (replace with hashed value)
        - 10007: Email hash (show domain, hash local part)
        - 10008: Show last four hash (hash prefix, show last 4)
        - 10009: Constant date (replace with 12/31/9999)

        Args:
            tag: Tag name. For Snowflake: UPPERCASE connected tag from
                `get_tags`. For Databricks: any raw tag name string —
                no prior connection required.
            policy_type: Must be "PUSHDOWN" for Databricks. Omit for
                Snowflake (defaults to "TAG").
            database_ids: REQUIRED for Databricks. Must be a list of ALTR
                database IDs for the target Databricks metastore(s) (from
                `get_databases`). Always pass a list — wrap a single ID in
                a list (e.g., [2167]); do NOT pass a bare int. Omit
                entirely for Snowflake.
        """
        settings = get_settings()
        response = await policy.create_altr_policy(
            {}, settings.auth, tag,
            policy_type=policy_type or "TAG",
            database_ids=database_ids,
        )
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def add_rules(policy_id: str, rules: str | list[dict]) -> dict:
        """Add one or more masking rules to a policy in a
        single batch request.

        Each rule specifies: which role, which tag value,
        and what masking level
        they should see. A policy must already exist for the tag (see
        `create_policy`). Accepts up to 99 rules per batch; if more than 99 are
        provided they are automatically split into multiple batches.

        Each rule in the list must be a dict with these keys:
        - masking_policy: int — masking level (10000-10009)
        - role: str — target user group / role name from `get_roles`
        - tag_value: str — exact tag value this rule
          applies to (case-sensitive)

        Pass as a list of dicts or a JSON string:
            [
                {"masking_policy": 10001, "role": "ANALYST",
                 "tag_value": "PII_SSN"},
                {"masking_policy": 10000, "role": "ADMIN",
                 "tag_value": "PII_SSN"}
            ]

        Masking levels:
        - 10000: No mask (show raw value) — use sparingly for trusted roles
        - 10001: Full mask (replace with * matching data length)
        - 10002: Email mask (show domain only, e.g., ****@bank.com)
        - 10003: Show last four (e.g., ***-**-1234)
        - 10004: Constant mask (1 for numbers,
          * for strings, 1/1/2000 for dates)
        - 10005: Null (replace with NULL)
        - 10006: Full mask hash (replace with hashed value)
        - 10007: Email hash (show domain, hash local part)
        - 10008: Show last four hash (hash prefix, show last 4)
        - 10009: Constant date (replace with 12/31/9999)

        Args:
            policy_id: Raw policy ID from `get_policies`. Do not URL-encode.
            rules: List of rule dicts, or a JSON string encoding such a list.
                Each dict must have 'masking_policy', 'role', and 'tag_value'.
        """
        if isinstance(rules, str):
            import json
            rules = json.loads(rules)
        validation_error = validate_masking_rules(rules)
        if validation_error:
            raise ValueError(validation_error)

        settings = get_settings()
        results = await policy.batch_add_rules(settings.auth, policy_id, rules)
        return {"success": True, "data": results, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def delete_policy(policy_id: str) -> dict:
        """Delete a masking policy and all its rules.

        Use with caution - this removes all masking rules
        associated with the policy. Consider reviewing rules
        with `get_rules` first to understand what will be
        deleted.

        Args:
            policy_id: Raw policy ID from `get_policies`. Do not URL-encode.
        """
        settings = get_settings()
        response = await policy.delete_altr_policy(
            {}, settings.auth, policy_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_rule(
            policy_id: str,
            rule_id: str,
            masking_policy: int | None = None,
            role: str | None = None,
            tag_value: str | None = None,
            access_rate_thresholds: dict | list[dict] | None = None,
            time_window_thresholds: dict | list[dict] | None = None
            ) -> dict:
        """Update an existing masking rule's properties
        without deleting and recreating it.

        Only the fields you provide will be updated; omitted
        fields remain unchanged. Use `get_rules` first to find
        the rule_id and see current values.

        Masking levels reference:
        - 10000: No mask (show raw value)
        - 10001: Full mask (replace with * matching data length)
        - 10002: Email mask (show domain only)
        - 10003: Show last four
        - 10004: Constant mask (1 for numbers,
          * for strings, 1/1/2000 for dates)
        - 10005: Null (replace with NULL)
        - 10006: Full mask hash (replace with hashed value)
        - 10007: Email hash (show domain, hash local part)
        - 10008: Show last four hash (hash prefix, show last 4)
        - 10009: Constant date (replace with 12/31/9999)

        Args:
            policy_id: Raw policy ID from `get_policies`. Do not URL-encode.
            rule_id: Raw rule ID from `get_rules`. Do not URL-encode.
            masking_policy: New masking level (10000-10009).
            role: New role/user group name.
            tag_value: New tag value for the rule.
            access_rate_thresholds: List of access rate threshold
                objects, each with 'access_rate_unit' (str),
                'access_rate_limit' (int), and 'action' (str).
            time_window_thresholds: List of time window threshold
                objects, each with 'day' (list of str),
                'start_time' (dict with hour/minute),
                'end_time' (dict with hour/minute),
                'timezone' (str), and 'action' (str).
        """
        from altr_mcp.models import (
            validate_access_rate_thresholds,
            validate_time_window_thresholds,
        )

        if access_rate_thresholds is not None:
            if isinstance(access_rate_thresholds, dict):
                access_rate_thresholds = [access_rate_thresholds]
            error = validate_access_rate_thresholds(access_rate_thresholds)
            if error:
                raise ValueError(error)

        if time_window_thresholds is not None:
            if isinstance(time_window_thresholds, dict):
                time_window_thresholds = [time_window_thresholds]
            error = validate_time_window_thresholds(time_window_thresholds)
            if error:
                raise ValueError(error)

        data = {}
        if masking_policy is not None:
            data["masking_policy"] = masking_policy
        if role is not None:
            data["role"] = role
        if tag_value is not None:
            data["tag_value"] = tag_value
        if access_rate_thresholds is not None:
            data["access_rate_thresholds"] = access_rate_thresholds
        if time_window_thresholds is not None:
            data["time_window_thresholds"] = time_window_thresholds

        if not data:
            raise ValueError("No fields provided to update.")

        settings = get_settings()
        response = await policy.update_altr_rule(
            settings.auth, policy_id, rule_id, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def delete_rule(policy_id: str, rule_id: str) -> dict:
        """Remove a specific masking rule from a policy.

        Allows fine-grained removal of individual rules
        without deleting the entire policy.
        Use `get_rules` first to identify the rule_id you want to remove.

        Args:
            policy_id: Raw policy ID containing the rule. Do not URL-encode.
            rule_id: Raw rule ID to delete. Do not URL-encode.
        """
        settings = get_settings()
        response = await policy.delete_altr_rule(
            {}, settings.auth, policy_id, rule_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_roles() -> dict:
        """List all ALTR roles (user groups) available in your organization.

        Role names are used in `add_rules` to define which user groups see what
        level of data masking.
        """
        settings = get_settings()
        user_group_names = await policy.get_user_group_names({}, settings.auth)
        return {"success": True, "data": user_group_names, "error": None}
