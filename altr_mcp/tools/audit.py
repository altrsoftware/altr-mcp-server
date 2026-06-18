from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from altr_mcp.utils.logging import log_tool
from altr_mcp.settings import get_settings
from altr_mcp.utils import audit


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    @log_tool
    async def search_audits(
            limit: int | None = None,
            offset: int | None = None,
            from_date_time: str | None = None,
            to_date_time: str | None = None,
            consuming_user: str | list[str] | None = None,
            consuming_user_email: str | list[str] | None = None,
            query_id: str | list[str] | None = None,
            sidecar_id: str | list[str] | None = None,
            sidecar_instance_id: str | list[str] | None = None,
            table_name: str | list[str] | None = None,
            schema_name: str | list[str] | None = None,
            database_name: str | list[str] | None = None,
            column_name: str | list[str] | None = None,
            statement_type: str | list[str] | None = None,
            statement_text_contains: str | None = None,
            order_by: str | None = None,
            sort_by: str | None = None
            ) -> dict:
        """Search sidecar query audits with filters.

        Triggers an async search and returns a search_uuid (valid 30 days).
        Use `get_audit_results` with the search_uuid to retrieve results.
        All filters are combined with AND logic.

        Args:
            limit: Max results (default 10000, max 100000).
            offset: Skip this many results.
            from_date_time: RFC3339 UTC start time
                (e.g. "2025-01-01T00:00:00Z").
            to_date_time: RFC3339 UTC end time.
            consuming_user: Filter by consuming usernames (case-insensitive).
                Pass a single string or a list of strings.
            consuming_user_email: Filter by consuming user emails.
                Pass a single string or a list of strings.
            query_id: Filter by specific query IDs.
                Pass a single string or a list of strings.
            sidecar_id: Filter by sidecar IDs.
                Pass a single string or a list of strings.
            sidecar_instance_id: Filter by sidecar instance IDs.
                Pass a single string or a list of strings.
            table_name: Filter by table names.
                Pass a single string or a list of strings.
            schema_name: Filter by schema names.
                Pass a single string or a list of strings.
            database_name: Filter by database names.
                Pass a single string or a list of strings.
            column_name: Filter by column names.
                Pass a single string or a list of strings.
            statement_type: Filter by statement types.
                Pass a single string or a list of strings.
            statement_text_contains: Case-insensitive substring
                match on SQL text.
            order_by: "asc" or "desc" (default "desc").
            sort_by: "event_time" or "rows_accessed" (default "event_time").
        """
        def _as_list(val):
            if val is None:
                return None
            return val if isinstance(val, list) else [val]

        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if from_date_time is not None:
            params["from_date_time"] = from_date_time
        if to_date_time is not None:
            params["to_date_time"] = to_date_time
        if consuming_user is not None:
            params["consuming_user"] = _as_list(consuming_user)
        if consuming_user_email is not None:
            params["consuming_user_email"] = _as_list(consuming_user_email)
        if query_id is not None:
            params["query_id"] = _as_list(query_id)
        if sidecar_id is not None:
            params["sidecar_id"] = _as_list(sidecar_id)
        if sidecar_instance_id is not None:
            params["sidecar_instance_id"] = _as_list(sidecar_instance_id)
        if table_name is not None:
            params["table_name"] = _as_list(table_name)
        if schema_name is not None:
            params["schema_name"] = _as_list(schema_name)
        if database_name is not None:
            params["database_name"] = _as_list(database_name)
        if column_name is not None:
            params["column_name"] = _as_list(column_name)
        if statement_type is not None:
            params["statement_type"] = _as_list(statement_type)
        if statement_text_contains is not None:
            params["statement_text_contains"] = statement_text_contains
        if order_by is not None:
            params["order_by"] = order_by
        if sort_by is not None:
            params["sort_by"] = sort_by

        response = await audit.search_audits(
            settings.auth, params
        )
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_audit_results(
            search_uuid: str,
            limit: int | None = None,
            next_page_token: str | None = None
            ) -> dict:
        """Get results from a previously triggered audit search.

        Results may not be immediately available — a 202 response means
        the search is still processing. Retry after a short wait.

        Args:
            search_uuid: UUID returned by `search_audits`.
            limit: Max results per page (default 250, max 250).
            next_page_token: Pagination token from a prior call.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if next_page_token is not None:
            params["next_page_token"] = next_page_token

        response = await audit.get_audit_results(
                settings.auth, search_uuid, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def search_system_audits(
            category: str,
            limit: int | None = None,
            offset: int | None = None,
            wait: int | None = None,
            from_date_time: str | None = None,
            to_date_time: str | None = None
            ) -> dict:
        """Search ALTR platform system audits.

        Starts an async query against system audit logs. Returns a token
        to retrieve results with `get_system_audit_results`. If `wait`
        is set, the API may return results directly (200) or a token
        for later retrieval (202).

        The `from` and `to` time range may be at most one week.

        Args:
            category: Audit category. Values: "API Keys", "Locks",
                "Data", "Administrators", "Thresholds", "Anomalies",
                "Applications", "User Groups", "Data Sources",
                "Row Access Policy", "Unified Access Policy",
                "Access Requests", "Access Management Policy",
                "Impersonation Policy".
            limit: Max results (1-100, default 50).
            offset: Results to skip (default 0).
            wait: Milliseconds to wait for results (-1 to 1000,
                default 100). Set to -1 to return immediately with token.
            from_date_time: ISO 8601 UTC start time. Defaults to 48h ago.
            to_date_time: ISO 8601 UTC end time. Defaults to now.
        """
        settings = get_settings()
        params = {"category": category}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if wait is not None:
            params["wait"] = wait
        if from_date_time is not None:
            params["from"] = from_date_time
        if to_date_time is not None:
            params["to"] = to_date_time

        response = await audit.search_system_audits(settings.auth, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_system_audit_results(token: str) -> dict:
        """Get results from a system audit query.

        Use the token returned by `search_system_audits`. If the response
        has `moreData: true`, use the new token to fetch the next page.

        Args:
            token: Token from `search_system_audits` or a prior call's
                response.
        """
        settings = get_settings()
        response = await audit.get_system_audit_results(settings.auth, token)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def search_query_audits(
            limit: int | None = None,
            offset: int | None = None,
            from_date_time: str | None = None,
            to_date_time: str | None = None,
            executing_role: str | None = None,
            executing_user: str | None = None,
            query_id: str | None = None,
            policy_tag_name: str | None = None,
            policy_tag_value: str | None = None,
            policy_column_database_name: str | None = None,
            policy_column_schema_name: str | None = None,
            policy_column_table_name: str | None = None,
            policy_column_name: str | None = None,
            order_by: str | None = None,
            sort_by: str | None = None
            ) -> dict:
        """Search Snowflake query audits (tag and column masking).

        Triggers an async search and returns a search_uuid (valid 30 days).
        Use `get_query_audit_results` with the search_uuid to retrieve
        results. All filters are combined with AND logic.

        Use this for Snowflake tag-based or column-based masking audits.
        For sidecar proxy audits, use `search_audits` instead.

        Args:
            limit: Max results (default 10000, max 10000).
            offset: Skip this many results.
            from_date_time: RFC3339 UTC start time
                (e.g. "2025-01-01T00:00:00Z").
            to_date_time: RFC3339 UTC end time. Must not be in the future.
            executing_role: Filter by role executing
                the query (case-insensitive).
            executing_user: Filter by user executing
                the query (case-insensitive).
            query_id: Filter by query identifier
                (case-insensitive).
            policy_tag_name: Filter by policy tag name
                (case-insensitive).
            policy_tag_value: Filter by policy tag value
                (case-insensitive).
            policy_column_database_name: Filter by
                database name (case-insensitive).
            policy_column_schema_name: Filter by schema
                name (case-insensitive).
            policy_column_table_name: Filter by table name (case-insensitive).
            policy_column_name: Filter by column name (case-insensitive).
            order_by: "asc" or "desc" (default "desc").
            sort_by: "event_time" or "rows_accessed" (default "event_time").
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if from_date_time is not None:
            params["from_date_time"] = from_date_time
        if to_date_time is not None:
            params["to_date_time"] = to_date_time
        if executing_role is not None:
            params["executing_role"] = executing_role
        if executing_user is not None:
            params["executing_user"] = executing_user
        if query_id is not None:
            params["query_id"] = query_id
        if policy_tag_name is not None:
            params["policy_tag_name"] = policy_tag_name
        if policy_tag_value is not None:
            params["policy_tag_value"] = policy_tag_value
        if policy_column_database_name is not None:
            params["policy_column_database_name"] = policy_column_database_name
        if policy_column_schema_name is not None:
            params["policy_column_schema_name"] = policy_column_schema_name
        if policy_column_table_name is not None:
            params["policy_column_table_name"] = policy_column_table_name
        if policy_column_name is not None:
            params["policy_column_name"] = policy_column_name
        if order_by is not None:
            params["order_by"] = order_by
        if sort_by is not None:
            params["sort_by"] = sort_by

        response = await audit.search_query_audits(settings.auth, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_query_audit_results(
            search_uuid: str,
            limit: int | None = None,
            next_page_token: str | None = None
            ) -> dict:
        """Get results from a previously triggered query audit search.

        Results may not be immediately available — a 202 response means
        the search is still processing. Retry after a short wait.

        Use this to retrieve results from `search_query_audits`.
        For sidecar audit results, use `get_audit_results` instead.

        Args:
            search_uuid: UUID returned by `search_query_audits`.
            limit: Max results per page (default 250, max 250).
            next_page_token: Pagination token from a prior call.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if next_page_token is not None:
            params["next_page_token"] = next_page_token

        response = await audit.get_query_audit_results(
                settings.auth, search_uuid, params)
        return {"success": True, "data": response, "error": None}
