# Audit Report Tools (17 tools)

Create, schedule, manage, and review structured audit report definitions and their generated instances. Covers the full lifecycle: defining what data to report on, triggering report generation, reviewing instances, adding comments, and recording sign-offs.

The tools follow the ALTR console's audit reports pages: they offer the console's choices, build the same requests, and refuse an action where the console blocks it.

## Tool Summary

| Tool | Description |
|------|-------------|
| `list_report_definitions` | List audit report definitions |
| `create_report_definition` | Create a definition, as the console's report builder does |
| `get_report_definition` | Get a single definition by ID |
| `update_report_definition` | Change some of a definition's settings and keep the rest |
| `archive_report_definition` | Archive a definition (the console's Delete) |
| `restore_report_definition` | Restore an archived definition |
| `trigger_report_definition` | Start generating a report now (the console's Run) |
| `list_report_instances` | List a definition's reports, newest first |
| `get_report_instance` | Get a single report instance |
| `get_report_instance_download_url` | Get a download URL for a report instance |
| `list_report_comments` | List comments on a report instance |
| `create_report_comment` | Add a comment to a report instance |
| `pin_report_comment` | Pin a comment on a report instance |
| `unpin_report_comment` | Unpin a comment on a report instance |
| `get_report_sign_off` | Get this server's sign-off on an instance |
| `create_report_sign_off` | Approve a report instance and attest to it |
| `list_report_sign_offs` | List all sign-offs on a report instance |

## Workflow

1. Create a definition with `create_report_definition`: the data source, its scope, field filters, schedule, recipients and required approvals.
2. Start a report now with `trigger_report_definition`. It returns the new `instance_id` while the report generates in the background. A definition can't run twice within 5 minutes, scheduled runs included.
3. Poll `get_report_instance` until its status is `generated` (or `failed`), and list a definition's reports with `list_report_instances`.
4. Download the report with `get_report_instance_download_url` (PDF or CSV). The link expires after 24 hours.
5. If the report needs approvals, add review comments with `create_report_comment`, and pin one comment per instance with `pin_report_comment`.
6. Record an approval with `create_report_sign_off`. When the sign-offs reach the instance's `required_approvals`, copied from the definition when the report was generated, the report is finalized and takes no more comments.

## What the tools refuse

The console blocks these, so the tools refuse them before calling the API:

- **Definitions:** a lookback other than 1, 3, 7, 14, 30, 60 or 90 days; more than 5 required approvals; no recipients or more than 20; a cron without 6 fields or without `?` in exactly one of day-of-month and day-of-week; an unknown timezone; a filter field, operator or value the console doesn't offer.
- **Scope:** an OLTP repository that can't be read, or a Snowflake database id that isn't a connected Snowflake database.
- **Updates and triggers** while one of the definition's reports is generating.
- **Filter changes** on a definition with more than one filter group. The console flattens such groups into one when it saves; the tools keep them as they are.
- **Comments, pins and sign-offs** on an instance that needs no approvals, is finalizing or finalized, or is fully approved.

## Sign-offs through this server

Every sign-off is recorded under the identity of the server's API key, and each identity counts once toward `required_approvals`. A definition needing more than 1 approval therefore also needs console users to sign off. Each sign-off also adds a comment to the instance.

## Cron Expression Reference

`schedule_cron` uses a **6-field** format: `minute hour day-of-month month day-of-week year`, evaluated in the definition's `timezone`.

- Put `?` in **exactly one** of `day-of-month` and `day-of-week`, even when neither is constrained (`0 9 * * ? *`, not `0 9 * * * *`)
- Use `*` for "every"
- A scheduled run can start up to 10 minutes after the cron time

| Natural language | Cron expression |
|-----------------|-----------------|
| Every day at 12:00 PM | `0 12 * * ? *` |
| Every day at 9:00 AM | `0 9 * * ? *` |
| Every Monday at 9:00 AM | `0 9 ? * MON *` |
| Every weekday (Mon–Fri) at 8:30 AM | `30 8 ? * MON-FRI *` |
| Every Sunday at 6:00 PM | `0 18 ? * SUN *` |
| First day of every month at midnight | `0 0 1 * ? *` |
| Every Tuesday and Thursday at 7 AM | `0 7 ? * TUE,THU *` |

**Day abbreviations:** `SUN MON TUE WED THU FRI SAT`  
**Month abbreviations:** `JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC`

## Paging

The list tools take `limit` (1–100, default 25) and `cursor`. Pass the previous page's `next_cursor` while `has_more` is true. The last page can be empty. Definitions come back in no particular order; instances come back newest first.

## Tool Details

### list_report_definitions

List audit report definitions, in no particular order.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Results per page, 1–100 (default 25) |
| `cursor` | str | no | `next_cursor` from the previous page |
| `archived` | bool | no | If true, return only archived definitions |

---

### create_report_definition

Create an audit report definition, as the console's report builder does. Each report is kept 90 days. Names don't have to be unique.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | str | yes | Display name, at most 200 bytes |
| `integration_type` | str | yes | `"oltp"` (sidecar repositories) or `"snowflake"` |
| `timezone` | str | yes | IANA timezone (e.g. `"America/New_York"`) for both the report window and the schedule |
| `schedule_cron` | str | yes | 6-field cron, evaluated in `timezone` (see the reference above) |
| `required_approvals` | int | yes | Sign-offs that finalize each report, 0–5. With 0, reports take no comments or sign-offs |
| `recipients` | list[str] | yes | 1–20 email addresses that receive each report, in the org's allowed email domains |
| `repo_names` | list[str] | no | OLTP only: the sidecar repositories the report covers. Omit to cover every repository |
| `database_ids` | list[int] | no | Snowflake only: ALTR ids of connected Snowflake databases (from `get_databases`). Omit to cover every connected database; the result then carries a `warning` |
| `filters` | list | no | Field filters, ANDed together (see below) |
| `description` | str | no | At most 1000 bytes |
| `lookback_days` | int | no | Complete days each report covers: 1, 3, 7, 14, 30, 60 or 90 (default 7) |
| `schedule_enabled` | bool | no | Default `true`; `false` saves the schedule paused |

The tool sets each repository's type itself, as the console does, from the repositories in `repo_names`.

**Filters.** Each filter is `{"field": ..., "operator": ..., "values": [...]}`, and matching ignores case.

| Operator | Meaning |
|----------|---------|
| `is` | The field equals one of the values |
| `is_not` | The field equals none of the values |
| `contains` | The field contains one of the values |
| `does_not_contain` | The field contains none of the values |

| Integration | Fields |
|-------------|--------|
| `oltp` | `consuming_user`, `statement_type`, `database_name`, `schema_name`, `table_name`, `column_name`, `event_source`, `event_name`, `repo_user`, `repo_host`, `application_name`, `client_host`, `connection_id`, `execution_success`, `statement_text` |
| `snowflake` | `username`, `query_type`, `event_source`, `event_name`, `current_role`, `client`, `ip_address`, `warehouse`, `warehouse_size`, `account_identifier`, `account_region`, `query_text` |

- `statement_type` values: `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `MERGE`, `GRANT`, `REVOKE`, `COPY`, `CALL`, `READ`, `ALTER_SESSION`, `USE`, `SHOW`, `DESCRIBE`, `EXPLAIN`, `DDL`, `DML`, `QUERY`.
- OLTP `event_name` values: `STATEMENT_EXECUTION`, `CONNECT_EXECUTION`, `SESSION_EXECUTION`.
- `execution_success` takes one filter, `is` or `is_not`, with `[true]` or `[false]`.
- `statement_text` and `query_text` values are at most 255 bytes, contain no backslash, and are not only `%` and `_`.
- Up to 50 values per filter and 50 filters.

```json
[
  {"field": "statement_type", "operator": "is", "values": ["DELETE", "UPDATE"]},
  {"field": "consuming_user", "operator": "does_not_contain", "values": ["svc_"]},
  {"field": "execution_success", "operator": "is", "values": [false]}
]
```

---

### get_report_definition

Get a single audit report definition by ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |

---

### update_report_definition

Change some of a definition's settings, as the console's edit form does. The tool reads the definition and changes only what you pass; everything else, including the retention period, is kept. The data source can't change. A changed `required_approvals` or `lookback_days` applies to reports generated afterwards. Updating an archived definition returns HTTP 409.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the definition to update |
| `name` | str | no | Display name, at most 200 bytes |
| `description` | str | no | At most 1000 bytes; `""` clears it |
| `timezone` | str | no | IANA timezone for both the report window and the schedule |
| `schedule_cron` | str | no | 6-field cron |
| `schedule_enabled` | bool | no | `false` pauses the schedule; `true` resumes it |
| `lookback_days` | int | no | 1, 3, 7, 14, 30, 60 or 90 |
| `required_approvals` | int | no | 0–5 |
| `recipients` | list[str] | no | Replaces the email recipients, 1–20 |
| `repo_names` | list[str] | no | OLTP only: replaces the repositories covered; `[]` covers every repository |
| `database_ids` | list[int] | no | Snowflake only: replaces the databases covered; `[]` covers every connected database |
| `filters` | list | no | Replaces the field filters; `[]` removes them |

Stored filters the tools can't express, such as `row_count` or a scope exclude, are kept when the field filters or the scope change, as in the console.

---

### archive_report_definition

Archive a definition (the console's Delete). This stops its schedule and hides it from listings; its reports stay until their retention ends. Archiving an archived definition returns HTTP 409.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the definition to archive |

---

### restore_report_definition

Restore an archived definition. This restarts its schedule if the schedule is enabled. The console has no restore. Restoring a definition that isn't archived returns HTTP 409.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the archived definition to restore |

---

### trigger_report_definition

Start generating a report now (the console's Run). Returns the new `instance_id` at once. Refused while another report of the definition is generating. A definition can't run within 5 minutes of its last run, scheduled runs included; the tool then returns HTTP 429 at once, without retrying. Triggering an archived definition returns HTTP 409.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the definition to trigger |

---

### list_report_instances

List a definition's reports, newest first.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `limit` | int | no | Results per page, 1–100 (default 25) |
| `cursor` | str | no | `next_cursor` from the previous page |

---

### get_report_instance

Get a single report instance by ID. `status` is `generating`, `generated`, `finalizing`, `finalized` or `failed`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |

---

### get_report_instance_download_url

Get a pre-signed download URL for a report, valid for 24 hours. Only a `generated` or `finalized` instance has one; any other status, `finalizing` included, returns HTTP 404.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |
| `format` | str | no | `"pdf"` (default) or `"csv"`, lowercase |

---

### list_report_comments

List comments on a report instance. The pinned comment comes first. Sign-offs appear as comments with a `sign_off_action`. An unknown instance returns an empty list.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |
| `limit` | int | no | Results per page, 1–100 (default 25) |
| `cursor` | str | no | `next_cursor` from the previous page |

---

### create_report_comment

Add a comment to a report instance. Refused when the instance needs no approvals, is finalizing or finalized, or is fully approved.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |
| `text` | str | yes | Comment text, at most 5000 bytes |

---

### pin_report_comment

Pin a comment on a report instance. Only one comment per instance can be pinned: pinning another while one is pinned returns HTTP 409, so unpin it first. Refused in the same instance states as `create_report_comment`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |
| `comment_id` | str | yes | ID of the comment to pin |

---

### unpin_report_comment

Unpin a comment on a report instance. Refused in the same instance states as `create_report_comment`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |
| `comment_id` | str | yes | ID of the comment to unpin |

---

### get_report_sign_off

Get this server's sign-off on a report instance (the API key's). Returns `{"sign_off": null}` if it hasn't signed off.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |

---

### create_report_sign_off

Approve a report instance and attest to it, as the console's Approve does. Call it only when the user says they approve the report and attest to its accuracy. The approval is recorded under the API key and adds a comment. Refused when the instance needs no approvals, is finalized or is fully approved. The API also refuses (HTTP 409) unless the status is `generated`, and a second sign-off by the same API key.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |

---

### list_report_sign_offs

List all sign-offs on a report instance. The console has no equivalent.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |
| `limit` | int | no | Results per page, 1–100 (default 25) |
| `cursor` | str | no | `next_cursor` from the previous page |
