import json

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from altr_mcp.settings import get_settings
from altr_mcp.utils import audit_report
from altr_mcp.utils.logging import log_tool


def _parse_json_param(value):
    """Accept either a dict or a JSON string; return a dict or None."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, ValueError) as e:
        raise ValueError(f"Invalid JSON: {e}") from e


def _build_definition_body(
        name: str,
        integration_type: str,
        description: str | None,
        lookback_days: int | None,
        timezone: str | None,
        schedule_cron: str | None,
        schedule_enabled: bool | None,
        schedule_timezone: str | None,
        delivery: str | dict | None,
        filters: str | dict | None,
) -> dict:
    body: dict = {
        "name": name,
        "integration_type": integration_type,
    }
    if description is not None:
        body["description"] = description
    if lookback_days is not None or timezone is not None:
        report_window: dict = {}
        if lookback_days is not None:
            report_window["lookback_days"] = lookback_days
        if timezone is not None:
            report_window["timezone"] = timezone
        body["report_window"] = report_window
    if (schedule_cron is not None
            or schedule_enabled is not None
            or schedule_timezone is not None):
        schedule: dict = {}
        if schedule_cron is not None:
            schedule["cron"] = schedule_cron
        if schedule_enabled is not None:
            schedule["enabled"] = schedule_enabled
        if schedule_timezone is not None:
            schedule["timezone"] = schedule_timezone
        body["schedule"] = schedule
    if delivery is not None:
        body["delivery"] = _parse_json_param(delivery)
    if filters is not None:
        body["filters"] = _parse_json_param(filters)
    return body


def register(mcp: FastMCP) -> None:

    # ── Definitions ──────────────────────────────────────────────────────────

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_report_definitions(
            limit: int | None = None,
            cursor: str | None = None,
            archived: bool | None = None
            ) -> dict:
        """List audit report definitions.

        Returns paginated definitions ordered by creation time descending.
        Use `cursor` to page through results.

        Args:
            limit: Max results per page.
            cursor: Pagination cursor from a prior call.
            archived: If True, return only archived definitions.
                If False or omitted, return only active definitions.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor
        if archived is not None:
            params["archived"] = archived

        response = await audit_report.list_definitions(settings.auth, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_report_definition(
            name: str,
            integration_type: str,
            description: str | None = None,
            lookback_days: int | None = None,
            timezone: str | None = None,
            schedule_cron: str | None = None,
            schedule_enabled: bool | None = None,
            schedule_timezone: str | None = None,
            delivery: str | dict | None = None,
            filters: str | dict | None = None,
            ) -> dict:
        """Create a new audit report definition.

        Defines what data is included, how it is scheduled, and where it
        is delivered. After creating, use `trigger_report_definition` to
        generate a report on demand.

        Args:
            name: Unique display name for the definition.
            integration_type: Data source type. Values: "oltp", "snowflake".
            description: Optional human-readable description.
            lookback_days: Number of complete calendar days to include in each
                report window (excludes the trigger day).
            timezone: IANA timezone for the report window
                (e.g. "America/New_York").
            schedule_cron: 6-field cron expression controlling when the
                report runs automatically. Format:
                "minute hour day-of-month month day-of-week year"
                Use ? in day-of-month OR day-of-week (not both) when the
                other field is specified. Use * for "every".
                Days: SUN MON TUE WED THU FRI SAT
                Months: JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC
                Common examples — convert natural language like:
                  "every day at 12 PM"          → "0 12 * * ? *"
                  "every day at 9 AM"           → "0 9 * * ? *"
                  "every Monday at 9 AM"        → "0 9 ? * MON *"
                  "every weekday at 8:30 AM"    → "30 8 ? * MON-FRI *"
                  "every Sunday at 6 PM"        → "0 18 ? * SUN *"
                  "first day of month midnight" → "0 0 1 * ? *"
                  "every hour"                  → "0 * * * ? *"
            schedule_enabled: Whether the schedule is active.
            schedule_timezone: IANA timezone for schedule evaluation
                (e.g. "America/New_York"). All cron times are interpreted
                in this timezone.
            delivery: Delivery configuration as a dict or JSON string.
                Shape: {"channels": [{"type": "email", "enabled": bool,
                "recipients": ["email@example.com"]}]}.
            filters: Filter groups as a dict or JSON string. Shape:
                {"filter_groups": [{"filters": [{"field": "database_name",
                "pattern": {"match_type": "exact", "value": "mydb"}}]}]}.
                OLTP fields: database_name, table_name, schema_name,
                column_name, statement_type, consuming_user, event_source,
                event_name, repo_user, repo_host, repo_name, repo_type,
                application_name, client_host, connection_id,
                statement_text, policy_blocked, execution_success,
                row_count. Snowflake fields: username, current_role,
                ip_address, client, query_type, warehouse, warehouse_size.
        """
        settings = get_settings()
        try:
            body = _build_definition_body(
                name=name,
                integration_type=integration_type,
                description=description,
                lookback_days=lookback_days,
                timezone=timezone,
                schedule_cron=schedule_cron,
                schedule_enabled=schedule_enabled,
                schedule_timezone=schedule_timezone,
                delivery=delivery,
                filters=filters,
            )
        except ValueError as e:
            return {"success": True, "data": {"success": False, "message": str(e)}, "error": None}
        response = await audit_report.create_definition(settings.auth, body)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_report_definition(definition_id: str) -> dict:
        """Get a single audit report definition by ID.

        Args:
            definition_id: ID of the report definition.
        """
        settings = get_settings()
        response = await audit_report.get_definition(
            settings.auth, definition_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_report_definition(
            definition_id: str,
            name: str,
            integration_type: str,
            description: str | None = None,
            lookback_days: int | None = None,
            timezone: str | None = None,
            schedule_cron: str | None = None,
            schedule_enabled: bool | None = None,
            schedule_timezone: str | None = None,
            delivery: str | dict | None = None,
            filters: str | dict | None = None,
            ) -> dict:
        """Update an existing audit report definition (full replacement).

        Replaces the definition's configuration entirely. All fields that
        should be preserved must be included.

        Args:
            definition_id: ID of the definition to update.
            name: Unique display name for the definition.
            integration_type: Data source type. Values: "oltp", "snowflake".
            description: Optional human-readable description.
            lookback_days: Number of complete calendar days to include in each
                report window (excludes the trigger day).
            timezone: IANA timezone for the report window
                (e.g. "America/New_York").
            schedule_cron: 6-field cron expression controlling when the
                report runs automatically. Format:
                "minute hour day-of-month month day-of-week year"
                Use ? in day-of-month OR day-of-week (not both) when the
                other field is specified. Use * for "every".
                Days: SUN MON TUE WED THU FRI SAT
                Months: JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC
                Common examples — convert natural language like:
                  "every day at 12 PM"          → "0 12 * * ? *"
                  "every day at 9 AM"           → "0 9 * * ? *"
                  "every Monday at 9 AM"        → "0 9 ? * MON *"
                  "every weekday at 8:30 AM"    → "30 8 ? * MON-FRI *"
                  "every Sunday at 6 PM"        → "0 18 ? * SUN *"
                  "first day of month midnight" → "0 0 1 * ? *"
                  "every hour"                  → "0 * * * ? *"
            schedule_enabled: Whether the schedule is active.
            schedule_timezone: IANA timezone for schedule evaluation
                (e.g. "America/New_York"). All cron times are interpreted
                in this timezone.
            delivery: Delivery configuration as a dict or JSON string.
                Shape: {"channels": [{"type": "email", "enabled": bool,
                "recipients": ["email@example.com"]}]}.
            filters: Filter groups as a dict or JSON string. Shape:
                {"filter_groups": [{"filters": [{"field": "database_name",
                "pattern": {"match_type": "exact", "value": "mydb"}}]}]}.
                OLTP fields: database_name, table_name, schema_name,
                column_name, statement_type, consuming_user, event_source,
                event_name, repo_user, repo_host, repo_name, repo_type,
                application_name, client_host, connection_id,
                statement_text, policy_blocked, execution_success,
                row_count. Snowflake fields: username, current_role,
                ip_address, client, query_type, warehouse, warehouse_size.
        """
        settings = get_settings()
        try:
            body = _build_definition_body(
                name=name,
                integration_type=integration_type,
                description=description,
                lookback_days=lookback_days,
                timezone=timezone,
                schedule_cron=schedule_cron,
                schedule_enabled=schedule_enabled,
                schedule_timezone=schedule_timezone,
                delivery=delivery,
                filters=filters,
            )
        except ValueError as e:
            return {"success": True, "data": {"success": False, "message": str(e)}, "error": None}
        response = await audit_report.update_definition(
            settings.auth, definition_id, body)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def archive_report_definition(definition_id: str) -> dict:
        """Archive (soft-delete) an audit report definition.

        Archived definitions are hidden from normal listings but can be
        restored with `restore_report_definition`.

        Args:
            definition_id: ID of the definition to archive.
        """
        settings = get_settings()
        response = await audit_report.archive_definition(
            settings.auth, definition_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def restore_report_definition(definition_id: str) -> dict:
        """Restore an archived audit report definition.

        Args:
            definition_id: ID of the archived definition to restore.
        """
        settings = get_settings()
        response = await audit_report.restore_definition(
            settings.auth, definition_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def trigger_report_definition(definition_id: str) -> dict:
        """Trigger an on-demand audit report for a definition.

        Generates a report instance immediately outside of the normal
        schedule. Rate-limited to one trigger per definition per 5 minutes.

        Args:
            definition_id: ID of the definition to trigger.
        """
        settings = get_settings()
        response = await audit_report.trigger_definition(
            settings.auth, definition_id)
        return {"success": True, "data": response, "error": None}

    # ── Instances ────────────────────────────────────────────────────────────

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_report_instances(
            definition_id: str,
            limit: int | None = None,
            cursor: str | None = None
            ) -> dict:
        """List report instances for a given definition.

        Each instance represents one generated report. Instances are
        returned newest-first.

        Args:
            definition_id: ID of the report definition.
            limit: Max results per page.
            cursor: Pagination cursor from a prior call.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor

        response = await audit_report.list_instances(
            settings.auth, definition_id, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_report_instance(
            definition_id: str,
            instance_id: str
            ) -> dict:
        """Get a single report instance by ID.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
        """
        settings = get_settings()
        response = await audit_report.get_instance(
            settings.auth, definition_id, instance_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_report_instance_download_url(
            definition_id: str,
            instance_id: str,
            format: str = "pdf"
            ) -> dict:
        """Get a download URL for a report instance.

        Returns a pre-signed URL to download the report file.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
            format: File format. Values: "pdf" (default), "csv".
        """
        settings = get_settings()
        params = {"format": format}
        response = await audit_report.get_instance_download_url(
            settings.auth, definition_id, instance_id, params)
        return {"success": True, "data": response, "error": None}

    # ── Comments ─────────────────────────────────────────────────────────────

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_report_comments(
            definition_id: str,
            instance_id: str,
            limit: int | None = None,
            cursor: str | None = None
            ) -> dict:
        """List comments on a report instance.

        Pinned comments appear first, followed by the rest in chronological
        order.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
            limit: Max results per page.
            cursor: Pagination cursor from a prior call.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor

        response = await audit_report.list_comments(
            settings.auth, definition_id, instance_id, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_report_comment(
            definition_id: str,
            instance_id: str,
            text: str
            ) -> dict:
        """Add a comment to a report instance.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
            text: Comment text to add.
        """
        settings = get_settings()
        body = {"text": text}
        response = await audit_report.create_comment(
            settings.auth, definition_id, instance_id, body)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def pin_report_comment(
            definition_id: str,
            instance_id: str,
            comment_id: str
            ) -> dict:
        """Pin a comment on a report instance.

        Only one comment per instance can be pinned at a time. Pinning is
        allowed after the instance has been signed off.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
            comment_id: ID of the comment to pin.
        """
        settings = get_settings()
        response = await audit_report.pin_comment(
            settings.auth, definition_id, instance_id, comment_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def unpin_report_comment(
            definition_id: str,
            instance_id: str,
            comment_id: str
            ) -> dict:
        """Unpin the currently pinned comment on a report instance.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
            comment_id: ID of the comment to unpin.
        """
        settings = get_settings()
        response = await audit_report.unpin_comment(
            settings.auth, definition_id, instance_id, comment_id)
        return {"success": True, "data": response, "error": None}

    # ── Sign-offs ────────────────────────────────────────────────────────────

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_report_sign_off(
            definition_id: str,
            instance_id: str
            ) -> dict:
        """Get the current user's sign-off for a report instance.

        Returns null/empty if the current user has not yet signed off.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
        """
        settings = get_settings()
        response = await audit_report.get_sign_off(
            settings.auth, definition_id, instance_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_report_sign_off(
            definition_id: str,
            instance_id: str,
            action: str = "approve",
            attestation: bool = True,
            comments: str | None = None
            ) -> dict:
        """Sign off on a report instance.

        Records the current user's approval of the report. After signing
        off, comments can be pinned on the instance.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
            action: Sign-off action. Values: "approve" (default).
            attestation: Whether to attest to the accuracy of the report
                (default True).
            comments: Optional comments to include with the sign-off.
        """
        settings = get_settings()
        body: dict = {
            "action": action,
            "attestation": attestation,
        }
        if comments is not None:
            body["comments"] = comments

        response = await audit_report.create_sign_off(
            settings.auth, definition_id, instance_id, body)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_report_sign_offs(
            definition_id: str,
            instance_id: str,
            limit: int | None = None,
            cursor: str | None = None
            ) -> dict:
        """List all sign-offs for a report instance.

        Returns sign-offs from all users who have reviewed the instance.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
            limit: Max results per page.
            cursor: Pagination cursor from a prior call.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor

        response = await audit_report.list_sign_offs(
            settings.auth, definition_id, instance_id, params)
        return {"success": True, "data": response, "error": None}
