# Policy Tools (8 tools)

Create and manage data masking policies and rules in ALTR. Policies define how tagged data is masked for different roles.

## Masking Levels Reference

| Level | Name | Behavior |
|-------|------|----------|
| 10000 | No mask | Show raw value |
| 10001 | Full mask | Replace with `*` matching data length |
| 10002 | Email mask | Show domain only (e.g. `****@bank.com`) |
| 10003 | Show last four | e.g. `***-**-1234` |
| 10004 | Constant mask | `1` for numbers, `*` for strings, `1/1/2000` for dates |
| 10005 | Null | Replace with NULL |
| 10006 | Full mask hash | Replace with hashed value |
| 10007 | Email hash | Show domain, hash local part |
| 10008 | Show last four hash | Hash prefix, show last 4 |
| 10009 | Constant date | Replace with `12/31/9999` |

## Tool Summary

| Tool | Description |
|------|-------------|
| `get_policies` | List masking policies in your organization |
| `get_rules` | View masking rules for a specific policy |
| `get_roles` | List all ALTR roles (user groups) |
| `create_policy` | Create a masking policy for a tag |
| `add_rules` | Add masking rules to a policy |
| `update_rule` | Update an existing masking rule |
| `delete_rule` | Remove a specific rule from a policy |
| `delete_policy` | Delete a masking policy and all its rules |

## Tool Details

### get_policies

List masking policies configured in your ALTR organization. Returns each policy's tag, policy ID, and current rule count.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_type` | str | no | Filter by type: `TAG`, `COLUMN`, `PUSHDOWN`, `IMPERSONATION`, `GRANT`, `ROW`, `OLTP`. If omitted, queries all types and merges results |

---

### get_rules

View all masking rules configured for a specific policy. Shows which roles have what masking levels for which tag values.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_id` | str | yes | Raw policy ID from `get_policies`. Do not URL-encode |

---

### get_roles

List all ALTR roles (user groups) available in your organization. Role names are used in `add_rules` to define which user groups see what level of data masking.

**Parameters:** None

---

### create_policy

Create a masking policy for a specific tag. Creates an empty policy -- until you add rules with `add_rules`, all users will see NULL for tagged columns. Each tag can only have one policy.

**Snowflake vs Databricks tags are not the same thing.** A Snowflake tag is a first-class ALTR object that you register with `connect_tag` (it has a `tag_group_id`, appears in `get_tags`, and is editable with `update_tag`). A Databricks tag is **not** an ALTR object at all — it is a raw string you reference here when you create the policy. There is no `connect_tag` for Databricks, no entry in `get_tags`, and no `tag_group_id`.

Tag and parameter handling differ by platform:

**Snowflake**
- `tag` must be the UPPERCASE tag name returned by `get_tags`.
- The tag must already be connected to ALTR via `connect_tag`.
- Omit `database_ids` — the API will reject it for Snowflake.
- `policy_type` defaults to `"TAG"`; omit it.

**Databricks**
- `tag` is any raw tag name string (e.g. `"pac_access_level"`); case-insensitive, no `connect_tag` step.
- Databricks tags never appear in `get_tags` — do not look them up there.
- `policy_type` **must** be `"PUSHDOWN"`. The API rejects `"TAG"` for Databricks.
- `database_ids` **must** be passed as a list, even for a single database (e.g. `database_ids=[2167]`). The ID is the ALTR database ID for the target Databricks metastore from `get_databases`. Omitting `database_ids` will be rejected.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tag` | str | yes | Tag name. Snowflake: UPPERCASE connected tag from `get_tags`. Databricks: any raw tag name string |
| `policy_type` | str | conditional | Snowflake: omit (defaults to `"TAG"`). Databricks: **must** be `"PUSHDOWN"` |
| `database_ids` | list[int] | conditional | Snowflake: omit. Databricks: **required** — list of ALTR database IDs for the target metastore(s). Always a list, even for one database (e.g. `[2167]`) |

**Snowflake example:**

```python
create_policy(tag="STOPLIGHT")
```

**Databricks example:**

```python
create_policy(
    tag="pac_access_level",
    policy_type="PUSHDOWN",
    database_ids=[2167],
)
```

---

### add_rules

Add one or more masking rules to a policy in a single batch request. Accepts up to 99 rules per batch; larger lists are automatically split into multiple batches.

Each rule dict must contain:
- `masking_policy` (int): masking level 10000-10009
- `role` (str): target role name from `get_roles`
- `tag_value` (str): exact tag value (case-sensitive)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_id` | str | yes | Raw policy ID from `get_policies`. Do not URL-encode |
| `rules` | list[dict] or str | yes | List of rule dicts or a JSON string encoding such a list |

**Example rules value:**
```json
[
  {"masking_policy": 10001, "role": "ANALYST", "tag_value": "PII_SSN"},
  {"masking_policy": 10000, "role": "ADMIN", "tag_value": "PII_SSN"}
]
```

---

### update_rule

Update an existing masking rule's properties without deleting and recreating it. Only provided fields are changed.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_id` | str | yes | Raw policy ID from `get_policies`. Do not URL-encode |
| `rule_id` | str | yes | Raw rule ID from `get_rules`. Do not URL-encode |
| `masking_policy` | int | no | New masking level (10000-10009) |
| `role` | str | no | New role/user group name |
| `tag_value` | str | no | New tag value for the rule |
| `access_rate_thresholds` | list[dict] | no | Access rate threshold objects with `access_rate_unit` (str), `access_rate_limit` (int), and `action` (str) |
| `time_window_thresholds` | list[dict] | no | Time window threshold objects with `day` (list[str]), `start_time` (dict), `end_time` (dict), `timezone` (str), and `action` (str) |

---

### delete_rule

Remove a specific masking rule from a policy. Use `get_rules` first to identify the rule_id.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_id` | str | yes | Raw policy ID containing the rule. Do not URL-encode |
| `rule_id` | str | yes | Raw rule ID to delete. Do not URL-encode |

---

### delete_policy

Delete a masking policy and all its rules. Consider reviewing rules with `get_rules` first.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_id` | str | yes | Raw policy ID from `get_policies`. Do not URL-encode |
