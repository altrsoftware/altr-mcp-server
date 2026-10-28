# Audit Report Tools (17 tools)

Create, schedule, manage, and review structured audit report definitions and their generated instances. Covers the full lifecycle: defining what data to report on, triggering report generation, reviewing instances, adding comments, and recording sign-offs.

## Tool Summary

| Tool | Description |
|------|-------------|
| `list_report_definitions` | List audit report definitions |
| `create_report_definition` | Create a new audit report definition |
| `get_report_definition` | Get a single definition by ID |
| `update_report_definition` | Update an existing definition (full replacement) |
| `archive_report_definition` | Archive (soft-delete) a definition |
| `restore_report_definition` | Restore an archived definition |
| `trigger_report_definition` | Trigger an on-demand report |
| `list_report_instances` | List report instances for a definition |
| `get_report_instance` | Get a single report instance |
| `get_report_instance_download_url` | Get a download URL for a report instance |
| `list_report_comments` | List comments on a report instance |
| `create_report_comment` | Add a comment to a report instance |
| `pin_report_comment` | Pin a comment on a report instance |
| `unpin_report_comment` | Unpin the pinned comment on a report instance |
| `get_report_sign_off` | Get the current user's sign-off for an instance |
| `create_report_sign_off` | Sign off on a report instance |
| `list_report_sign_offs` | List all sign-offs for a report instance |

## Workflow

1. Create a definition with `create_report_definition` — set integration type, schedule, filters, and delivery.
2. Generate a report immediately with `trigger_report_definition` (rate-limited: 1 per definition per 5 minutes).
3. List generated instances with `list_report_instances` and retrieve details with `get_report_instance`.
4. Download the report file with `get_report_instance_download_url` (PDF or CSV).
5. Add review comments with `create_report_comment`. Pin one comment per instance with `pin_report_comment`.
6. Record approval with `create_report_sign_off`. View all approvals with `list_report_sign_offs`. When the instance's `required_approvals`, copied from the definition when it was generated, is above 0, the instance is finalized once that many users sign off.

## Cron Expression Reference

`schedule_cron` uses a **6-field** format: `minute hour day-of-month month day-of-week year`

- Use `?` in **either** `day-of-month` or `day-of-week` (not both) when the other is specified
- Use `*` for "every" in fields where day-of-month/day-of-week aren't constrained
- Times are evaluated in `schedule_timezone` (e.g. `"America/New_York"`; default `"UTC"`)

| Natural language | Cron expression |
|-----------------|-----------------|
| Every day at 12:00 PM | `0 12 * * ? *` |
| Every day at 9:00 AM | `0 9 * * ? *` |
| Every Monday at 9:00 AM | `0 9 ? * MON *` |
| Every weekday (Mon–Fri) at 8:30 AM | `30 8 ? * MON-FRI *` |
| Every Sunday at 6:00 PM | `0 18 ? * SUN *` |
| First day of every month at midnight | `0 0 1 * ? *` |
| Every hour | `0 * * * ? *` |
| Every 15 minutes | `0/15 * * * ? *` |
| Every Tuesday and Thursday at 7 AM | `0 7 ? * TUE,THU *` |

**Day abbreviations:** `SUN MON TUE WED THU FRI SAT`  
**Month abbreviations:** `JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC`

## Tool Details

### list_report_definitions

List audit report definitions. Returns paginated definitions ordered by creation time descending.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max results per page |
| `cursor` | str | no | Pagination cursor from a prior call |
| `archived` | bool | no | If True, return only archived definitions |

---

### create_report_definition

Create a new audit report definition.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | str | yes | Unique display name for the definition (max 200 chars) |
| `integration_type` | str | yes | Data source type: `"oltp"` or `"snowflake"` |
| `description` | str | no | Human-readable description (max 1000 chars) |
| `lookback_days` | int | no | Complete calendar days to include in each report window (excludes trigger day). 1–120; default 7 |
| `timezone` | str | no | IANA timezone for the report window (e.g. `"America/New_York"`). The API requires it |
| `schedule_cron` | str | no | Cron expression for scheduled delivery (e.g. `"0 9 ? * MON *"`). Required when any schedule field is set |
| `schedule_enabled` | bool | no | Whether the schedule is active |
| `schedule_timezone` | str | no | IANA timezone for schedule evaluation (default `"UTC"`) |
| `delivery` | str or dict | no | Delivery config. Shape: `{"channels": [{"type": "email", "enabled": true, "recipients": ["email@example.com"]}]}`. At most 20 recipients, in the org's allowed email domains |
| `filters` | str or dict | no | Filter groups. See filter schema below |
| `required_approvals` | int | no | Sign-offs that finalize each report. Default 0: sign-offs never finalize it |
| `retention_days` | int | no | Days to keep each report, 1–2555. Default 90 |

**Filter schema.** Groups are ORed; the filters in a group are ANDed. At most 20 groups and 50 filters per group.

| Integration | Fields |
|-------------|--------|
| `oltp` | `database_name`, `table_name`, `schema_name`, `column_name`, `statement_type`, `consuming_user`, `event_source`, `event_name`, `repo_user`, `repo_host`, `repo_name`, `repo_type`, `application_name`, `client_host`, `connection_id`, `statement_text`, `policy_blocked`†, `execution_success`†, `row_count`‡ |
| `snowflake` | `database_id`, `username`, `current_role`, `ip_address`, `client`, `query_type`, `warehouse`, `warehouse_size`, `account_identifier`, `account_region`, `event_source`, `event_name`, `query_text`, `row_count`‡ |

† boolean · ‡ numeric range · all others take patterns

```json
{
  "filter_groups": [
    {
      "filters": [
        {
          "field": "database_name",
          "mode": "include",
          "patterns": [{"match_type": "exact", "value": "mydb"}]
        }
      ]
    }
  ]
}
```

A pattern filter needs a `mode` (`include` or `exclude`) and a `patterns` array of 1–50 `{match_type, value}` entries.

- Match types: `exact`, `contains`, `starts_with`, `ends_with`. The default is `exact`, or `contains` for `statement_text` and `query_text`.
- `statement_type` values: `SELECT`, `READ`, `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `ALTER_SESSION`, `DROP`, `GRANT`, `REVOKE`, `MERGE`, `TRUNCATE`, `COPY`, `USE`, `SHOW`, `DESCRIBE`, `EXPLAIN`, `CALL`, `DDL`, `DML`, `QUERY`.
- `statement_text` and `query_text` patterns are at most 255 bytes, contain no backslash, and are not only `%` and `_` wildcards.

A boolean field takes `value` instead of `patterns`; `row_count` takes `range` with `min`, `max`, or both:

```json
{"field": "policy_blocked", "value": true}
{"field": "row_count", "range": {"min": 1000}}
```

---

### get_report_definition

Get a single audit report definition by ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |

---

### update_report_definition

Update an existing definition (full replacement). All fields that should be preserved must be included. `timezone` is always required; the API rejects an update without it. Any other omitted field is cleared or reset: `description` is emptied, the schedule and delivery are removed, `filters` are removed so the report covers every event, `lookback_days` returns to 7, `required_approvals` to 0 and `retention_days` to 90. Read the definition first with `get_report_definition`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the definition to update |
| `name` | str | yes | Unique display name |
| `integration_type` | str | yes | Data source type: `"oltp"` or `"snowflake"` |
| `description` | str | no | Human-readable description |
| `lookback_days` | int | no | Complete calendar days per report window |
| `timezone` | str | no | IANA timezone for the report window (e.g. `"America/New_York"`). The API requires it |
| `schedule_cron` | str | no | Cron expression for scheduled delivery |
| `schedule_enabled` | bool | no | Whether the schedule is active |
| `schedule_timezone` | str | no | IANA timezone for schedule evaluation |
| `delivery` | str or dict | no | Delivery config (see `create_report_definition`) |
| `filters` | str or dict | no | Filter groups (see `create_report_definition`) |
| `required_approvals` | int | no | Sign-offs that finalize each report (default 0) |
| `retention_days` | int | no | Days to keep each report, 1–2555 (default 90) |

---

### archive_report_definition

Archive (soft-delete) a definition. Archived definitions are hidden from normal listings but can be restored.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the definition to archive |

---

### restore_report_definition

Restore an archived audit report definition.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the archived definition to restore |

---

### trigger_report_definition

Trigger an on-demand report for a definition. Rate-limited to one trigger per definition per 5 minutes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the definition to trigger |

---

### list_report_instances

List report instances for a definition. Instances are returned newest-first.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `limit` | int | no | Max results per page |
| `cursor` | str | no | Pagination cursor from a prior call |

---

### get_report_instance

Get a single report instance by ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |

---

### get_report_instance_download_url

Get a pre-signed download URL for a report instance file. Only instances with status `generated` or `finalized` have one.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |
| `format` | str | no | File format: `"pdf"` (default) or `"csv"` |

---

### list_report_comments

List comments on a report instance. Pinned comments appear first, followed by the rest in chronological order.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |
| `limit` | int | no | Max results per page |
| `cursor` | str | no | Pagination cursor from a prior call |

---

### create_report_comment

Add a comment to a report instance.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |
| `text` | str | yes | Comment text (max 5000 chars) |

---

### pin_report_comment

Pin a comment on a report instance. Only one comment per instance can be pinned at a time; unpin the current one first.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |
| `comment_id` | str | yes | ID of the comment to pin |

---

### unpin_report_comment

Unpin the currently pinned comment on a report instance.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |
| `comment_id` | str | yes | ID of the comment to unpin |

---

### get_report_sign_off

Get the current user's sign-off for a report instance. Returns null/empty if not yet signed off.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |

---

### create_report_sign_off

Sign off on a report instance. Each user signs off once, and only while the instance status is `generated`. Each instance copies `required_approvals` from its definition when generated. If that value is above 0, the instance is finalized when its sign-offs reach it.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |
| `action` | str | no | Sign-off action. Values: `"approve"` (default) |
| `attestation` | bool | no | Attest to accuracy of the report (default `true`) |
| `comments` | str | no | Optional comments to include with the sign-off |

---

### list_report_sign_offs

List all sign-offs for a report instance across all users.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `definition_id` | str | yes | ID of the report definition |
| `instance_id` | str | yes | ID of the report instance |
| `limit` | int | no | Max results per page |
| `cursor` | str | no | Pagination cursor from a prior call |
