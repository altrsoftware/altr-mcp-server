# Sidecar Configuration Tools (37 tools)

Configure ALTR sidecar infrastructure: agents, agent tasks, database repositories, repo users, service users, sidecars, listeners, and bindings. All tool names use the `sc_` prefix to distinguish them from other domains.

## Tool Summary

### Agents (5 tools)

| Tool | Description |
|------|-------------|
| `list_sc_agents` | List agents in your organization |
| `create_sc_agent` | Create a new agent |
| `get_sc_agent` | Get details for a specific agent |
| `update_sc_agent` | Update an existing agent |
| `disconnect_sc_agent` | Disconnect an agent from ALTR |

### Agent Tasks (4 tools)

| Tool | Description |
|------|-------------|
| `list_sc_agent_tasks` | List tasks assigned to an agent |
| `create_sc_agent_task` | Create a task for an agent |
| `update_sc_agent_task` | Update an agent task |
| `delete_sc_agent_task` | Delete an agent task |

### Repos (5 tools)

| Tool | Description |
|------|-------------|
| `list_sc_repos` | List database repositories |
| `create_sc_repo` | Create a new repository |
| `get_sc_repo` | Get details for a specific repository |
| `update_sc_repo` | Update a repository's description |
| `disconnect_sc_repo` | Disconnect a repository from ALTR |

### Repo Users (5 tools)

| Tool | Description |
|------|-------------|
| `list_sc_repo_users` | List users for a repository |
| `create_sc_repo_user` | Create a repo user |
| `get_sc_repo_user` | Get details for a specific repo user |
| `update_sc_repo_user` | Update a repo user's credentials |
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
| `contiguous_id` | str | no | Pagination token |
| `agent_type` | str | no | Filter by `"SIS"` or `"CLASSIFIER"` |
| `name_starts_with` | str | no | Case-insensitive name prefix filter |

---

### create_sc_agent

Create a new ALTR agent.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_type` | str | yes | `"SIS"` or `"CLASSIFIER"` |
| `name` | str | yes | Agent name |
| `description` | str | no | Agent description |
| `public_key_1` | str | no | First public key for mTLS |
| `public_key_2` | str | no | Second public key for mTLS rotation |

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
| `name` | str | no | Updated name |
| `description` | str | no | Updated description |
| `public_key_1` | str | no | Updated first public key |
| `public_key_2` | str | no | Updated second public key |

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
| `contiguous_id` | str | no | Pagination token |

---

### create_sc_agent_task

Create a task for an agent. A task runs against a specific repo on a schedule.

**CLASSIFIER agent** configuration:
- `classification_type`: must be `5`
- `sample_strategy`: `"ROWS"` or `"PERCENT"`
- `collection_name`: classifier collection name

Do NOT include SIS fields for classifier agents.

**SIS (audit) agent** configuration varies by DB:
- **Oracle**: optional `initial_audit_timestamp`, `service_name`
- **MSSQL**: `audit_file_path` (required, absolute path)
- **PostgreSQL**: `audit_file_path`, `audit_file_type` (`log`/`csv`/`json`), optional `log_line_prefix`
- **MySQL**: either `table_name` or `audit_file_path`

Do NOT include classifier fields for SIS agents.

**Schedule** format: `type` (`"CRON"`), `value` (cron expression), optional `max_duration` (ISO 8601), optional `timezone` (e.g. `"America/New_York"`).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | Agent UUID |
| `name` | str | yes | Task name |
| `repo_name` | str | yes | Target repository name |
| `configuration` | dict or str | yes | Agent-type-specific config (see above), or JSON string |
| `schedule` | dict or str | yes | Schedule config, or JSON string |
| `description` | str | no | Task description |
| `service_user` | str | no | Service user for auth. Required for Oracle, MSSQL, MySQL (table_name mode). Forbidden for PostgreSQL and MySQL (audit_file_path mode) |

---

### update_sc_agent_task

Update an agent task. Only provided fields change.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | Agent UUID |
| `task_id` | str | yes | Task UUID |
| `name` | str | no | Updated task name |
| `description` | str | no | Updated description |
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

List database repositories configured for sidecar proxying.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max items (default 50, max 100) |
| `contiguous_id` | str | no | Pagination token |
| `repo_type` | str | no | Filter by `"Oracle"`, `"MSSQL"`, `"MySQL"`, or `"Postgres"` |

---

### create_sc_repo

Create a new database repository for sidecar proxying.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | str | yes | Repository name |
| `repo_type` | str | yes | Database type (e.g. `"Oracle"`, `"MSSQL"`, `"MySQL"`, `"Postgres"`) |
| `hostname` | str | yes | Database server hostname |
| `port` | int | yes | Database server port |
| `description` | str | no | Repository description |

---

### get_sc_repo

Get details for a specific repository.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |

---

### update_sc_repo

Update a repository's description.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `description` | str | yes | Updated description |

---

### disconnect_sc_repo

Disconnect a repository from ALTR. Must have no users or bindings.

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
| `contiguous_id` | str | no | Pagination token |

---

### create_sc_repo_user

Create a repo user with credential reference. Provide exactly one of `aws_secrets_manager` or `azure_key_vault`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `username` | str | yes | Database username |
| `aws_secrets_manager` | dict or str | no | Dict with `secrets_path` (required) and `iam_role` (optional) |
| `azure_key_vault` | dict or str | no | Dict with `key_vault_uri` and `secret_name` |

---

### get_sc_repo_user

Get details for a specific repo user.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `username` | str | yes | Database username |

---

### update_sc_repo_user

Update a repo user's credential reference.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `username` | str | yes | Database username |
| `aws_secrets_manager` | dict or str | no | Updated AWS Secrets Manager config |
| `azure_key_vault` | dict or str | no | Updated Azure Key Vault config |

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

List service users. Optionally filter by repo.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | no | If provided, list only service users for this repo |
| `limit` | int | no | Max items (default 50, max 100) |
| `contiguous_id` | str | no | Pagination token |
| `username_starts_with` | str | no | Filter by username prefix (only works with `repo_name`) |

---

### create_sc_service_user

Create a service user for a repository. Provide exactly one of `aws_secrets_manager` or `azure_key_vault`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `username` | str | yes | Service user name |
| `resource` | str | yes | Resource identifier |
| `aws_secrets_manager` | dict or str | no | Dict with `secrets_path` and optional `iam_role` |
| `azure_key_vault` | dict or str | no | Dict with `key_vault_uri` and `secret_name` |

---

### get_sc_service_user

Get details for a specific service user.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `username` | str | yes | Service user name |

---

### update_sc_service_user

Update a service user. Only provided fields are changed.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `username` | str | yes | Service user name |
| `resource` | str | no | Updated resource identifier |
| `aws_secrets_manager` | dict or str | no | Updated AWS config |
| `azure_key_vault` | dict or str | no | Updated Azure config |

---

### disconnect_sc_service_user

Disconnect a service user from ALTR.

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
| `contiguous_id` | str | no | Pagination token |

---

### create_sc_sidecar

Create a new sidecar.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | str | yes | Sidecar name (max 64 chars) |
| `hostname` | str | yes | Sidecar hostname (max 500 chars) |
| `description` | str | no | Sidecar description (max 400 chars) |
| `public_key_1` | str | no | First public key for mTLS |
| `public_key_2` | str | no | Second public key for mTLS rotation |
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
| `name` | str | no | Updated name |
| `hostname` | str | no | Updated hostname |
| `description` | str | no | Updated description |
| `public_key_1` | str | no | Updated first public key |
| `public_key_2` | str | no | Updated second public key |
| `unsupported_query_bypass` | bool | no | Updated bypass setting |
| `disable_platform_audits` | bool | no | Updated audit setting |

---

### disconnect_sc_sidecar

Disconnect a sidecar from ALTR. Must have no listeners.

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
| `contiguous_id` | str | no | Pagination token |

---

### register_sc_sidecar_listener

Register a listener port on a sidecar.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sidecar_id` | str | yes | Sidecar UUID |
| `port` | int | yes | Port number to listen on |
| `database_type` | str | yes | Database type for this listener |
| `advertised_version` | str | no | Version string to advertise |

---

### deregister_sc_sidecar_listener

Remove a listener port from a sidecar.

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
| `contiguous_id` | str | no | Pagination token |

---

### list_sc_repo_bindings

List sidecar bindings for a repository.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name |
| `ports` | str | no | Comma-separated port filter |
| `sidecar_ids` | str | no | Comma-separated sidecar ID filter |
| `limit` | int | no | Max items (default 50, max 100) |
| `contiguous_id` | str | no | Pagination token |

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

Bind a repository to a sidecar listener port.

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
