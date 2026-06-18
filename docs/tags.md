# Tag Tools (8 tools)

Manage Snowflake tag connections in ALTR. Connect tags from Snowflake to ALTR, configure masking settings, and inspect tag values for use in policies.

> **Snowflake only.** Every tool on this page operates on Snowflake tags that have been connected to ALTR. **Databricks tags are not ALTR-managed objects** — they are referenced as raw strings at policy-creation time (`create_policy`) and have no `tag_group_id`, no `get_tags` listing, no `connect_tag` step, and no `update_tag` / `disconnect_tag` lifecycle. See [Policies & Rules](policies.md#create_policy) for the Databricks flow.

## Snowflake vs Databricks at a Glance

| Concept | Snowflake | Databricks |
|---|---|---|
| What is a tag in ALTR? | A first-class connected object (has `tag_group_id`, masking config, allowed values) | A raw string used only when creating the policy |
| Registration step | Required: call `connect_tag` first | None — skip `connect_tag` entirely |
| Listed by `get_tags`? | Yes (once connected) | No, never |
| Has `tag_group_id`? | Yes | No |
| Updated by `update_tag`? | Yes | N/A — change the policy/rules instead |
| Disconnected by `disconnect_tag*`? | Yes | N/A — remove the policy instead |
| Passed to `create_policy` as… | UPPERCASE name of the connected tag | Raw tag name string + `policy_type="PUSHDOWN"` + `database_ids=[…]` |

## Tool Summary

| Tool | Description |
|------|-------------|
| `get_tags` | List all tags connected to ALTR |
| `get_tag_values` | List allowed values for a specific tag |
| `get_tag_details_by_group_id` | Get full tag details by group ID |
| `get_tag_details` | Get full tag details by database, tag, and schema |
| `connect_tag` | Connect a Snowflake tag to ALTR |
| `update_tag` | Update a tag connection's masking configuration |
| `disconnect_tag` | Disconnect a tag from ALTR by group ID |
| `disconnect_tag_by_details` | Disconnect a tag from ALTR by database, schema, and tag name |

## Tool Details

### get_tags

List all tags connected to ALTR (available for use in policies). Only tags connected via `connect_tag` appear here. Tags created in Snowflake but not yet connected will not be listed.

**Parameters:** None

---

### get_tag_values

List all allowed values configured for a specific tag. These values are referenced when creating masking rules with `add_rules`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tag_name` | str | yes | Tag name (from `get_tags`) whose values you want to inspect |

---

### get_tag_details_by_group_id

Get full details for a specific tag masking by its group ID. Returns masking configuration, status, database info, and timestamps.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tag_group_id` | str | yes | Tag group identifier from `get_tags` |

---

### get_tag_details

Get full details for a specific tag masking by database, tag, and schema. Use when you know the exact database/schema/tag but not the `tag_group_id`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `database_id` | int | yes | Numeric ALTR database ID (from `get_database_id`) |
| `database_name` | str | yes | Database name in ALTR |
| `tag_name` | str | yes | Tag name |
| `schema_name` | str | yes | Schema name containing the tag |
| `protection_type` | str | no | Filter: `"governed"`, `"governed-pushdown"`, `"tokenized-vault"`, or `"encryption-fpe"` |

---

### connect_tag

Connect a Snowflake tag to ALTR so it can be used in masking policies. The tag must already exist in Snowflake. Once connected, it appears in `get_tags` and can be used with `create_policy`.

The tool automatically resolves the friendly name to the actual Snowflake database name for the API call.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `database_name` | str | yes | Friendly database name as shown in ALTR (`friendlyDatabaseName` from `get_databases`) |
| `schema_name` | str | yes | Exact schema name inside the target database |
| `tag_name` | str | yes | Tag to associate with this database/schema |

---

### update_tag

Update an existing tag connection's masking configuration. To connect a new tag, use `connect_tag` instead.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tag_group_id` | str | yes | Tag group identifier from `get_tags` |
| `database_id` | int | yes | Numeric ALTR database ID (from `get_database_id`) |
| `friendly_name` | str | yes | Display name for the tag in ALTR |
| `protection_type` | str | no | Masking type: `"governed"` (default), `"governed-pushdown"`, `"tokenized-vault"`, or `"encryption-fpe"` |
| `custom_role_provider_enabled` | bool | no | Enable custom role provider UDF. Default: `false` |
| `mask_data_type_list` | str or list[str] | no | List of data types to mask |
| `encryption_fpe_options` | dict | no | FPE config with `alphabet` (`"numeric"`, `"alphabetic"`, `"alphanumeric"`), `is_padded` (bool), `key_name` (str), `tweak_name` (str) |

---

### disconnect_tag

Disconnect a tag from ALTR. All policies on the tag must be removed first, or the disconnect will fail.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tag_group_id` | str | yes | Tag group identifier to disconnect |

---

### disconnect_tag_by_details

Disconnect a tag from ALTR by database, schema, and tag name. Alternative to `disconnect_tag` when you don't have the `tag_group_id`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `database_id` | int | yes | Numeric ALTR database ID |
| `database_name` | str | yes | Database name in ALTR |
| `schema_name` | str | yes | Schema name containing the tag |
| `tag_name` | str | yes | Tag name to disconnect |
| `ignore_errors` | bool | no | If true, force-forget the tag even if cleanup fails. Default: `false` |
