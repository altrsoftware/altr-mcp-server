# Sidecar Configuration Tools (38 tools)

Configure ALTR sidecar infrastructure: agents, agent tasks, repos (databases, warehouses and file stores), repo users, service users, sidecars, listeners, and bindings. All tool names use the `sc_` prefix to distinguish them from other domains.

## Tool Summary

### Agents (5 tools)

| Tool | Description |
|------|-------------|
| `list_sc_agents` | List agents in your organization |
| `create_sc_agent` | Create a new agent |
| `get_sc_agent` | Get details for a specific agent |
| `update_sc_agent` | Update an existing agent |
| `disconnect_sc_agent` | Disconnect an agent from ALTR |

### Agent Tasks (5 tools)

| Tool | Description |
|------|-------------|
| `list_sc_agent_tasks` | List tasks assigned to an agent |
| `get_sc_agent_task` | Get one task with its configuration and schedule |
| `create_sc_agent_task` | Create a task for an agent |
| `update_sc_agent_task` | Update an agent task |
| `delete_sc_agent_task` | Delete an agent task |

### Repos (5 tools)

| Tool | Description |
|------|-------------|
| `list_sc_repos` | List repos |
| `create_sc_repo` | Create a new repo |
| `get_sc_repo` | Get details for a specific repo |
| `update_sc_repo` | Turn redaction of SQL comments in audits on or off |
| `disconnect_sc_repo` | Disconnect a repository from ALTR |

### Repo Users (5 tools)

| Tool | Description |
|------|-------------|
| `list_sc_repo_users` | List users for a repository |
| `create_sc_repo_user` | Create a repo user |
| `get_sc_repo_user` | Get details for a specific repo user |
| `update_sc_repo_user` | Change a repo user's credentials |
| `disconnect_sc_repo_user` | Disconnect a repo user from ALTR |

### Service Users (5 tools)

| Tool | Description |
|------|-------------|
| `list_sc_service_users` | List service users |
| `create_sc_service_user` | Create a service user |
| `get_sc_service_user` | Get details for a specific service user |
| `update_sc_service_user` | Update a service user |
| `disconnect_sc_service_user` | Disconnect a service user from ALTR |

### Sidecars (5 tools)

| Tool | Description |
|------|-------------|
| `list_sc_sidecars` | List sidecars in your organization |
| `create_sc_sidecar` | Create a new sidecar |
| `get_sc_sidecar` | Get details for a specific sidecar |
| `update_sc_sidecar` | Update a sidecar |
| `disconnect_sc_sidecar` | Disconnect a sidecar from ALTR |

### Listeners (3 tools)

| Tool | Description |
|------|-------------|
| `list_sc_sidecar_listeners` | List listener ports on a sidecar |
| `register_sc_sidecar_listener` | Register a listener port |
| `deregister_sc_sidecar_listener` | Remove a listener port |

### Bindings (5 tools)

| Tool | Description |
|------|-------------|
| `list_sc_sidecar_bindings` | List repo bindings for a sidecar |
| `list_sc_repo_bindings` | List sidecar bindings for a repo |
| `get_sc_sidecar_binding` | Get a specific binding |
| `create_sc_sidecar_binding` | Bind a repo to a sidecar listener |
| `disconnect_sc_sidecar_binding` | Remove a repo binding |

---

## Agents

### list_sc_agents

List ALTR agents (SIS or CLASSIFIER) in your organization.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max items (default 50, max 100) |
| `contiguous_id` | str | no | Pagination token from the previous page. A page can hold fewer items than `limit`, or none, and still return one: keep going until it is absent |
| `agent_type` | str | no | Filter by `"SIS"` or `"CLASSIFIER"` |
| `name_starts_with` | str | no | Case-insensitive name filter (max 64 chars). Matches the start of the name, or anywhere in it where the API has contains search on |

---

### create_sc_agent

Create a new ALTR agent. Give at least one public key.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_type` | str | yes | `"SIS"` or `"CLASSIFIER"` |
| `name` | str | yes | Agent name (max 64 chars) |
| `description` | str | no | Agent description (max 100 chars) |
| `public_key_1` | str | one of the two | First PEM public key for mTLS |
| `public_key_2` | str | one of the two | Second PEM public key, for key rotation |

---

### get_sc_agent

Get details for a specific agent.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | Agent UUID |

---

### update_sc_agent

Update an existing agent. Only provided fields are changed.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | Agent UUID |
| `name` | str | no | Updated name (max 64 chars) |
| `description` | str | no | Updated description (max 400 chars); `""` clears it |
| `public_key_1` | str | no | Updated first PEM public key; `""` removes it |
| `public_key_2` | str | no | Updated second PEM public key; `""` removes it |

---

### disconnect_sc_agent

Disconnect an agent from ALTR. Agent must have `task_count` of 0.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | Agent UUID |

---

## Agent Tasks

### list_sc_agent_tasks

List tasks assigned to an agent.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | Agent UUID |
| `limit` | int | no | Max items (default 50, max 100) |
| `contiguous_id` | str | no | Pagination token from the previous page. A page can hold fewer items than `limit`, or none, and still return one: keep going until it is absent |

---

### get_sc_agent_task

Get one task of an agent, with its configuration and schedule.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | Agent UUID |
| `task_id` | str | yes | Task UUID |

---

### create_sc_agent_task

Create a task for an agent. A task runs against a specific repo on a schedule. The configuration depends on the agent type and the repo type; the tool reads both.

**CLASSIFIER agent** configuration, as the console builds it. The tool sets `classification_type` 5, `sample_strategy` `ROWS` and every condition type (`ROW_DATA`, `METADATA`, `COLUMN_LOCATION`, `GDLP`, `CONTENT_TYPE`, `DATA_LENGTH`, `COLUMN_SIZE`, `AMAZON_COMPREHEND`, `ENTROPY`); a configuration that sets any of the three is refused.

| Field | Notes |
|-------|-------|
| `collection_name` | Required. Classifier collection name |
| `sample_type`, `sample_size` | Database repos: `ROWS` (the default, 1000 rows) or `PERCENT` (default 5, at most 100) |
| `requires_review` | Hold each job's report for human review (default false) |
| `scope` | Limit runs to one database, schema or table: `{"level": "TABLE", "database": "db", "schema": "s", "table": "t"}`. S3 and FILESYSTEM repos take `{"level": "PATH", "paths": ["dir/"]}`: at most 50 relative paths inside the repo's prefix or `root_path`. Names and paths are at most 255 chars, without `#`. Omit for the whole source. On MongoDB and Cassandra a `SCHEMA` or `TABLE` scope or exclusion repeats the database in `schema`. On PostgreSQL, Oracle, MongoDB and Cassandra a scope or exclusion database must be the service user's `resource`, unless that is `*` |
| `exclusions` | List of scopes to skip, at most 100 |
| `file_options` | S3 and FILESYSTEM only: `content_classification`, `full_file_scan`, `include_glob`, `exclude_glob`, `max_files`, `max_file_bytes` (at most 64 MiB); S3 also `scan_mode` (`CRAWL` or `GLUE`), `sniff_bytes`, `glue_crawler`, `glue_start_crawler` |
| `metadata_map` | S3 and FILESYSTEM only: `"hashed"` (the default), `"plaintext"` or `"none"`, or `{"default": ..., "by_format": {"csv": ...}}`. `by_format` keys: `base64`, `csv`, `docx`, `gif`, `gzip`, `html`, `jpeg`, `json`, `ms_office_legacy`, `parquet`, `pdf`, `plain_text`, `png`, `pptx`, `rtf`, `tiff`, `xlsx`, `xml`, `yaml`, `zip` |

Do NOT include SIS fields for classifier agents.

**SIS (audit) agent** configuration varies by repo type:

| Repo type | Fields |
|-----------|--------|
| Oracle | optional `service_name` |
| MSSQL | `audit_file_path` (required, absolute path) |
| Postgres | `audit_file_path` (required, absolute path), `audit_file_type` (`stderr`, `csv` or `json`). `log_line_prefix` is required with `stderr` and rejected otherwise |
| MySQL | either `table_name` or `audit_file_path` (absolute path) |
| Snowflake | `table_name` (required): `QUERY_HISTORY` or `LOGIN_HISTORY`, one task per view |
| Databricks | `table_name` (`QUERY_HISTORY` or `ACCESS_AUDIT`) and `workspace_id` (1–20 digits), both required |
| Any | optional `initial_audit_timestamp` (RFC 3339) and `ssl_config` (`enabled`, `trust_server_certificate`, `trust_store_path` (absolute), `trust_store_password_arn`, `hostname_in_certificate`) |

MongoDB, Cassandra, S3 and FILESYSTEM repos take no SIS tasks. Do NOT include classifier fields for SIS agents.

**Schedule** format: `value`, a 5-field cron expression (minute hour day-of-month month day-of-week); optional `timezone` (IANA name, default `"UTC"`) and `max_duration` (ISO 8601). `type` is always `"CRON"`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | Agent UUID |
| `name` | str | yes | Task name (max 64 chars) |
| `repo_name` | str | yes | Target repository name |
| `configuration` | dict or str | yes | Agent-type-specific config (see above), or JSON string |
| `schedule` | dict or str | yes | Schedule config, or JSON string |
| `description` | str | no | Task description (max 400 chars) |
| `service_user` | str | no | Service user the agent signs in as. SIS: required for Oracle, MSSQL, Snowflake, Databricks and MySQL with `table_name`; rejected for Postgres and MySQL with `audit_file_path`. CLASSIFIER: required except on FILESYSTEM repos |

---

### update_sc_agent_task

Update an agent task. Only provided fields change.

- **Schedule:** give only what changes. The API replaces a schedule whole, so the tool keeps the stored `timezone` and `max_duration` unless you replace them. Send `"max_duration": null` to remove it.
- **CLASSIFIER tasks:** configuration fields not sent are kept, and the merged result must pass the create rules. The tool sets `classification_type` 5, `sample_strategy` `ROWS` and every condition type, as the console does on every edit. `scope`, `exclusions`, `file_options` and `metadata_map` replace the stored value; send `null` (or `[]` for `exclusions`) to clear one.
- **SIS tasks:** `initial_audit_timestamp` cannot change. Every type takes `ssl_config`. Oracle also takes `service_name`; MSSQL `audit_file_path`; Postgres any of `audit_file_path`, `audit_file_type`, `log_line_prefix`; MySQL only the field it was created with; Snowflake `table_name`; Databricks `table_name` and `workspace_id`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | Agent UUID |
| `task_id` | str | yes | Task UUID |
| `name` | str | no | Updated task name (max 64 chars) |
| `description` | str | no | Updated description (max 400 chars) |
| `configuration` | dict or str | no | Updated config or JSON string |
| `schedule` | dict or str | no | Updated schedule or JSON string |

---

### delete_sc_agent_task

Delete an agent task. Atomically removes the task and decrements the agent's and service user's task counts.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | Agent UUID |
| `task_id` | str | yes | Task UUID |

---

## Repos

### list_sc_repos

List repos: the data sources sidecars and agents connect to.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max items (default 50, max 100) |
| `contiguous_id` | str | no | Pagination token from the previous page. A page can hold fewer items than `limit`, or none, and still return one: keep going until it is absent |
| `repo_type` | str | no | Filter by `"Oracle"`, `"MSSQL"`, `"MySQL"`, `"Postgres"`, `"MongoDB"`, `"Cassandra"`, `"Snowflake"`, `"Databricks"`, `"S3"` or `"FILESYSTEM"` |
| `name_starts_with` | str | no | Case-insensitive name filter (max 32 chars). Matches the start of the name, or anywhere in it where the API has contains search on |

---

### create_sc_repo

Create a repo: a database, warehouse or file store.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | str | yes | Repo name: lowercase letters, digits and underscores, max 32 chars |
| `repo_type` | str | yes | `"Oracle"`, `"MSSQL"`, `"MySQL"`, `"Postgres"`, `"MongoDB"`, `"Cassandra"`, `"Snowflake"`, `"Databricks"`, `"S3"` or `"FILESYSTEM"` |
| `hostname` | str | see note | Server hostname (max 500 chars). Required for every type but S3 and FILESYSTEM, which reject it. Snowflake: `<account>.snowflakecomputing.com`; Databricks: the workspace host |
| `port` | int | see note | Server port, 1–65535. Required and rejected like `hostname`. Snowflake and Databricks use 443 |
| `description` | str | no | Repository description (max 100 chars) |
| `connection_properties` | dict or str | no | String values, accepted only for the types below. As in the console, these tools don't change them after the repo is created |
| `audit_properties` | dict or str | no | The only key is `redact_comments`: `"*"` redacts SQL comments from audited query text; `""` (the default) keeps them |

| Repo type | `connection_properties` keys |
|-----------|------------------------------|
| S3 | `bucket` and `region` (required), `prefix`, `glue_database` |
| FILESYSTEM | `root_path` (required, absolute) |
| Databricks | `http_path` of the SQL warehouse (required, starts with `/`) |
| MongoDB | `auth_database`, `replica_set`, `srv` (`"true"` or `"false"`), `connection_options` (`k=v&k=v`, without tls, ssl, proxy, auth or replicaSet options) |
| Cassandra | `local_datacenter` |

---

### get_sc_repo

Get details for a specific repository.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |

---

### update_sc_repo

Turn redaction of SQL comments in audited query text on or off, the only repo setting the console edits. As in the console, hostname, port and connection properties aren't changed here.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `redact_comments` | bool | yes | `true` redacts SQL comments from audited query text; `false` keeps them |

---

### disconnect_sc_repo

Delete a repository from ALTR. The API refuses while it has repo users, service users or sidecar bindings.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |

---

## Repo Users

### list_sc_repo_users

List users configured for a repository.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `limit` | int | no | Max items (default 50, max 100) |
| `contiguous_id` | str | no | Pagination token from the previous page. A page can hold fewer items than `limit`, or none, and still return one: keep going until it is absent |

---

### create_sc_repo_user

Create a repo user with credential reference. Provide exactly one credential source.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `username` | str | yes | Database username: lowercase letters, digits and underscores, max 32 chars |
| `aws_secrets_manager` | dict or str | no | Dict with `secrets_path` and optional `iam_role`. S3 and FILESYSTEM repos also accept `iam_role` alone |
| `azure_key_vault` | dict or str | no | Dict with `key_vault_uri` and `secret_name` |
| `environment_variable` | dict or str | no | Dict with `variable_name`, the OS environment variable holding the secret |
| `secret_file` | dict or str | no | Dict with `path`, a file name (no directories) read from `/altr/secrets/` |

---

### get_sc_repo_user

Get details for a specific repo user.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `username` | str | yes | Database username |

---

### update_sc_repo_user

Change a repo user's credential reference. Provide exactly one credential source, shaped as in `create_sc_repo_user`. A new source type clears the old one. An `aws_secrets_manager` update changes only the keys sent, so a stored `iam_role` stays unless replaced.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `username` | str | yes | Database username |
| `aws_secrets_manager` | dict or str | no | AWS Secrets Manager config |
| `azure_key_vault` | dict or str | no | Azure Key Vault config |
| `environment_variable` | dict or str | no | Environment variable config |
| `secret_file` | dict or str | no | Secret file config |

---

### disconnect_sc_repo_user

Disconnect a repo user from ALTR.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `username` | str | yes | Database username to disconnect |

---

## Service Users

### list_sc_service_users

List service users. Optionally filter by repo. With `repo_name`, the API can also return service users of other repos whose names start with it; the tool drops those.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | no | If provided, list only service users for this repo |
| `limit` | int | no | Max items (default 50, max 100) |
| `contiguous_id` | str | no | Pagination token from the previous page. A page can hold fewer items than `limit`, or none, and still return one: keep going until it is absent |
| `username_starts_with` | str | no | Case-insensitive username filter (max 32 chars; only with `repo_name`). Matches the start of the name, or anywhere in it where the API has contains search on |

---

### create_sc_service_user

Create a service user: the account an agent signs in as. Provide exactly one credential source, shaped as in `create_sc_repo_user`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `username` | str | yes | Service user name: lowercase letters, digits and underscores, max 32 chars |
| `resource` | str | yes | The database the credential connects to: the Oracle service name; the MySQL, MSSQL, Postgres or Snowflake database; the Databricks catalog; the MongoDB database or Cassandra keyspace (`"*"` for all, classifier tasks only) |
| `aws_secrets_manager` | dict or str | no | AWS Secrets Manager config |
| `azure_key_vault` | dict or str | no | Azure Key Vault config |
| `environment_variable` | dict or str | no | Environment variable config |
| `secret_file` | dict or str | no | Secret file config |

---

### get_sc_service_user

Get details for a specific service user.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `username` | str | yes | Service user name |

---

### update_sc_service_user

Update a service user. Only provided fields are changed. Give at most one credential source. A new source type clears the old one. An `aws_secrets_manager` update changes only the keys sent, so a stored `iam_role` stays unless replaced.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `username` | str | yes | Service user name |
| `resource` | str | no | Updated resource (see `create_sc_service_user`) |
| `aws_secrets_manager` | dict or str | no | AWS Secrets Manager config |
| `azure_key_vault` | dict or str | no | Azure Key Vault config |
| `environment_variable` | dict or str | no | Environment variable config |
| `secret_file` | dict or str | no | Secret file config |

---

### disconnect_sc_service_user

Delete a service user from ALTR. The API refuses while any agent task uses it (`task_count` above 0).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `username` | str | yes | Service user name to disconnect |

---

## Sidecars

### list_sc_sidecars

List sidecars in your organization.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max items (default 50, max 100) |
| `contiguous_id` | str | no | Pagination token from the previous page. A page can hold fewer items than `limit`, or none, and still return one: keep going until it is absent |

---

### create_sc_sidecar

Create a new sidecar. Give at least one public key.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | str | yes | Sidecar name (max 64 chars) |
| `hostname` | str | yes | Sidecar hostname (max 500 chars), without a scheme or trailing `/` |
| `description` | str | no | Sidecar description (max 400 chars) |
| `public_key_1` | str | one of the two | First PEM public key for mTLS |
| `public_key_2` | str | one of the two | Second PEM public key, for key rotation |
| `unsupported_query_bypass` | bool | no | If true, unsupported queries bypass the query parser |
| `disable_platform_audits` | bool | no | If true, sidecar won't send activity audits |

---

### get_sc_sidecar

Get details for a specific sidecar.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sidecar_id` | str | yes | Sidecar UUID |

---

### update_sc_sidecar

Update a sidecar. Only provided fields are changed.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sidecar_id` | str | yes | Sidecar UUID |
| `name` | str | no | Updated name (max 64 chars) |
| `hostname` | str | no | Updated hostname (max 500 chars) |
| `description` | str | no | Updated description (max 400 chars) |
| `public_key_1` | str | no | Updated first PEM public key; `""` removes it |
| `public_key_2` | str | no | Updated second PEM public key; `""` removes it |
| `unsupported_query_bypass` | bool | no | Updated bypass setting |
| `disable_platform_audits` | bool | no | Updated audit setting |

---

### disconnect_sc_sidecar

Delete a sidecar from ALTR. The API refuses while it has listener ports.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sidecar_id` | str | yes | Sidecar UUID |

---

## Listeners

### list_sc_sidecar_listeners

List listener ports registered on a sidecar.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sidecar_id` | str | yes | Sidecar UUID |
| `limit` | int | no | Max items (default 50, max 100) |
| `contiguous_id` | str | no | Pagination token from the previous page. A page can hold fewer items than `limit`, or none, and still return one: keep going until it is absent |

---

### register_sc_sidecar_listener

Register a listener port on a sidecar.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sidecar_id` | str | yes | Sidecar UUID |
| `port` | int | yes | Port number to listen on, 1–65535 |
| `database_type` | str | yes | `"Oracle"`, `"MSSQL"`, `"MySQL"`, `"Postgres"`, `"MongoDB"` or `"Cassandra"` |
| `advertised_version` | str | yes | Database version string the sidecar advertises to clients (max 128 chars) |

---

### deregister_sc_sidecar_listener

Remove a listener port from a sidecar. The API refuses while repos are bound to the port.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sidecar_id` | str | yes | Sidecar UUID |
| `port` | int | yes | Port number to deregister |

---

## Bindings

### list_sc_sidecar_bindings

List repo bindings for a sidecar.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sidecar_id` | str | yes | Sidecar UUID |
| `ports` | str | no | Comma-separated port filter |
| `repo_names` | str | no | Comma-separated repo name filter |
| `limit` | int | no | Max items (default 50, max 100) |
| `contiguous_id` | str | no | Pagination token from the previous page. A page can hold fewer items than `limit`, or none, and still return one: keep going until it is absent |

---

### list_sc_repo_bindings

List sidecar bindings for a repository.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `ports` | str | no | Comma-separated port filter |
| `sidecar_ids` | str | no | Comma-separated sidecar ID filter |
| `limit` | int | no | Max items (default 50, max 100) |
| `contiguous_id` | str | no | Pagination token from the previous page. A page can hold fewer items than `limit`, or none, and still return one: keep going until it is absent |

---

### get_sc_sidecar_binding

Get a specific sidecar-repo binding.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sidecar_id` | str | yes | Sidecar UUID |
| `port` | int | yes | Listener port number |
| `repo_name` | str | yes | Repository name |

---

### create_sc_sidecar_binding

Bind a repository to a sidecar listener port. The port needs a listener (`register_sc_sidecar_listener`) whose database type matches the repo's type.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sidecar_id` | str | yes | Sidecar UUID |
| `port` | int | yes | Listener port number |
| `repo_name` | str | yes | Repository name to bind |

---

### disconnect_sc_sidecar_binding

Remove a repo binding from a sidecar listener port.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sidecar_id` | str | yes | Sidecar UUID |
| `port` | int | yes | Listener port number |
| `repo_name` | str | yes | Repository name to unbind |
