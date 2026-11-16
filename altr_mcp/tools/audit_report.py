import json
import zoneinfo

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from altr_mcp.settings import get_settings
from altr_mcp.utils import audit_report, database, sidecar_config
from altr_mcp.utils.logging import log_tool

# The console's report builder offers these choices and no others.
LOOKBACK_DAYS = (1, 3, 7, 14, 30, 60, 90)
MAX_APPROVALS = 5
MAX_RECIPIENTS = 20
RETENTION_DAYS = 90
OLTP_FIELDS = (
    "consuming_user", "statement_type", "database_name", "schema_name",
    "table_name", "column_name", "event_source", "event_name", "repo_user",
    "repo_host", "application_name", "client_host", "connection_id",
    "execution_success", "statement_text",
)
SNOWFLAKE_FIELDS = (
    "username", "query_type", "event_source", "event_name", "current_role",
    "client", "ip_address", "warehouse", "warehouse_size",
    "account_identifier", "account_region", "query_text",
)
FIELDS = {"oltp": OLTP_FIELDS, "snowflake": SNOWFLAKE_FIELDS}
SCOPE_FIELDS = {"oltp": ("repo_name", "repo_type"), "snowflake": ("database_id",)}
STATEMENT_TYPES = (
    "SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP",
    "TRUNCATE", "MERGE", "GRANT", "REVOKE", "COPY", "CALL", "READ",
    "ALTER_SESSION", "USE", "SHOW", "DESCRIBE", "EXPLAIN", "DDL", "DML",
    "QUERY",
)
OLTP_EVENT_NAMES = (
    "STATEMENT_EXECUTION", "CONNECT_EXECUTION", "SESSION_EXECUTION")
OPERATORS = {
    "is": ("include", "exact"),
    "is_not": ("exclude", "exact"),
    "contains": ("include", "contains"),
    "does_not_contain": ("exclude", "contains"),
}
GENERATING = ("generating", "in_progress", "finalizing")
SNOWFLAKE_DB_TYPE = "snowflake_external_functions"
UNSCOPED_SNOWFLAKE = (
    "This report has no database_ids, so it covers query activity from "
    "every connected Snowflake database.")


def _failed(response) -> bool:
    return isinstance(response, dict) and response.get("success") is False


def _failure(response: dict) -> str:
    if "body" in response:
        body = (response.get("body") or "").strip()[:200]
        return f"HTTP {response.get('status_code')}" + (f": {body}" if body else "")
    return str(response.get("message"))


async def _read(fetch, what: str, *args) -> dict:
    response = await fetch(get_settings().auth, *args)
    if _failed(response):
        raise ValueError(f"Could not read {what}: {_failure(response)}")
    return response or {}


def _parse_list(value, what: str) -> list | None:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError as e:
            raise ValueError(f"{what} is not valid JSON: {e}") from e
    if value is not None and not isinstance(value, list):
        raise ValueError(f"{what} must be a list.")
    return value


def _check_limit(limit: int | None) -> None:
    if limit is not None and not 1 <= limit <= 100:
        raise ValueError("limit must be 1-100 (the API caps pages at 100).")


def _page(limit: int | None, cursor: str | None) -> dict:
    _check_limit(limit)
    params = {}
    if limit is not None:
        params["limit"] = limit
    if cursor is not None:
        params["cursor"] = cursor
    return params


def _check_integration_type(integration_type: str) -> None:
    if integration_type not in FIELDS:
        raise ValueError('integration_type must be "oltp" or "snowflake".')


def _check_timezone(tz: str) -> None:
    zones = zoneinfo.available_timezones()
    if zones and tz != "UTC" and tz not in zones:
        raise ValueError(
            f"Unknown timezone {tz!r}: use an IANA name such as "
            '"America/New_York" or "UTC".')


def _check_cron(cron: str) -> None:
    parts = cron.split()
    if len(parts) != 6:
        raise ValueError(
            "schedule_cron needs 6 fields: minute hour day-of-month month "
            "day-of-week year.")
    if [i for i, p in enumerate(parts) if p == "?"] not in ([2], [4]):
        raise ValueError(
            "schedule_cron needs ? in exactly one of day-of-month and "
            'day-of-week, e.g. "0 9 * * ? *".')


def _check_lookback(lookback_days: int) -> None:
    if lookback_days not in LOOKBACK_DAYS:
        raise ValueError(
            f"lookback_days must be one of {', '.join(map(str, LOOKBACK_DAYS))}.")


def _check_approvals(required_approvals: int) -> None:
    if not 0 <= required_approvals <= MAX_APPROVALS:
        raise ValueError(f"required_approvals must be 0-{MAX_APPROVALS}.")


def _delivery(recipients) -> dict:
    recipients = _parse_list(recipients, "recipients") or []
    unique = list(dict.fromkeys(r.strip() for r in recipients if isinstance(r, str)))
    if not unique or not all("@" in r for r in unique):
        raise ValueError("recipients needs at least one email address.")
    if len(unique) > MAX_RECIPIENTS:
        raise ValueError(f"recipients takes at most {MAX_RECIPIENTS} addresses.")
    return {"channels": [{"type": "email", "recipients": unique, "enabled": True}]}


def _field_filters(filters, integration_type: str) -> list[dict]:
    """Build the API filters for the console's field rows, in one group."""
    entries = _parse_list(filters, "filters") or []
    allowed = FIELDS[integration_type]
    patterns: dict[tuple[str, str], list] = {}
    success: list[dict] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Each filter must be an object with field, operator and values.")
        field, operator = entry.get("field"), entry.get("operator")
        values = entry.get("values")
        if field in SCOPE_FIELDS[integration_type]:
            scope = "repo_names" if integration_type == "oltp" else "database_ids"
            raise ValueError(f"Scope the report with {scope}, not a {field} filter.")
        if field not in allowed:
            raise ValueError(
                f"{field!r} is not a {integration_type} filter field. "
                f"Fields: {', '.join(allowed)}.")
        if operator not in OPERATORS:
            raise ValueError(
                f"operator must be one of {', '.join(OPERATORS)}, not {operator!r}.")
        if not isinstance(values, list):
            values = [values]
        mode, match_type = OPERATORS[operator]
        if field == "execution_success":
            if (operator not in ("is", "is_not") or success
                    or len(values) != 1 or str(values[0]).lower() not in ("true", "false")):
                raise ValueError(
                    'execution_success takes one filter, "is" or "is_not", '
                    "with values [true] or [false].")
            success.append({"field": field, "mode": mode,
                            "value": str(values[0]).lower() == "true"})
            continue
        if not values or not all(isinstance(v, str) and v.strip() for v in values):
            raise ValueError(f"{field} needs a non-blank text value in values.")
        if field == "statement_type" or (integration_type == "oltp" and field == "event_name"):
            choices = STATEMENT_TYPES if field == "statement_type" else OLTP_EVENT_NAMES
            values = [v.strip().upper() for v in values]
            bad = [v for v in values if v not in choices]
            if bad:
                raise ValueError(f"{field} values must be among: {', '.join(choices)}.")
        patterns.setdefault((field, mode), []).extend(
            {"match_type": match_type, "value": v} for v in values)
    built = [{"field": f, "mode": m, "patterns": p} for (f, m), p in patterns.items()]
    return built + success


async def _scope_filters(
        integration_type: str, repo_names, database_ids) -> list[dict]:
    """The console's scope: OLTP repos with their types, or Snowflake databases."""
    repo_names = _parse_list(repo_names, "repo_names")
    database_ids = _parse_list(database_ids, "database_ids")
    if integration_type == "oltp":
        if database_ids:
            raise ValueError("database_ids scopes Snowflake reports; use repo_names.")
        if not repo_names:
            return []
        types = []
        for name in dict.fromkeys(repo_names):
            repo = await _read(sidecar_config.get_repo, f"repo {name!r}", name)
            if repo.get("type"):
                types.append(repo["type"])
        scope = [{"field": "repo_name", "mode": "include",
                  "patterns": [{"match_type": "exact", "value": n}
                               for n in dict.fromkeys(repo_names)]}]
        if types:
            scope.append({"field": "repo_type", "mode": "include",
                          "patterns": [{"match_type": "exact", "value": t}
                                       for t in dict.fromkeys(types)]})
        return scope
    if repo_names:
        raise ValueError("repo_names scopes OLTP reports; use database_ids.")
    if not database_ids:
        return []
    wanted = {str(i) for i in database_ids}
    found: set[str] = set()
    offset = 0
    while wanted - found:
        page = await database._get_databases(
            {"databaseType": SNOWFLAKE_DB_TYPE, "limit": 100, "offset": offset},
            get_settings().auth)
        if _failed(page):
            raise ValueError(f"Could not read the Snowflake databases: {_failure(page)}")
        rows = (page.get("data") or {}).get("databases") or []
        found |= {str(r.get("id")) for r in rows} & wanted
        offset += len(rows)
        if not rows or offset >= (page.get("data") or {}).get("count", 0):
            break
    missing = sorted(wanted - found)
    if missing:
        raise ValueError(
            f"No connected Snowflake database has id {', '.join(missing)}. "
            "List them with get_databases.")
    return [{"field": "database_id", "mode": "include",
             "patterns": [{"match_type": "exact", "value": i}
                          for i in dict.fromkeys(str(i) for i in database_ids)]}]


def _is_scope(f: dict, integration_type: str) -> bool:
    """A scope filter as the console writes it: an exact include."""
    if f.get("field") not in SCOPE_FIELDS[integration_type]:
        return False
    return f.get("mode") == "include" and all(
        p.get("match_type", "exact") == "exact" for p in f.get("patterns") or [])


def _is_field_filter(f: dict, integration_type: str) -> bool:
    return f.get("field") in FIELDS[integration_type]


def _filter_groups(group: list[dict]) -> dict:
    return {"filter_groups": [{"filters": group}] if group else []}


async def _no_generating_instance(definition_id: str, action: str) -> None:
    page = await _read(audit_report.list_instances, "the report instances",
                       definition_id, {"limit": 100})
    if any(i.get("status") in GENERATING for i in page.get("items") or []):
        raise ValueError(
            f"Can't {action} definition {definition_id} while a report is "
            "generating. Try again when it finishes.")


async def _open_instance(definition_id: str, instance_id: str, action: str) -> dict:
    """Refuse where the console hides comments and approval."""
    instance = await _read(audit_report.get_instance, f"instance {instance_id}",
                           definition_id, instance_id)
    required = instance.get("required_approvals") or 0
    if required == 0:
        raise ValueError(
            f"Can't {action}: instance {instance_id} needs no approvals, "
            "so it takes no comments or sign-offs.")
    if instance.get("status") in ("finalizing", "finalized"):
        raise ValueError(f"Can't {action}: instance {instance_id} is {instance['status']}.")
    if (instance.get("sign_off_count") or 0) >= required:
        raise ValueError(f"Can't {action}: instance {instance_id} is fully approved.")
    return instance


def _with_warning(response, warning: str | None) -> dict:
    result = {"success": True, "data": response, "error": None}
    if warning:
        result["warning"] = warning
    return result


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

        Definitions come back in no particular order. Page with
        `next_cursor` while `has_more` is true.

        Args:
            limit: Results per page, 1-100 (default 25).
            cursor: `next_cursor` from the previous page.
            archived: If True, return only archived definitions.
                If False or omitted, return only active definitions.
        """
        params = _page(limit, cursor)
        if archived is not None:
            params["archived"] = "true" if archived else "false"
        response = await audit_report.list_definitions(get_settings().auth, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_report_definition(
            name: str,
            integration_type: str,
            timezone: str,
            schedule_cron: str,
            required_approvals: int,
            recipients: list[str] | str,
            repo_names: list[str] | str | None = None,
            database_ids: list[int] | str | None = None,
            filters: list[dict] | str | None = None,
            description: str | None = None,
            lookback_days: int = 7,
            schedule_enabled: bool = True,
            ) -> dict:
        """Create an audit report definition, as the console's report builder does.

        Each report covers the activity of the last lookback_days complete
        days, runs on the schedule, and is emailed to the recipients. Each
        report is kept 90 days. Names don't have to be unique. Use
        `trigger_report_definition` to generate a report now.

        Args:
            name: Display name, at most 200 bytes.
            integration_type: "oltp" (sidecar repositories) or "snowflake".
            timezone: IANA timezone (e.g. "America/New_York") for both the
                report window and the schedule.
            schedule_cron: 6-field cron, in timezone: "minute hour
                day-of-month month day-of-week year". Put ? in exactly one
                of day-of-month and day-of-week. Days SUN-SAT, months
                JAN-DEC. Examples: every day at 9 AM "0 9 * * ? *"; every
                Monday at 9 AM "0 9 ? * MON *"; weekdays at 8:30 AM
                "30 8 ? * MON-FRI *"; first of the month "0 0 1 * ? *".
                A run can start up to 10 minutes after the cron time.
            required_approvals: Sign-offs that finalize each report, 0-5.
                With 0, reports take no comments or sign-offs. Each user
                counts once, and every sign-off through this server is the
                same user (the API key), so above 1 needs console users too.
            recipients: Email addresses that receive each report, 1-20, in
                the org's allowed email domains.
            repo_names: OLTP only: the sidecar repositories the report
                covers. Omit to cover every repository.
            database_ids: Snowflake only: ALTR ids of connected Snowflake
                databases (from `get_databases`) the report covers. Omit
                to cover every connected database; the result then carries
                a warning.
            filters: Field filters, ANDed together, as a list or JSON
                string of {"field": ..., "operator": ..., "values": [...]}.
                operator: "is", "is_not", "contains" or "does_not_contain".
                Matching ignores case. OLTP fields: consuming_user,
                statement_type, database_name, schema_name, table_name,
                column_name, event_source, event_name, repo_user,
                repo_host, application_name, client_host, connection_id,
                execution_success, statement_text. statement_type values:
                SELECT INSERT UPDATE DELETE CREATE ALTER DROP TRUNCATE
                MERGE GRANT REVOKE COPY CALL READ ALTER_SESSION USE SHOW
                DESCRIBE EXPLAIN DDL DML QUERY. OLTP event_name values:
                STATEMENT_EXECUTION, CONNECT_EXECUTION, SESSION_EXECUTION.
                execution_success takes one entry, "is" or "is_not", with
                values [true] or [false]. Snowflake fields: username,
                query_type, event_source, event_name, current_role,
                client, ip_address, warehouse, warehouse_size,
                account_identifier, account_region, query_text.
                statement_text and query_text values: at most 255 bytes,
                no backslash, and not only % and _. Up to 50 values per
                filter and 50 filters.
            description: Optional description, at most 1000 bytes.
            lookback_days: Complete days each report covers: 1, 3, 7, 14,
                30, 60 or 90. Default 7.
            schedule_enabled: Default True. False saves the schedule
                paused.
        """
        _check_integration_type(integration_type)
        _check_timezone(timezone)
        _check_cron(schedule_cron)
        _check_lookback(lookback_days)
        _check_approvals(required_approvals)
        delivery = _delivery(recipients)
        group = (await _scope_filters(integration_type, repo_names, database_ids)
                 + _field_filters(filters, integration_type))
        body = {
            "name": name,
            "description": description or "",
            "integration_type": integration_type,
            "filters": _filter_groups(group),
            "retention_days": RETENTION_DAYS,
            "schedule": {"cron": schedule_cron, "enabled": schedule_enabled,
                         "timezone": timezone},
            "report_window": {"lookback_days": lookback_days, "timezone": timezone},
            "required_approvals": required_approvals,
            "delivery": delivery,
        }
        unscoped = integration_type == "snowflake" and not any(
            f["field"] == "database_id" for f in group)
        response = await audit_report.create_definition(get_settings().auth, body)
        return _with_warning(response, UNSCOPED_SNOWFLAKE if unscoped else None)

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_report_definition(definition_id: str) -> dict:
        """Get a single audit report definition by ID.

        Args:
            definition_id: ID of the report definition.
        """
        response = await audit_report.get_definition(
            get_settings().auth, definition_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_report_definition(
            definition_id: str,
            name: str | None = None,
            description: str | None = None,
            timezone: str | None = None,
            schedule_cron: str | None = None,
            schedule_enabled: bool | None = None,
            lookback_days: int | None = None,
            required_approvals: int | None = None,
            recipients: list[str] | str | None = None,
            repo_names: list[str] | str | None = None,
            database_ids: list[int] | str | None = None,
            filters: list[dict] | str | None = None,
            ) -> dict:
        """Update an audit report definition, as the console's edit form does.

        Reads the definition and changes only what you pass; everything
        else is kept. The data source can't change. Refused while one of
        the definition's reports is generating, and for an archived
        definition (HTTP 409). A changed required_approvals or
        lookback_days applies to reports generated afterwards.

        Args:
            definition_id: ID of the definition to update.
            name: Display name, at most 200 bytes.
            description: Description, at most 1000 bytes; "" clears it.
            timezone: IANA timezone for both the report window and the
                schedule.
            schedule_cron: 6-field cron; see `create_report_definition`.
            schedule_enabled: False pauses the schedule; True resumes it.
            lookback_days: 1, 3, 7, 14, 30, 60 or 90.
            required_approvals: 0-5.
            recipients: Replaces the email recipients, 1-20.
            repo_names: OLTP only: replaces the repositories covered; []
                covers every repository.
            database_ids: Snowflake only: replaces the databases covered;
                [] covers every connected database.
            filters: Replaces the field filters; [] removes them. Same
                shape and rules as in `create_report_definition`.
        """
        stored = await _read(audit_report.get_definition,
                             f"definition {definition_id}", definition_id)
        integration_type = stored.get("integration_type") or "oltp"
        groups = (stored.get("filters") or {}).get("filter_groups") or []
        if len(groups) > 1 and (filters is not None or repo_names is not None
                                or database_ids is not None):
            raise ValueError(
                f"Definition {definition_id} has {len(groups)} filter groups, "
                "which neither the console nor this tool can edit. Change its "
                "other settings, or create a new definition.")
        await _no_generating_instance(definition_id, "update")

        report_window = dict(stored.get("report_window") or {})
        schedule = dict(stored.get("schedule") or {})
        if timezone is not None:
            _check_timezone(timezone)
            report_window["timezone"] = timezone
        if lookback_days is not None:
            _check_lookback(lookback_days)
            report_window["lookback_days"] = lookback_days
        if schedule_cron is not None:
            _check_cron(schedule_cron)
            schedule["cron"] = schedule_cron
        if not schedule.get("cron"):
            raise ValueError(
                f"Definition {definition_id} has no schedule: pass schedule_cron.")
        if schedule_enabled is not None:
            schedule["enabled"] = schedule_enabled
        schedule.setdefault("enabled", True)
        schedule["timezone"] = report_window.get("timezone") or "UTC"
        if required_approvals is not None:
            _check_approvals(required_approvals)
        if recipients is None:
            recipients = next(
                (c.get("recipients") for c in (stored.get("delivery") or {}).get("channels") or []
                 if c.get("type") == "email"), None)
            if not recipients:
                raise ValueError(
                    f"Definition {definition_id} has no email recipients: pass recipients.")
        delivery = _delivery(recipients)

        group = (groups[0].get("filters") or []) if groups else []
        if repo_names is not None or database_ids is not None:
            group = [f for f in group if not _is_scope(f, integration_type)]
            group = await _scope_filters(integration_type, repo_names, database_ids) + group
        if filters is not None:
            group = ([f for f in group if not _is_field_filter(f, integration_type)]
                     + _field_filters(filters, integration_type))
        body = {
            "name": name if name is not None else stored.get("name"),
            "description": (description if description is not None
                            else stored.get("description") or ""),
            "integration_type": integration_type,
            "filters": (_filter_groups(group) if len(groups) <= 1
                        else stored.get("filters")),
            "retention_days": stored.get("retention_days") or RETENTION_DAYS,
            "schedule": schedule,
            "report_window": report_window,
            "required_approvals": (required_approvals if required_approvals is not None
                                   else stored.get("required_approvals") or 0),
            "delivery": delivery,
        }
        unscoped = integration_type == "snowflake" and len(groups) <= 1 and not any(
            _is_scope(f, integration_type) for f in group)
        response = await audit_report.update_definition(
            get_settings().auth, definition_id, body)
        return _with_warning(response, UNSCOPED_SNOWFLAKE if unscoped else None)

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def archive_report_definition(definition_id: str) -> dict:
        """Archive an audit report definition (the console's Delete).

        Stops its schedule and hides it from listings. Its reports stay
        until their retention ends. `restore_report_definition` brings it
        back. Archiving an archived definition returns HTTP 409.

        Args:
            definition_id: ID of the definition to archive.
        """
        response = await audit_report.archive_definition(
            get_settings().auth, definition_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def restore_report_definition(definition_id: str) -> dict:
        """Restore an archived audit report definition.

        Restarts its schedule if the schedule is enabled. Restoring a
        definition that isn't archived returns HTTP 409.

        Args:
            definition_id: ID of the archived definition to restore.
        """
        response = await audit_report.restore_definition(
            get_settings().auth, definition_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def trigger_report_definition(definition_id: str) -> dict:
        """Start generating a report for a definition now (the console's Run).

        Returns the new instance_id at once; the report is generated in
        the background, so poll `get_report_instance` until its status
        is "generated" or "failed". Refused while another report of the
        definition is generating. A definition can't be triggered within
        5 minutes of its last run, scheduled runs included (HTTP 429), or
        while archived (HTTP 409).

        Args:
            definition_id: ID of the definition to trigger.
        """
        await _no_generating_instance(definition_id, "trigger")
        response = await audit_report.trigger_definition(
            get_settings().auth, definition_id)
        if _failed(response) and response.get("status_code") == 429:
            response = {**response, "message": (
                "This definition ran in the last 5 minutes. Try again "
                "after the cooldown.")}
        return {"success": True, "data": response, "error": None}

    # ── Instances ────────────────────────────────────────────────────────────

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_report_instances(
            definition_id: str,
            limit: int | None = None,
            cursor: str | None = None
            ) -> dict:
        """List the reports generated for a definition, newest first.

        Page with `next_cursor` while `has_more` is true; the last page
        can be empty.

        Args:
            definition_id: ID of the report definition.
            limit: Results per page, 1-100 (default 25).
            cursor: `next_cursor` from the previous page.
        """
        response = await audit_report.list_instances(
            get_settings().auth, definition_id, _page(limit, cursor))
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_report_instance(
            definition_id: str,
            instance_id: str
            ) -> dict:
        """Get a single report instance by ID.

        status is generating, generated, finalizing, finalized or failed.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
        """
        response = await audit_report.get_instance(
            get_settings().auth, definition_id, instance_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_report_instance_download_url(
            definition_id: str,
            instance_id: str,
            format: str = "pdf"
            ) -> dict:
        """Get a download URL for a report instance.

        The URL expires after 24 hours. Only a "generated" or "finalized"
        instance has one; any other status, finalizing included, returns
        HTTP 404.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
            format: "pdf" (default) or "csv", lowercase.
        """
        response = await audit_report.get_instance_download_url(
            get_settings().auth, definition_id, instance_id, {"format": format})
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

        The pinned comment comes first. Sign-offs appear as comments with a
        sign_off_action. An unknown instance returns an empty list.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
            limit: Results per page, 1-100 (default 25).
            cursor: `next_cursor` from the previous page.
        """
        response = await audit_report.list_comments(
            get_settings().auth, definition_id, instance_id, _page(limit, cursor))
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_report_comment(
            definition_id: str,
            instance_id: str,
            text: str
            ) -> dict:
        """Add a comment to a report instance.

        As in the console, refused when the instance needs no approvals,
        is finalizing or finalized, or is fully approved.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
            text: Comment text, at most 5000 bytes.
        """
        await _open_instance(definition_id, instance_id, "comment")
        response = await audit_report.create_comment(
            get_settings().auth, definition_id, instance_id, {"text": text})
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def pin_report_comment(
            definition_id: str,
            instance_id: str,
            comment_id: str
            ) -> dict:
        """Pin a comment on a report instance.

        One comment per instance can be pinned: pinning another while one
        is pinned returns HTTP 409, so unpin it first. Refused in the same
        instance states as `create_report_comment`.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
            comment_id: ID of the comment to pin.
        """
        await _open_instance(definition_id, instance_id, "pin a comment")
        response = await audit_report.pin_comment(
            get_settings().auth, definition_id, instance_id, comment_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def unpin_report_comment(
            definition_id: str,
            instance_id: str,
            comment_id: str
            ) -> dict:
        """Unpin a comment on a report instance.

        Refused in the same instance states as `create_report_comment`.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
            comment_id: ID of the pinned comment.
        """
        await _open_instance(definition_id, instance_id, "unpin a comment")
        response = await audit_report.unpin_comment(
            get_settings().auth, definition_id, instance_id, comment_id)
        return {"success": True, "data": response, "error": None}

    # ── Sign-offs ────────────────────────────────────────────────────────────

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_report_sign_off(
            definition_id: str,
            instance_id: str
            ) -> dict:
        """Get this server's sign-off on a report instance.

        Sign-offs through this server are recorded under the API key.
        Returns {"sign_off": null} if it hasn't signed off.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
        """
        response = await audit_report.get_sign_off(
            get_settings().auth, definition_id, instance_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_report_sign_off(
            definition_id: str,
            instance_id: str,
            ) -> dict:
        """Approve a report instance and attest to it, as the console's Approve does.

        Only call this when the user says they approve the report and
        attest to its accuracy. The approval is recorded under the API
        key and adds a comment. When the sign-offs reach the instance's
        required_approvals, the report is finalized and takes no more
        comments. Refused when the instance needs no approvals, is
        finalized or is fully approved. The API also refuses (HTTP 409)
        unless the status is "generated", and a second sign-off by the
        same API key.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
        """
        await _open_instance(definition_id, instance_id, "sign off")
        body = {"action": "approve", "attestation": True, "comments": ""}
        response = await audit_report.create_sign_off(
            get_settings().auth, definition_id, instance_id, body)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_report_sign_offs(
            definition_id: str,
            instance_id: str,
            limit: int | None = None,
            cursor: str | None = None
            ) -> dict:
        """List all sign-offs on a report instance.

        Args:
            definition_id: ID of the report definition.
            instance_id: ID of the report instance.
            limit: Results per page, 1-100 (default 25).
            cursor: `next_cursor` from the previous page.
        """
        response = await audit_report.list_sign_offs(
            get_settings().auth, definition_id, instance_id, _page(limit, cursor))
        return {"success": True, "data": response, "error": None}
