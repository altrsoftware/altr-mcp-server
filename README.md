# ALTR MCP Server

[![PyPI](https://img.shields.io/pypi/v/altr-mcp.svg)](https://pypi.org/project/altr-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/altr-mcp)](https://pypi.org/project/altr-mcp/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE.md)
[![CI](https://github.com/altrsoftware/altr-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/altrsoftware/altr-mcp-server/actions/workflows/ci.yml)
[![Security](https://github.com/altrsoftware/altr-mcp-server/actions/workflows/security.yml/badge.svg)](https://github.com/altrsoftware/altr-mcp-server/actions/workflows/security.yml)

[ALTR](https://www.altr.com) provides tag-based data masking, access governance, and classification for Snowflake, Databricks, and OLTP databases. This MCP server enables AI assistants (Claude, Cursor, and other MCP clients) to manage data security on the ALTR platform — 99 tools across 10 domains covering database connections, tag masking, policies, classification, access management, audits, telemetry, and sidecar configuration.

All tools return structured `{success, data, error}` responses and can run over stdio, SSE, or streamable-http transports.

## Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Getting Credentials](#getting-credentials)
- [Configuration](#configuration)
  - [Restricting Tools](#restricting-tools)
- [Setup](#setup)
  - [Claude Desktop](#claude-desktop)
  - [Claude Code (CLI)](#claude-code-cli)
  - [Cursor](#cursor)
  - [VS Code (GitHub Copilot)](#vs-code-github-copilot)
  - [Windsurf](#windsurf)
  - [Running from Local Source](#running-from-local-source)
- [CLI](#cli)
- [Tools](#tools)
  - [Databases](#databases-8-tools)
  - [Roles](#roles-1-tool)
  - [Tags](#tags-8-tools)
  - [Policies & Rules](#policies--rules-7-tools)
  - [Classification](#classification-13-tools)
  - [Access Management](#access-management-4-tools)
  - [Access Requests](#access-requests-6-tools)
  - [Audits](#audits-6-tools)
  - [Telemetry](#telemetry-9-tools)
  - [Sidecar Configuration](#sidecar-configuration-37-tools)
- [Data Source Support](#data-source-support)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [License](#license)

## Quick Start

Once installed, verify your setup by asking your AI assistant to run a few read-only tools:

1. `get_databases` — list your connected databases
2. `get_tags` — list tags connected to ALTR
3. `get_roles` — list ALTR roles (user groups)
4. `get_policies` — list existing masking policies

If these return data, your credentials are working and you're ready to go.

## Installation

Install from PyPI:

```bash
pip install altr-mcp
```

Or run directly with [uvx](https://docs.astral.sh/uv/guides/tools/) (no install required):

```bash
uvx altr-mcp
```

> `uvx` is part of the [uv](https://docs.astral.sh/uv/) Python package manager. Install it with `pip install uv` or see the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

## Getting Credentials

You need three values from the ALTR platform to configure this server:

| Credential | Where to find it |
|---|---|
| `ORG_ID` | In the ALTR console: **Settings > Preferences > Organization** — copy the value from "ALTR Organization ID" |
| `MAPI_KEY` | In the ALTR console: **Settings > Preferences > API > Add New** — give it a description, then copy the key |
| `MAPI_SECRET` | Shown once when you create the API key above — copy and store it securely |

## Configuration

Set the following environment variables before starting the server:

| Variable | Required | Description |
|---|---|---|
| `ORG_ID` | Yes | ALTR organization ID |
| `MAPI_KEY` | Yes | ALTR management API key |
| `MAPI_SECRET` | Yes | ALTR management API secret |
| `MCP_TRANSPORT` | No | Transport protocol: `stdio` (default), `sse`, or `streamable-http` |
| `MCP_HOST` | No | Bind address for HTTP transports (default: `0.0.0.0`) |
| `MCP_PORT` | No | Port for HTTP transports (default: `8000`) |
| `RESTRICTED_TOOLS` | No | Comma-separated tool names to hide from clients |
| `LOG_FORMAT` | No | Log output format: `console` (default) or `json` |
| `LOG_LEVEL` | No | Log level (default: `INFO`) |

**URL overrides** (optional, default to ALTR production):

| Variable | Default |
|---|---|
| `ALTR_API_BASE_URL` | `https://api.live.altr.com` |
| `ALTR_ALTRNET_BASE_URL` | `https://altrnet.live.altr.com` |
| `ALTR_CLASSIFICATION_BASE_URL` | `https://{ORG_ID}.classification.live.altr.com` |
| `ALTR_SC_CONTROL_BASE_URL` | `https://{ORG_ID}.sc-control.live.altr.com` |
| `ALTR_SERVICE_USER_BASE_URL` | `https://{ORG_ID}.service-user.live.altr.com` |

### Restricting Tools

Use `RESTRICTED_TOOLS` to hide specific tools from MCP clients. Restricted tools are removed from the tool list and blocked if called directly.

For example, to give a team read-only access without any destructive operations:

```bash
RESTRICTED_TOOLS=delete_database,delete_policy,delete_rule,delete_tag,delete_tag_by_details,delete_classifier,delete_collection,delete_sc_repo,delete_sc_sidecar
```

Or in the Claude Desktop config:

```json
{
  "mcpServers": {
    "altr": {
      "command": "uvx",
      "args": ["altr-mcp"],
      "env": {
        "ORG_ID": "your-org-id",
        "MAPI_KEY": "your-api-key",
        "MAPI_SECRET": "your-api-secret",
        "RESTRICTED_TOOLS": "delete_database,delete_policy,delete_rule,delete_tag"
      }
    }
  }
}
```

This is an operator-level safety net — it prevents accidental or unwanted tool usage but is not a substitute for proper API key permissions.

## Setup

### Claude Desktop

Add the following to your `claude_desktop_config.json` (Settings > Developer > Edit Config):

```json
{
  "mcpServers": {
    "altr": {
      "command": "uvx",
      "args": ["altr-mcp"],
      "env": {
        "ORG_ID": "your-org-id",
        "MAPI_KEY": "your-api-key",
        "MAPI_SECRET": "your-api-secret"
      }
    }
  }
}
```

### Claude Code (CLI)

```bash
claude mcp add altr -e ORG_ID=your-org-id -e MAPI_KEY=your-api-key -e MAPI_SECRET=your-api-secret -- uvx altr-mcp
```

This writes the config to `.mcp.json` which can be committed to share with your team.

### Cursor

Add to `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project-scoped):

```json
{
  "mcpServers": {
    "altr": {
      "command": "uvx",
      "args": ["altr-mcp"],
      "env": {
        "ORG_ID": "your-org-id",
        "MAPI_KEY": "your-api-key",
        "MAPI_SECRET": "your-api-secret"
      }
    }
  }
}
```

### VS Code (GitHub Copilot)

Open User Settings JSON (Ctrl+Shift+P → "Preferences: Open User Settings (JSON)") and add:

```json
{
  "mcp": {
    "servers": {
      "altr": {
        "command": "uvx",
        "args": ["altr-mcp"],
        "env": {
          "ORG_ID": "your-org-id",
          "MAPI_KEY": "your-api-key",
          "MAPI_SECRET": "your-api-secret"
        }
      }
    }
  }
}
```

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "altr": {
      "command": "uvx",
      "args": ["altr-mcp"],
      "env": {
        "ORG_ID": "your-org-id",
        "MAPI_KEY": "your-api-key",
        "MAPI_SECRET": "your-api-secret"
      }
    }
  }
}
```

### Running from Local Source

To run from a local clone instead of the published PyPI package:

**Claude Code:**

```bash
claude mcp add altr \
  -e ORG_ID=your-org-id \
  -e MAPI_KEY=your-api-key \
  -e MAPI_SECRET=your-api-secret \
  -- uv run --directory /path/to/altr-mcp altr-mcp
```

**Claude Desktop:**

```json
{
  "mcpServers": {
    "altr": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/altr-mcp", "altr-mcp"],
      "env": {
        "ORG_ID": "your-org-id",
        "MAPI_KEY": "your-api-key",
        "MAPI_SECRET": "your-api-secret"
      }
    }
  }
}
```

## CLI (Optional)

> This section is for building a standalone CLI binary. If you just want to use the server with Claude Desktop or Claude Code, skip to [Tools](#tools).

A standalone CLI is available for using ALTR tools directly from the terminal without an MCP client.

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js](https://nodejs.org/) (for building the CLI)

### Building

From the repo root:

```bash
npx mcporter generate-cli --command "uv run --directory . altr-mcp" --name altr-cli --compile ./altr-cli
```

This generates a compiled binary at `./altr-cli`.

### Usage

Set your credentials as environment variables, then run any tool:

```bash
export ORG_ID=your-org-id
export MAPI_KEY=your-api-key
export MAPI_SECRET=your-api-secret

# List databases
./altr-cli get-databases

# Get a specific database ID
./altr-cli get-database-id --database-name "my_database"

# Create a masking policy
./altr-cli create-policy --tag "STOPLIGHT"

# Add rules (pass JSON string for complex params)
./altr-cli add-rules --policy-id "TAG#abc123" --rules '[{"masking_policy": 10001, "role": "PUBLIC", "tag_value": "red"}]'

# Search query audits
./altr-cli search-query-audits --limit 10

# JSON output
./altr-cli get-databases --output json

# See all available commands
./altr-cli --help
```

The CLI runs the MCP server locally via `uv run` and requires the repo to be present at the working directory. All environment variables from the [Configuration](#configuration) section apply.

## Tools

99 tools organized into 10 domains.

### Databases (8 tools)

| Tool | Description |
|---|---|
| `get_databases` | List connected databases |
| `get_database_id` | Get database ID by friendly name |
| `get_service_users` | List service users for keypair/token auth |
| `create_database` | Connect a new Snowflake or OLTP database |
| `create_databricks_database` | Connect a Databricks workspace |
| `update_database` | Update database connection properties |
| `trigger_database_status_sync` | Trigger a database status check |
| `delete_database` | Disconnect and remove a database |

### Roles (1 tool)

| Tool | Description |
|---|---|
| `get_roles` | List all ALTR roles (user groups) |

### Tags (8 tools)

> **Snowflake tags vs Databricks tags.** All eight tools below are Snowflake-only. A **Snowflake tag** is a first-class ALTR object — you register it with `connect_tag`, it gets a `tag_group_id`, and it shows up in `get_tags`, `get_tag_details*`, `update_tag`, and `delete_tag*`. A **Databricks tag** is the opposite: it is not an ALTR object at all, just a raw string you pass straight into `create_policy` (with `policy_type="PUSHDOWN"` and `database_ids=[…]`). Databricks tags never appear in `get_tags` and do not have a `tag_group_id` — none of the tools in this section apply to them.

| Tool | Description |
|---|---|
| `get_tags` | List all Snowflake tags connected to ALTR |
| `get_tag_values` | Get allowed values for a connected Snowflake tag |
| `get_tag_details` | Get connected Snowflake tag details by database, schema, and tag name |
| `get_tag_details_by_group_id` | Get connected Snowflake tag details by group ID |
| `connect_tag` | Register an existing Snowflake tag as an ALTR tag object |
| `update_tag` | Update a connected Snowflake tag's masking configuration |
| `delete_tag` | Delete a connected Snowflake tag by group ID |
| `delete_tag_by_details` | Delete a connected Snowflake tag by database, schema, and tag name |

### Policies & Rules (7 tools)

| Tool | Description |
|---|---|
| `get_policies` | List masking policies (all types or filtered) |
| `get_rules` | Get rules for a specific policy |
| `create_policy` | Create a masking policy for a tag |
| `add_rules` | Add masking rules to a policy |
| `update_rule` | Update a masking rule |
| `delete_rule` | Delete a masking rule |
| `delete_policy` | Delete a policy and all its rules |

**Databricks tag policies (`create_policy`):** when creating a masking policy for a Databricks metastore, you **must** pass `database_ids` as a list — even for a single database (e.g. `database_ids=[2167]`) — and set `policy_type="PUSHDOWN"`. Omitting `database_ids` or using `policy_type="TAG"` will be rejected by the API. Snowflake policies do the opposite: omit `database_ids` and let `policy_type` default to `TAG`.

### Classification (13 tools)

| Tool | Description |
|---|---|
| `get_classifiers` | List classifiers (pattern-based detectors) |
| `create_classifier` | Create a custom classifier |
| `delete_classifier` | Delete a custom classifier |
| `get_collections` | List classifier collections |
| `create_collection` | Create a classifier collection |
| `delete_collection` | Delete a classifier collection |
| `add_classifiers_to_collection` | Add classifiers to a collection |
| `remove_classifiers_from_collection` | Remove classifiers from a collection |
| `get_jobs` | List classification jobs |
| `create_job` | Run a classification scan (Snowflake / OLTP) |
| `create_databricks_job` | Run a GDLP classification scan on a Databricks connection |
| `update_job_status` | Pause, cancel, or resume a job |
| `get_classification_report` | Get results from a completed job |

### Access Management (4 tools)

| Tool | Description |
|---|---|
| `create_snowflake_access_policy` | Create a Snowflake access management policy |
| `create_oltp_access_policy` | Create an OLTP access management policy |
| `update_snowflake_access_policy` | Update a Snowflake access policy |
| `trigger_access_policy_check` | Trigger a manual compliance check |

### Access Requests (6 tools)

| Tool | Description |
|---|---|
| `create_access_request` | Submit a data access request |
| `get_access_requests` | List access requests |
| `get_access_request` | Get a specific access request |
| `approve_access_request` | Approve a pending request |
| `deny_access_request` | Deny a pending request |
| `cancel_access_request` | Cancel a request |

### Audits (6 tools)

| Tool | Description |
|---|---|
| `search_audits` | Search sidecar proxy query audits |
| `get_audit_results` | Get sidecar audit search results |
| `search_query_audits` | Search Snowflake query audits (tag/column masking) |
| `get_query_audit_results` | Get Snowflake query audit results |
| `search_system_audits` | Search ALTR platform system audits |
| `get_system_audit_results` | Get system audit results |

### Telemetry (9 tools)

| Tool | Description |
|---|---|
| `get_agent_instances` | List agent instances |
| `get_agent_instance` | Get a specific agent instance |
| `delete_agent_instance` | Delete an agent instance |
| `get_agent_task_telemetry` | Get task telemetry for an agent |
| `get_sidecar_instances` | List sidecar instances |
| `get_sidecar_instance` | Get a specific sidecar instance |
| `delete_sidecar_instance` | Delete a sidecar instance |
| `get_task_telemetry` | Get telemetry for a task |
| `delete_task_telemetry` | Delete task telemetry |

### Sidecar Configuration (37 tools)

**Agents** — `list_sc_agents`, `create_sc_agent`, `get_sc_agent`, `update_sc_agent`, `delete_sc_agent`

**Agent Tasks** — `list_sc_agent_tasks`, `create_sc_agent_task`, `update_sc_agent_task`, `delete_sc_agent_task`

**Repos** — `list_sc_repos`, `create_sc_repo`, `get_sc_repo`, `update_sc_repo`, `delete_sc_repo`

**Repo Users** — `list_sc_repo_users`, `create_sc_repo_user`, `get_sc_repo_user`, `update_sc_repo_user`, `delete_sc_repo_user`

**Service Users** — `list_sc_service_users`, `create_sc_service_user`, `get_sc_service_user`, `update_sc_service_user`, `delete_sc_service_user`

**Sidecars** — `list_sc_sidecars`, `create_sc_sidecar`, `get_sc_sidecar`, `update_sc_sidecar`, `delete_sc_sidecar`

**Listeners** — `list_sc_sidecar_listeners`, `register_sc_sidecar_listener`, `deregister_sc_sidecar_listener`

**Bindings** — `list_sc_sidecar_bindings`, `list_sc_repo_bindings`, `get_sc_sidecar_binding`, `create_sc_sidecar_binding`, `delete_sc_sidecar_binding`

## Data Source Support

| Feature | Snowflake | OLTP (via sidecar) | Databricks |
|---|---|---|---|
| Database connections | ✅ | — | ✅ |
| Tag masking & policies | ✅ | ❌ | ⚠️ Alpha |
| Classification | ✅ Full | ⚠️ Partial | ⚠️ Partial |
| Access management (RBAC) | ✅ | ✅ | ✅ |
| Access requests | ✅ | ❌ | ❌ |
| Query audit logging | ✅ | ✅ | ❌ |
| System audit logging | ✅ | ✅ | ❌ |
| Sidecar configuration | — | ✅ | — |
| Telemetry & monitoring | — | ✅ | — |

**Legend:** ✅ Supported &nbsp; ⚠️ Partial &nbsp; ❌ Not supported &nbsp; — Not applicable

**Classification — OLTP partial:** ALTR Native and Google DLP BYOK only; no automatic tagging.

**Classification — Databricks partial:** GDLP scan only (`create_databricks_job`); no classifier or collection selection.

**OLTP** refers to relational databases (PostgreSQL, MySQL, Oracle, SQL Server) accessed through a customer-managed ALTR sidecar proxy.

## Troubleshooting

### `uvx: command not found`

Install [uv](https://docs.astral.sh/uv/getting-started/installation/): `pip install uv` or via the [official installer](https://docs.astral.sh/uv/getting-started/installation/).

### Server not appearing in your AI client

Restart your AI client after editing the config file — changes are not picked up automatically.

### `ERROR: Missing required environment variables`

Verify `ORG_ID`, `MAPI_KEY`, and `MAPI_SECRET` are set in the `env` block of your client config. Variable names are case-sensitive.

### Tools returning `{"success": false, ...}`

| HTTP status | Likely cause | Fix |
|---|---|---|
| `401` | Invalid credentials | Verify `MAPI_KEY` / `MAPI_SECRET` in the ALTR console under **Settings > Preferences > API** |
| `403` | Insufficient permissions | Check that your API key has access to the resource |
| `404` | Resource not found | Confirm the ID exists in your organization |
| `429` | Rate limited | The server retries automatically up to 3× with backoff; if persistent, reduce request frequency |

### A tool is missing from the tool list

Check whether the tool name appears in the `RESTRICTED_TOOLS` env var in your client config. Restricted tools are hidden from the tool list entirely.

### Timeouts on large result sets

Use pagination parameters (`limit`, `offset`, or `cursor`) available on audit, telemetry, and classification tools to reduce response size.

## Development

### Running Tests

```bash
# Install dependencies
uv sync --extra dev

# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/integration/test_database.py

# Run a specific test
uv run pytest tests/integration/test_database.py::test_create_database_with_service_user

# Run with coverage report (terminal)
uv run pytest --cov=altr_mcp --cov-report=term-missing

# Run with coverage and generate an HTML report at htmlcov/index.html
uv run pytest --cov=altr_mcp --cov-report=html
```

### Project Structure

```
altr_mcp/
  server.py          # MCP server entrypoint and tool registration
  settings.py        # Pydantic settings (env vars)
  instructions.md    # System prompt for LLM tool guidance
  tools/             # Tool definitions (one file per domain)
  utils/             # API client functions (one file per API)
tests/
  unit/              # Unit tests (settings, models, annotations)
  integration/       # Integration tests (httpx mocks per domain)
```

## License

GNU General Public License v3.0 or later. See [LICENSE.md](LICENSE.md) for the full text.
