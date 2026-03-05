# ALTR MCP Server

mcp-name: io.github.altrsoftware/altr-mcp-server

ALTR MCP Server enables Claude and Cursor to automate data security configuration in ALTR. It reads Security Requirements documents, maps Snowflake metadata to ALTR tags, and auto-generates masking policies and rules. Without Snowflake credentials, it operates as a full-featured ALTR API wrapper with 20+ tools for managing tags, policies, and rules programmatically.

## Installation

Install from PyPI:

```bash
pip install altr-mcp
```

Or run directly with uvx (no install required):

```bash
uvx altr-mcp
```

## Configuration

Set the following environment variables before starting the server:

| Variable | Required | Description |
|---|---|---|
| ORG_ID | Yes | ALTR organization ID |
| MAPI_KEY | Yes | ALTR management API key |
| MAPI_SECRET | Yes | ALTR management API secret |
| SNOWFLAKE_ACCOUNT | No | Snowflake account identifier (e.g., xy12345.us-east-1) |
| SNOWFLAKE_USER | No | Snowflake username |
| SNOWFLAKE_PAT | No | Snowflake personal access token |
| SNOWFLAKE_WAREHOUSE | No | Snowflake compute warehouse name |
| SNOWFLAKE_ROLE | No | Snowflake role with tag and schema privileges |

Snowflake credentials are optional. Without them, the server operates as an ALTR API wrapper only. Add Snowflake credentials to enable tag creation and sync workflows.

## MCP Client Configuration

Add the following to your MCP client configuration (Claude Desktop or Cursor):

```json
{
  "mcpServers": {
    "altr": {
      "command": "altr-mcp",
      "env": {
        "ORG_ID": "your-org-id",
        "MAPI_KEY": "your-api-key",
        "MAPI_SECRET": "your-api-secret"
      }
    }
  }
}
```

To enable Snowflake workflows, add the optional Snowflake variables to the `env` block:

```json
{
  "mcpServers": {
    "altr": {
      "command": "altr-mcp",
      "env": {
        "ORG_ID": "your-org-id",
        "MAPI_KEY": "your-api-key",
        "MAPI_SECRET": "your-api-secret",
        "SNOWFLAKE_ACCOUNT": "xy12345.us-east-1",
        "SNOWFLAKE_USER": "your-snowflake-user",
        "SNOWFLAKE_PAT": "your-pat",
        "SNOWFLAKE_WAREHOUSE": "your-warehouse",
        "SNOWFLAKE_ROLE": "your-role"
      }
    }
  }
}
```

This configuration works for both Claude Desktop and Cursor.

## License

MIT
