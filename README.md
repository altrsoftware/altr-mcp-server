# ALTR MCP Server

[![PyPI](https://img.shields.io/pypi/v/altr-mcp.svg)](https://pypi.org/project/altr-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/altr-mcp)](https://pypi.org/project/altr-mcp/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE.md)
[![CI](https://github.com/altrsoftware/altr-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/altrsoftware/altr-mcp-server/actions/workflows/ci.yml)
[![Security](https://github.com/altrsoftware/altr-mcp-server/actions/workflows/security.yml/badge.svg)](https://github.com/altrsoftware/altr-mcp-server/actions/workflows/security.yml)

[ALTR](https://www.altr.com) provides tag-based data masking, access governance, and classification for Snowflake, Databricks, and OLTP databases. This MCP server enables AI assistants (Claude, Cursor, and other MCP clients) to manage data security on the ALTR platform — 156 tools across 13 domains covering database connections, tag masking, policies, classification, access management, audits, telemetry, and sidecar configuration.

> **New to ALTR?** See the [ALTR documentation](https://docs.altr.com) for an overview of the platform, concepts, and supported data sources.

All tools return structured `{success, data, error}` responses and can run over stdio, SSE, or streamable-http transports.

## Table of Contents

- [Quick Start](#quick-start)
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
- [CLI](#cli-optional)
- [Tools](#tools)
- [Data Source Support](#data-source-support)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [License](#license)

## Quick Start

1. **Install from PyPI:**

   ```bash
   pip install altr-mcp
   ```

   Or run directly with [uvx](https://docs.astral.sh/uv/guides/tools/) (no install required):

   ```bash
   uvx altr-mcp
   ```

   > `uvx` is part of the [uv](https://docs.astral.sh/uv/) Python package manager. Install it with `pip install uv` or see the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/).

2. **Set the three required environment variables** (see [Getting Credentials](#getting-credentials) for where to find each in the ALTR console):

   ```bash
   export ORG_ID=your-org-id
   export MAPI_KEY=your-api-key
   export MAPI_SECRET=your-api-secret
   ```

3. **Wire it into your AI client** — see [Setup](#setup) for Claude Desktop, Claude Code, Cursor, VS Code, and Windsurf. The same three env vars go into the client's `env` block.

4. **Verify** by asking your AI assistant to run a read-only tool:

   - "List my ALTR databases" → calls `get_databases`
   - "Show me the tags connected to ALTR" → calls `get_tags`
   - "List the ALTR roles in my org" → calls `get_roles`

   If these return data, your setup is working.

## Getting Credentials

You need three values from the ALTR platform to configure this server. See [Manage API keys](https://docs.altr.com/api/manage-api-keys/) for the full reference.

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

### Restricting Tools

Use `RESTRICTED_TOOLS` to hide specific tools from MCP clients. Restricted tools are removed from the tool list and blocked if called directly.

For example, to give a team read-only access without any destructive operations:

```bash
RESTRICTED_TOOLS=disconnect_database,delete_policy,delete_rule,disconnect_tag,disconnect_tag_by_details,delete_classifier,delete_collection,disconnect_sc_repo,disconnect_sc_sidecar
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
        "RESTRICTED_TOOLS": "disconnect_database,delete_policy,delete_rule,disconnect_tag"
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

> This section is for building a standalone CLI binary from the MCP server. If you just want to use the server with Claude Desktop or Claude Code, skip to [Tools](#tools).

A standalone CLI lets you call ALTR tools directly from the terminal without an MCP client. It's built with [mcporter](https://github.com/openclaw/mcporter), an open-source tool that compiles MCP servers into native CLI binaries. See the [mcporter docs](https://github.com/openclaw/mcporter) for the full set of options.

### Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [Node.js](https://nodejs.org/) (for `npx` to fetch and run `mcporter`)

`mcporter` itself does not need to be installed separately — `npx` downloads and runs it on demand.

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

156 tools across 13 domains. For a full breakdown of every tool with parameters, behavior, and examples, see [docs/index.md](./docs/index.md).

| Domain | Tools | What it does |
|---|---|---|
| [Databases](./docs/databases.md) | 8 | Connect Snowflake, OLTP, and Databricks data sources. Setup per platform: [Snowflake](https://docs.altr.com/data-sources/snowflake/), [OLTP](https://docs.altr.com/data-sources/oltp/), [Databricks](https://docs.altr.com/data-sources/databricks/). |
| Roles | 1 | `get_roles` — list all ALTR roles (called [user groups](https://docs.altr.com/page-descriptions/user-groups/) in the ALTR console). |
| [Tags](./docs/tags.md) | 8 | Manage Snowflake tag connections to ALTR. See [Snowflake tag-based access policy](https://docs.altr.com/features/data-access-controls/tag-based-access-policy/snowflake/). |
| [Policies & Rules](./docs/policies.md) | 7 | Create masking policies and per-role rules. Tag-based ([Snowflake](https://docs.altr.com/features/data-access-controls/tag-based-access-policy/snowflake/), [Databricks](https://docs.altr.com/features/data-access-controls/tag-based-access-policy/databricks/)) and [column-based](https://docs.altr.com/features/data-access-controls/column-based-access-policy/) (Snowflake only). [Masking levels 10000–10009](https://docs.altr.com/features/data-access-controls/masking-policies/). |
| [Classification](./docs/classification.md) | 13 | Run automated [data classification scans](https://docs.altr.com/features/data-classification/). Snowflake (in-house + ALTR Native + GDLP), OLTP (ALTR Native + GDLP), Databricks (GDLP only). |
| [Access Management](./docs/access-management.md) | 4 | Access management policies for [Snowflake](https://docs.altr.com/features/data-access-controls/access-management-policy/snowflake/) and [OLTP](https://docs.altr.com/features/data-access-controls/access-management-policy/oltp/). Databricks access control is not exposed through this server. |
| [Access Requests](./docs/access-requests.md) | 6 | Submit, review, and resolve Snowflake [data access requests](https://docs.altr.com/features/data-access-controls/manage-access-requests/). |
| [Audits](./docs/audits.md) | 6 | Search sidecar, Snowflake query, and platform [system audits](https://docs.altr.com/features/audit-logging/). |
| [Telemetry](./docs/telemetry.md) | 9 | Monitor [ALTR sidecar proxy](https://docs.altr.com/data-sources/oltp/) agent and sidecar instance health. |
| [Sidecar Configuration](./docs/sidecar-config.md) | 37 | Configure the [ALTR sidecar proxy](https://docs.altr.com/data-sources/oltp/) — agents, repos, repo users, service users, sidecars, listeners, and bindings. |

### Critical callouts

A few things are easy to miss and worth surfacing here:

**Snowflake tags vs Databricks tags.** A **Snowflake tag** is a first-class ALTR object — you register it with `connect_tag`, it gets a `tag_group_id`, and shows up in `get_tags`, `get_tag_details*`, `update_tag`, and `disconnect_tag*`. A **Databricks tag** is the opposite: not an ALTR object at all, just a raw string you pass into `create_policy` (with `policy_type="PUSHDOWN"` and `database_ids=[…]`). Databricks tags never appear in `get_tags` and do not have a `tag_group_id`. None of the Tags tools apply to Databricks.

**Databricks `create_policy` requirements.** When creating a masking policy for a Databricks metastore, you **must** pass `database_ids` as a list — even for a single database (e.g. `database_ids=[2167]`) — and set `policy_type="PUSHDOWN"`. Omitting `database_ids` or using `policy_type="TAG"` will be rejected by the API. Snowflake policies do the opposite: omit `database_ids` and let `policy_type` default to `TAG`.

## Data Source Support

Platform setup guides on the ALTR docs site:
- [Snowflake](https://docs.altr.com/data-sources/snowflake/)
- [OLTP databases](https://docs.altr.com/data-sources/oltp/) (PostgreSQL, MySQL, Oracle, SQL Server)
- [Databricks](https://docs.altr.com/data-sources/databricks/)

| Feature | Snowflake | OLTP (via sidecar) | Databricks |
|---|---|---|---|
| Database connections | ✅ | — | ✅ |
| Masking policies | ✅ | ❌ | ✅ |
| Classification | ✅ | ✅ | ⚠️ Partial |
| Access management policies | ✅ | ✅ | ❌ |
| Access requests | ✅ | ❌ | ❌ |
| Query audit logging | ✅ | ✅ | ❌ |
| System audit logging | ✅ | ✅ | ❌ |
| Sidecar configuration | — | ✅ | — |
| Telemetry & monitoring | — | ✅ | — |

**Legend:** ✅ Supported &nbsp; ⚠️ Partial &nbsp; ❌ Not supported &nbsp; — Not applicable

**Classification mode coverage:**

| Mode | Snowflake | OLTP | Databricks |
|---|---|---|---|
| In-house (ALTR pattern matching) | ✅ | ❌ | ❌ |
| ALTR Native classifiers | ✅ | ✅ | ❌ |
| GDLP (Google Cloud DLP) | ✅ | ✅ | ✅ |

**Databricks classification — Partial:** GDLP only via `create_databricks_job`; no in-house or ALTR Native classifiers. A `collection_name` may optionally be passed to scope the scan to a specific ALTR collection's classifiers (subject to `condition_types`); when omitted, all default Google DLP infoTypes are used.

**Access management policies (Databricks):** This MCP server does not currently expose Databricks grant or access management APIs. For Databricks access control, use the Databricks UI or REST API directly.

**OLTP** refers to relational databases (PostgreSQL, MySQL, Oracle, SQL Server) accessed through a customer-managed [ALTR sidecar proxy](https://docs.altr.com/data-sources/oltp/).

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
| `403` | Feature not enabled for this organization | The endpoint exists but is gated by an ALTR feature flag your org doesn't have turned on. Contact ALTR support to confirm the feature is enabled for your account. |
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

## Learn More

**Platform setup**
- [ALTR documentation home](https://docs.altr.com)
- [Snowflake data source](https://docs.altr.com/data-sources/snowflake/)
- [OLTP data source](https://docs.altr.com/data-sources/oltp/)
- [Databricks data source](https://docs.altr.com/data-sources/databricks/)
- [Manage API keys](https://docs.altr.com/api/manage-api-keys/)

**Data access controls**
- [Tag-based access policy — Snowflake](https://docs.altr.com/features/data-access-controls/tag-based-access-policy/snowflake/)
- [Tag-based access policy — Databricks](https://docs.altr.com/features/data-access-controls/tag-based-access-policy/databricks/)
- [Column-based access policy — Snowflake](https://docs.altr.com/features/data-access-controls/column-based-access-policy/)
- [Masking policies (10000–10009 types)](https://docs.altr.com/features/data-access-controls/masking-policies/)
- [Access management policy — Snowflake](https://docs.altr.com/features/data-access-controls/access-management-policy/snowflake/)
- [Access management policy — OLTP](https://docs.altr.com/features/data-access-controls/access-management-policy/oltp/)
- [Manage access requests](https://docs.altr.com/features/data-access-controls/manage-access-requests/)

**Discovery and observability**
- [Data Classification](https://docs.altr.com/features/data-classification/)
- [Audit Logging](https://docs.altr.com/features/audit-logging/)

**Protocol**
- [Model Context Protocol specification](https://modelcontextprotocol.io)

## License

GNU General Public License v3.0 or later. See [LICENSE.md](LICENSE.md) for the full text.
