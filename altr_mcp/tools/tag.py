from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from altr_mcp.settings import get_settings
from altr_mcp.utils import tag
from altr_mcp.utils.logging import log_tool


def register(mcp: FastMCP) -> None:

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_tags() -> dict:
        """List all Snowflake tags connected to ALTR (available for use
        in policies).

        SNOWFLAKE ONLY. Databricks tags are NOT first-class objects in
        ALTR — they are raw string references used at policy-creation
        time only — so they will never appear in this list. Do not call
        `get_tags` to discover Databricks tags; pass the raw tag name
        directly to `create_policy` instead.

        For Snowflake, only tags that have been connected to ALTR via
        `connect_tag` appear here. Tags created in Snowflake but never
        connected will not be listed and cannot be used in a policy.
        """
        settings = get_settings()
        response = await tag.make_altr_tag_request({}, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def disconnect_tag(tag_group_id: str) -> dict:
        """Disconnect a connected Snowflake tag from ALTR.

        SNOWFLAKE ONLY. Databricks tags are not ALTR objects (they are
        raw strings referenced at policy-creation time), so there is
        nothing to disconnect here for Databricks — to stop masking a
        Databricks column tag, remove the policy with `delete_policy`
        instead.

        All policies on the tag must be removed first, or the disconnect
        will fail.

        Args:
            tag_group_id: Tag group identifier to disconnect.
        """
        settings = get_settings()
        response = await tag.delete_altr_tag(tag_group_id, {}, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_tag_values(tag_name: str) -> dict:
        """List all allowed values configured for a specific tag.

        SNOWFLAKE ONLY. Databricks tags are raw strings, not ALTR-managed
        objects, so they have no stored allowed-values list here — use
        whatever tag values exist in the Databricks catalog directly.

        These values are referenced when creating masking
        rules with `add_rules`.

        Args:
            tag_name: Tag name (from `get_tags`) whose
                values you want to inspect.
        """
        settings = get_settings()
        response = await tag.make_altr_tag_values_request(
            {"filter": tag_name}, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_tag_details_by_group_id(tag_group_id: str) -> dict:
        """Get full details for a specific connected tag by its group ID.

        SNOWFLAKE ONLY. `tag_group_id` only exists for connected Snowflake
        tags; Databricks tags are raw strings and have no group ID.

        Returns masking configuration, status, database info, and timestamps.
        Use `get_tags` first to find the tag_group_id.

        Args:
            tag_group_id: Tag group identifier from `get_tags`.
        """
        settings = get_settings()
        response = await tag.get_tag_by_group_id(tag_group_id, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_tag_details(
            database_id: int,
            database_name: str,
            tag_name: str,
            schema_name: str,
            protection_type: str | None = None
            ) -> dict:
        """Get full details for a specific tag masking by
        database, tag, and schema.

        SNOWFLAKE ONLY. Databricks tags are not stored as ALTR objects, so
        they have no detail record to fetch.

        Returns masking configuration, status, and timestamps. Use when you
        know the exact database/schema/tag but not the tag_group_id.

        Args:
            database_id: Numeric ALTR database ID (from `get_database_id`).
            database_name: Database name in ALTR.
            tag_name: Tag name.
            schema_name: Schema name containing the tag.
            protection_type: Optional filter — "governed", "governed-pushdown",
                "tokenized-vault", or "encryption-fpe".
        """
        settings = get_settings()
        response = await tag.get_tag_by_details(
            database_id, database_name, tag_name, schema_name, settings.auth,
            protection_type)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_tag(
            tag_group_id: str,
            database_id: int,
            friendly_name: str,
            protection_type: str = "governed",
            custom_role_provider_enabled: bool = False,
            mask_data_type_list: str | list[str] | None = None,
            encryption_fpe_options: dict | None = None
            ) -> dict:
        """Update an existing tag connection's masking configuration.

        SNOWFLAKE ONLY. Databricks tags are not ALTR-managed objects, so
        there is no Databricks tag configuration to update — change
        Databricks masking by editing the policy or its rules instead.

        Use `get_tags` to find the `tag_group_id` of the tag you want
        to update. To connect a new tag, use `connect_tag` instead.

        Args:
            tag_group_id: Tag group identifier from `get_tags`.
            database_id: Numeric ALTR database ID (from `get_database_id`).
            friendly_name: Display name for the tag in ALTR.
            protection_type: Masking type — "governed", "governed-pushdown",
                "tokenized-vault", or "encryption-fpe".
            custom_role_provider_enabled: Enable custom role provider UDF.
            mask_data_type_list: Optional list of data types to mask.
            encryption_fpe_options: Optional FPE config dict with 'alphabet'
                ("numeric"|"alphabetic"|"alphanumeric"), 'is_padded' (bool),
                'key_name' (str), and 'tweak_name' (str).
        """
        data = {
            "database_id": database_id,
            "friendly_name": friendly_name,
            "masking": {
                "protection_type": protection_type,
                "custom_role_provider": {
                    "enabled": custom_role_provider_enabled
                },
            },
        }
        if mask_data_type_list is not None:
            if isinstance(mask_data_type_list, str):
                mask_data_type_list = [mask_data_type_list]
            data["masking"]["mask_data_type_list"] = mask_data_type_list
        if encryption_fpe_options is not None:
            data["masking"]["encryption_fpe_options"] = encryption_fpe_options

        settings = get_settings()
        response = await tag.create_tag_by_group_id(
            tag_group_id, settings.auth, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def disconnect_tag_by_details(
            database_id: int,
            database_name: str,
            schema_name: str,
            tag_name: str,
            ignore_errors: bool = False
            ) -> dict:
        """Disconnect a tag from ALTR by database, schema, and tag name.

        SNOWFLAKE ONLY. Databricks tags are not ALTR objects; to stop
        masking a Databricks column, delete the policy with
        `delete_policy` instead.

        Alternative to `disconnect_tag` when you don't have the tag_group_id
        but know the database/schema/tag details.

        Args:
            database_id: Numeric ALTR database ID.
            database_name: Database name in ALTR.
            schema_name: Schema name containing the tag.
            tag_name: Tag name to disconnect.
            ignore_errors: If true, force-forget the tag even if cleanup fails.
        """
        data = {
            "database_id": database_id,
            "database_name": database_name,
            "schema_name": schema_name,
            "tag_name": tag_name,
        }
        settings = get_settings()
        response = await tag.delete_tag_by_details(
            settings.auth, data, ignore_errors)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def connect_tag(
            database_name: str,
            schema_name: str,
            tag_name: str
            ) -> dict:
        """Connect a Snowflake tag to ALTR so it can be used in masking
        policies.

        SNOWFLAKE ONLY — do NOT use for Databricks. There is no Databricks
        equivalent of this tool: Databricks tags are not stored as ALTR
        objects, they are just raw strings referenced at policy-creation
        time. Skip `connect_tag` entirely for Databricks and pass the raw
        tag name string directly to `create_policy`.

        For Snowflake, this call registers an existing Snowflake tag as a
        first-class ALTR tag object — it gets a `tag_group_id`, masking
        configuration, etc. The tag must already exist in Snowflake. Once
        connected, it appears in `get_tags`, can be inspected with
        `get_tag_details*`, edited with `update_tag`, and used in
        `create_policy`.

        The tool automatically resolves the friendly name to the actual
        Snowflake database name for the API call.

        Args:
            database_name: Friendly database name as shown in ALTR
                (the `friendlyDatabaseName` from `get_databases`).
            schema_name: Exact schema name inside the target database.
            tag_name: Tag to associate with this database/schema.
        """
        settings = get_settings()
        response = await tag.connect_tag_request(
            database_name,
            schema_name,
            tag_name,
            settings.auth
        )
        return {"success": True, "data": response, "error": None}
