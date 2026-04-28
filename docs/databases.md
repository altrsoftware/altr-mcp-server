# Database Tools (7 tools)

Manage Snowflake database connections in ALTR. Connect new data sources, update connection properties, check status, and remove databases.

## Tool Summary

| Tool | Description |
|------|-------------|
| `get_databases` | List all Snowflake databases connected to ALTR |
| `get_database_id` | Get the numeric ALTR database ID for a database name |
| `get_service_users` | List Snowflake service users available for connections |
| `create_database` | Connect a new data source to ALTR |
| `update_database` | Update a database connection's properties |
| `trigger_database_status_sync` | Trigger a database status sync |
| `delete_database` | Disconnect and remove a database from ALTR |

## Tool Details

### get_databases

Discover which Snowflake databases are connected to ALTR. Returns connection metadata including database names and IDs. Use `get_database_id` to get the numeric ID required for classification jobs.

**Parameters:** None

---

### get_database_id

Get the ALTR database ID for a database name. Required before creating classification jobs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `database_name` | str | yes | Friendly database name as shown in the ALTR UI |

---

### get_service_users

List Snowflake service users available for database connections. Returns service user IDs needed for `create_database` when using keypair authentication (recommended for Snowflake).

**Parameters:** None

---

### create_database

Connect a new data source to the ALTR platform. Supports two authentication modes:

1. **Service user (keypair auth -- recommended for Snowflake):** Provide `service_user_id` from `get_service_users`. No password, hostname, or port needed.
2. **Password auth:** Provide `database_username`, `database_password`, `hostname`, and `database_port`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `friendly_database_name` | str | yes | Display name for the database in ALTR |
| `database_type` | str | yes | Database type (e.g. `"snowflake_external_functions"`) |
| `database_name` | str | yes | Actual database name (e.g. `"MY_DATABASE_NAME"`) |
| `service_user_id` | str | no | Service user ID from `get_service_users` for keypair auth |
| `database_username` | str | no | Username (password auth only) |
| `database_password` | str | no | Password (password auth only) |
| `hostname` | str | no | Database server hostname (password auth only) |
| `database_port` | int | no | Database server port (password auth only) |

---

### update_database

Update a database connection's properties. Only the fields you provide will be updated; omitted fields remain unchanged.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `database_id` | int | yes | Numeric ALTR database ID (from `get_databases`) |
| `friendly_database_name` | str | no | Updated display name |
| `max_number_of_connections` | int | no | Max concurrent connections |
| `max_number_of_batches` | int | no | Max concurrent batches |
| `service_user_id` | str | no | Service user identifier |
| `connection_string` | str | no | Database connection string |
| `database_password` | str | no | Updated password |
| `database_username` | str | no | Updated username |
| `snowflake_role` | str | no | Snowflake role to use |
| `warehouse_name` | str | no | Snowflake warehouse to use |
| `should_classify` | bool | no | Enable/disable classification |
| `data_usage_history` | bool | no | Enable/disable data usage history |
| `classification_type` | str | no | Classification type code |
| `reinvoke` | bool | no | Trigger reinvocation of database setup |

---

### trigger_database_status_sync

Trigger a database status sync. Sets the database to "in progress" until the status check completes. Use `get_databases` afterward to see the updated status.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `database_id` | int | yes | Numeric ALTR database ID (from `get_databases`) |

---

### delete_database

Disconnect and remove a database from ALTR. Permanently removes the ALTR connection -- does not affect the actual database.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `database_id` | int | yes | Numeric ALTR database ID (from `get_databases`) |
| `ignore_errors` | bool | no | If true, force removal even if cleanup fails. Default: `false` |
