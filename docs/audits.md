# Audit Tools (6 tools)

Search and retrieve audit logs from ALTR. Covers three audit types: sidecar query audits, Snowflake query audits (tag/column masking), and platform system audits.

## Tool Summary

| Tool | Description |
|------|-------------|
| `search_audits` | Search sidecar query audits |
| `get_audit_results` | Get results from a sidecar audit search |
| `search_query_audits` | Search Snowflake query audits |
| `get_query_audit_results` | Get results from a query audit search |
| `search_system_audits` | Search platform system audits |
| `get_system_audit_results` | Get results from a system audit query |

## Audit Search Workflow

All audit searches are asynchronous:
1. Call a `search_*` tool to start the search -- returns a token or UUID
2. Call the corresponding `get_*_results` tool to retrieve results
3. If the response is 202, the search is still processing -- retry after a short wait

## Tool Details

### search_audits

Search sidecar query audits with filters. Triggers an async search and returns a `search_uuid` (valid 30 days). All filters are combined with AND logic.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max results (default 10000, max 100000) |
| `offset` | int | no | Skip this many results |
| `from_date_time` | str | no | RFC3339 UTC start time (e.g. `"2025-01-01T00:00:00Z"`) |
| `to_date_time` | str | no | RFC3339 UTC end time |
| `consuming_user` | str or list[str] | no | Filter by consuming usernames (case-insensitive) |
| `consuming_user_email` | str or list[str] | no | Filter by consuming user emails |
| `query_id` | str or list[str] | no | Filter by specific query IDs |
| `sidecar_id` | str or list[str] | no | Filter by sidecar IDs |
| `sidecar_instance_id` | str or list[str] | no | Filter by sidecar instance IDs |
| `table_name` | str or list[str] | no | Filter by table names |
| `schema_name` | str or list[str] | no | Filter by schema names |
| `database_name` | str or list[str] | no | Filter by database names |
| `column_name` | str or list[str] | no | Filter by column names |
| `statement_type` | str or list[str] | no | Filter by statement types |
| `statement_text_contains` | str | no | Case-insensitive substring match on SQL text |
| `order_by` | str | no | `"asc"` or `"desc"` (default `"desc"`) |
| `sort_by` | str | no | `"event_time"` or `"rows_accessed"` (default `"event_time"`) |

---

### get_audit_results

Get results from a previously triggered sidecar audit search. A 202 response means the search is still processing.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `search_uuid` | str | yes | UUID returned by `search_audits` |
| `limit` | int | no | Max results per page (default 250, max 250) |
| `next_page_token` | str | no | Pagination token from a prior call |

---

### search_query_audits

Search Snowflake query audits (tag and column masking). Triggers an async search and returns a `search_uuid` (valid 30 days). Use this for Snowflake tag-based or column-based masking audits. For sidecar proxy audits, use `search_audits` instead.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max results (default 10000, max 100000) |
| `offset` | int | no | Skip this many results |
| `from_date_time` | str | no | RFC3339 UTC start time |
| `to_date_time` | str | no | RFC3339 UTC end time |
| `executing_role` | str | no | Filter by executing role (case-insensitive) |
| `executing_user` | str | no | Filter by executing user (case-insensitive) |
| `query_id` | str | no | Filter by query identifier (case-insensitive) |
| `policy_tag_name` | str | no | Filter by policy tag name (case-insensitive) |
| `policy_tag_value` | str | no | Filter by policy tag value (case-insensitive) |
| `policy_column_database_name` | str | no | Filter by database name (case-insensitive) |
| `policy_column_schema_name` | str | no | Filter by schema name (case-insensitive) |
| `policy_column_table_name` | str | no | Filter by table name (case-insensitive) |
| `policy_column_name` | str | no | Filter by column name (case-insensitive) |
| `order_by` | str | no | `"asc"` or `"desc"` (default `"desc"`) |
| `sort_by` | str | no | `"event_time"` or `"rows_accessed"` (default `"event_time"`) |

---

### get_query_audit_results

Get results from a previously triggered query audit search. A 202 response means the search is still processing. For sidecar audit results, use `get_audit_results` instead.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `search_uuid` | str | yes | UUID returned by `search_query_audits` |
| `limit` | int | no | Max results per page (default 250, max 250) |
| `next_page_token` | str | no | Pagination token from a prior call |

---

### search_system_audits

Search ALTR platform system audits. Starts an async query against system audit logs. If `wait` is set, the API may return results directly (200) or a token for later retrieval (202). The time range may be at most one week.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `category` | str | yes | Audit category: `"API Keys"`, `"Locks"`, `"Data"`, `"Administrators"`, `"Thresholds"`, `"Anomalies"`, `"Applications"`, `"User Groups"`, `"Data Sources"`, `"Row Access Policy"`, `"Unified Access Policy"`, `"Access Requests"`, `"Access Management Policy"`, `"Impersonation Policy"` |
| `limit` | int | no | Max results (1-100, default 50) |
| `offset` | int | no | Results to skip (default 0) |
| `wait` | int | no | Milliseconds to wait for results (-1 to 1000, default 100). Set to -1 to return immediately with token |
| `from_date_time` | str | no | ISO 8601 UTC start time. Defaults to 48h ago |
| `to_date_time` | str | no | ISO 8601 UTC end time. Defaults to now |

---

### get_system_audit_results

Get results from a system audit query. If the response has `moreData: true`, use the new token to fetch the next page.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | str | yes | Token from `search_system_audits` or a prior call's response |
