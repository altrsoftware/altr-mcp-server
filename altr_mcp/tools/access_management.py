from fastmcp import FastMCP
from altr_mcp.utils.logging import log_tool
from altr_mcp.settings import get_settings
from altr_mcp.utils import access_management


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    @log_tool
    async def create_snowflake_access_policy(
            policy_name: str,
            description: str,
            connection_id: int,
            rules: str | list[dict],
            policy_maintenance: dict | None = None,
            access_request_id: str | None = None
            ) -> dict:
        """Create an access management policy for a Snowflake datasource.

        Defines which roles can access which databases, schemas, or tables
        with read or write permissions. Policies are enforced by ALTR and
        checked on a schedule.

        Each rule in the list must contain:
        - actors: list of dicts with 'type' ("role"),
          'condition' ("equals"|"starts_with"|"ends_with"),
          and 'identifiers' (list of str).
        - objects: list of dicts with 'type'
          ("database"|"schema"|"table"), 'condition'
          ("equals"|"starts_with"|"ends_with"|
          "fully_qualified"), and 'identifiers' (list of
          str) or 'fully_qualified_identifiers' (list of
          dicts with database/schema/table/view keys).
        - access: list of dicts with 'name' ("read"|"write").

        Optionally, rules may include 'tagged_objects' for tag-based targeting:
        - tagged_objects: list of dicts with 'check_against'
          (list of "databases"|"schemas"|"tables"|"views"),
          'tagged_with' (list of dicts with database/schema/name/value keys),
          and 'tag_condition' ("or"|"and").

        Args:
            policy_name: Name for the policy (1-255 chars).
            description: Description of the policy (1-255 chars).
            connection_id: ALTR connection ID for the Snowflake database.
            rules: List of access rule objects, or a JSON string encoding
                such a list.
            policy_maintenance: Optional schedule dict with
                'rate' ("day"|"cron") and 'value' (number
                or cron string).
            access_request_id: Optional access request ID this policy fulfills.
        """
        if isinstance(rules, str):
            import json
            rules = json.loads(rules)
        data = {
            "policy_name": policy_name,
            "description": description,
            "connection_ids": [connection_id],
            "rules": rules,
        }
        if policy_maintenance is not None:
            data["policy_maintenance"] = policy_maintenance
        if access_request_id is not None:
            data["access_request_id"] = access_request_id

        settings = get_settings()
        response = await access_management.create_snowflake_access_policy(
                settings.auth, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_oltp_access_policy(
            policy_name: str,
            description: str,
            repo_name: str,
            database_type: int,
            database_type_name: str,
            rules: str | list[dict],
            case_sensitivity: str = "case_sensitive"
            ) -> dict:
        """Create an access management policy for an OLTP datasource.

        Each rule in the list must contain:
        - type: "read"
        - actors: list of dicts with 'type' ("idp_user"|"idp_group"),
          'condition' ("equals"), and 'identifiers' (list of str).
        - objects: list of dicts with 'type' ("column") and 'identifiers'
          (list of dicts with database/schema/table/column keys, each having
          'name' (str) and 'wildcard' (bool)).

        Args:
            policy_name: Name for the policy (1-255 chars).
            description: Description of the policy (1-255 chars).
            repo_name: Repository/connection name.
            database_type: Database type code (e.g., 4 for Oracle).
            database_type_name: Database type name (e.g., "oracle").
            rules: List of OLTP access rule objects, or a JSON string
                encoding such a list.
            case_sensitivity: Case sensitivity setting
                (default: "case_sensitive").
        """
        if isinstance(rules, str):
            import json
            rules = json.loads(rules)
        data = {
            "policy_name": policy_name,
            "description": description,
            "repo_name": repo_name,
            "database_type": database_type,
            "database_type_name": database_type_name,
            "rules": rules,
            "case_sensitivity": case_sensitivity,
        }

        settings = get_settings()
        response = await access_management.create_oltp_access_policy(
            settings.auth, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_snowflake_access_policy(
            policy_id: str,
            policy_name: str,
            rules: str | list[dict],
            description: str | None = None
            ) -> dict:
        """Update an existing Snowflake access management policy.

        Replaces the policy's name, description, and rules. See
        `create_snowflake_access_policy` for the rule format.

        Args:
            policy_id: Raw policy ID. Do not URL-encode.
            policy_name: Updated policy name (1-255 chars).
            rules: Updated list of access rule objects, or a JSON string
                encoding such a list.
            description: Updated description (1-255 chars).
        """
        if isinstance(rules, str):
            import json
            rules = json.loads(rules)
        data = {
            "policy_name": policy_name,
            "rules": rules,
        }
        if description is not None:
            data["description"] = description

        settings = get_settings()
        response = await access_management.update_snowflake_access_policy(
                settings.auth, policy_id, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def trigger_access_policy_check(policy_id: str) -> dict:
        """Trigger a manual compliance check for a
        grant/access management policy.

        Runs the policy check immediately instead of waiting for the next
        scheduled run.

        Args:
            policy_id: Raw policy ID. Do not URL-encode.
        """
        settings = get_settings()
        response = await access_management.trigger_access_policy_check(
                settings.auth, policy_id)
        return {"success": True, "data": response, "error": None}
