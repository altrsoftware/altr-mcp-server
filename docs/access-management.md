# Access Management Tools (4 tools)

Create and manage access management policies that control which roles can access which databases, schemas, or tables. Supports Snowflake and OLTP datasources.

## Tool Summary

| Tool | Description |
|------|-------------|
| `create_snowflake_access_policy` | Create an access policy for Snowflake |
| `update_snowflake_access_policy` | Update an existing Snowflake access policy |
| `create_oltp_access_policy` | Create an access policy for an OLTP datasource |
| `trigger_access_policy_check` | Trigger a manual compliance check |

## Tool Details

### create_snowflake_access_policy

Create an access management policy for a Snowflake datasource. Defines which roles can access which databases, schemas, or tables with read or write permissions. Policies are enforced by ALTR and checked on a schedule.

Each rule in the list must contain:
- **actors**: list of dicts with `type` (`"role"`), `condition` (`"equals"`, `"starts_with"`, `"ends_with"`), and `identifiers` (list of str)
- **objects**: list of dicts with `type` (`"database"`, `"schema"`, `"table"`), `condition` (`"equals"`, `"starts_with"`, `"ends_with"`, `"fully_qualified"`), and `identifiers` (list of str) or `fully_qualified_identifiers` (list of dicts with database/schema/table/view keys)
- **access**: list of dicts with `name` (`"read"` or `"write"`)

Optionally, rules may include:
- **tagged_objects**: list of dicts with `check_against` (list of `"databases"`, `"schemas"`, `"tables"`, `"views"`), `tagged_with` (list of dicts with database/schema/name/value keys), and `tag_condition` (`"or"` or `"and"`)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_name` | str | yes | Name for the policy (1-255 chars) |
| `description` | str | yes | Description of the policy (1-255 chars) |
| `connection_id` | int | yes | ALTR connection ID for the Snowflake database |
| `rules` | list[dict] or str | yes | List of access rule objects, or a JSON string |
| `policy_maintenance` | dict | no | Schedule with `rate` (`"day"` or `"cron"`) and `value` (number or cron string) |
| `access_request_id` | str | no | Access request ID this policy fulfills |

---

### update_snowflake_access_policy

Update an existing Snowflake access management policy. Replaces the policy's name, description, and rules.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_id` | str | yes | Raw policy ID. Do not URL-encode |
| `policy_name` | str | yes | Updated policy name (1-255 chars) |
| `rules` | list[dict] or str | yes | Updated list of access rule objects, or a JSON string |
| `description` | str | no | Updated description (1-255 chars) |

---

### create_oltp_access_policy

Create an access management policy for an OLTP datasource.

Each rule in the list must contain:
- **type**: `"read"`
- **actors**: list of dicts with `type` (`"idp_user"` or `"idp_group"`), `condition` (`"equals"`), and `identifiers` (list of str)
- **objects**: list of dicts with `type` (`"column"`) and `identifiers` (list of dicts with database/schema/table/column keys, each having `name` (str) and `wildcard` (bool))

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_name` | str | yes | Name for the policy (1-255 chars) |
| `description` | str | yes | Description of the policy (1-255 chars) |
| `repo_name` | str | yes | Repository/connection name |
| `database_type` | int | yes | Database type code (e.g. `4` for Oracle) |
| `database_type_name` | str | yes | Database type name (e.g. `"oracle"`) |
| `rules` | list[dict] or str | yes | List of OLTP access rule objects, or a JSON string |
| `case_sensitivity` | str | no | Case sensitivity setting. Default: `"case_sensitive"` |

---

### trigger_access_policy_check

Trigger a manual compliance check for an access management policy. Runs the policy check immediately instead of waiting for the next scheduled run.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_id` | str | yes | Raw policy ID. Do not URL-encode |
