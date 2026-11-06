# Access Management Tools (5 tools)

Create and manage access management policies: which Snowflake roles can read or write which objects, and which ALTR users or IdP groups can create, read, update or delete which objects in a database repository. The tools build policies the way the console's Access Management Policy editor does, so every policy they create stays editable in the console.

## Tool Summary

| Tool | Description |
|------|-------------|
| `create_snowflake_access_policy` | Grant Snowflake roles access to named or tagged objects |
| `update_snowflake_access_policy` | Change a Snowflake policy's name, rule or refresh schedule |
| `create_oltp_access_policy` | Control access to a database repository through the sidecar |
| `update_oltp_access_policy` | Change a database repository policy's name or rules |
| `trigger_access_policy_check` | Re-apply a Snowflake policy's grants now |

## Tool Details

### create_snowflake_access_policy

Grant one set of Snowflake roles read and/or write access, as the console does. A policy has one rule, and the rule targets objects either by name or by tag. ALTR applies the grants asynchronously and re-applies them on the refresh schedule.

- **By name:** `object_type` `database` with database names; `schema` with `database` and schema names; `table` or `view` with `database`, `schema` and table or view names.
- **By tag:** objects of kind `tag_check_against` carrying any of `tag_names` (the tag lives in `tag_database`.`tag_schema`), or carrying one tag name with any of `tag_values`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_name` | str | yes | Name for the policy (1-255 chars) |
| `connection_id` | int | yes | Snowflake connection ID (from `get_databases`) |
| `roles` | str or list[str] | yes | Snowflake roles that get access |
| `refresh` | str | yes | How often ALTR re-applies the grants: `none`, `daily`, `weekly` or `monthly` |
| `access` | str | no | `read` (default), `write` or `read_write` |
| `object_type` | str | no | `database`, `schema`, `table` or `view` |
| `names` | str or list[str] | no | Names of the objects of `object_type` |
| `database` | str | no | Database holding the schemas, tables or views |
| `schema` | str | no | Schema holding the tables or views |
| `tag_check_against` | str | no | `database`, `schema`, `table` or `view` |
| `tag_database` | str | no | Database the tag is defined in |
| `tag_schema` | str | no | Schema the tag is defined in |
| `tag_names` | str or list[str] | no | Tag names; with `tag_values`, exactly one |
| `tag_values` | str or list[str] | no | Tag values to match on the one tag name |
| `refresh_time` | str | no | `HH:MM` in UTC; needed unless `refresh` is `none` |
| `refresh_day` | str | no | Day for a weekly or monthly refresh, `MON` to `SUN` |
| `refresh_week` | int | no | Week of the month for a monthly refresh, 1 to 4 |

The console builds the same rule shape: one role list matched exactly, fully qualified object names, and tag matches combined with OR. The API accepts more, such as several rules or name patterns, but the console shows such a policy's rules as read-only, so these tools don't create them.

---

### update_snowflake_access_policy

Change a Snowflake access management policy, as the console's editor does. Anything left out keeps its current value: the name, the rule and the refresh schedule. Saving re-applies the grants, so there's no need to call `trigger_access_policy_check` afterwards.

To change the rule, pass all of it: `roles`, `access` and a target, as for `create_snowflake_access_policy`. A policy whose rule the console can't edit keeps that rule; only its name and schedule can change. A policy still applying a previous change can't be updated until it finishes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_id` | str | yes | Policy ID, starting `GRANT#`. Do not URL-encode |
| `policy_name` | str | no | New name (1-255 chars) |
| `roles`, `access`, `object_type`, `names`, `database`, `schema`, `tag_check_against`, `tag_database`, `tag_schema`, `tag_names`, `tag_values` | | no | A new rule, as for `create_snowflake_access_policy` |
| `refresh` | str | no | `none` to remove the schedule, or `daily`, `weekly` or `monthly` to replace it |
| `refresh_time`, `refresh_day`, `refresh_week` | | no | As for `create_snowflake_access_policy` |

---

### create_oltp_access_policy

Control which ALTR users or IdP groups may create, read, update or delete which objects in a database repository, through the sidecar, as the console does. Supports Oracle, MSSQL, Postgres, MySQL, MongoDB and Cassandra repositories. The tool reads the repository's type to fill in the database type.

Each rule grants one kind of access to one set of users or groups on objects of one type:
- **access:** `create`, `read` (default), `update` or `delete`
- **users** (ALTR usernames, which are emails) or **groups** (IdP group names), as a list
- **object_type:** one level of the repository's hierarchy:

  | Repository | Levels |
  |---|---|
  | Oracle, MSSQL, Postgres | database, schema, table, column |
  | MySQL | database, table, column |
  | MongoDB | database, collection, field |
  | Cassandra | keyspace, table, column |

- One key per level above `object_type`, each a name or `"*"` for any, and the `object_type` key itself: a list of names, or `"*"` for any.

```json
{"access": "read", "users": ["ana@example.com"], "object_type": "column",
 "database": "sales", "schema": "*", "table": "orders", "column": ["email", "phone"]}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_name` | str | yes | Name for the policy (1-255 chars) |
| `repo_name` | str | yes | Repository name (from `list_sc_repos`) |
| `rules` | list[dict] or str | yes | List of rules as above, or a JSON string |

---

### update_oltp_access_policy

Change a database repository's access management policy, as the console's editor does. Anything left out keeps its current value. The repository can't change.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_id` | str | yes | Policy ID, starting `OLTP#`. Do not URL-encode |
| `policy_name` | str | no | New name (1-255 chars) |
| `rules` | list[dict] or str | no | The complete new list of rules, as for `create_oltp_access_policy`. Replaces every rule |

---

### trigger_access_policy_check

Re-apply a Snowflake access management policy's grants now, as the console's Refresh button does, instead of waiting for its schedule. The run is queued, and the policy shows as pending until it finishes. Database repository policies don't need it.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `policy_id` | str | yes | Policy ID, starting `GRANT#`. Do not URL-encode |
