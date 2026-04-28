title: ALTR MCP Server

# ALTR MCP Server Documentation

97 tools across 12 domains for managing data security on the ALTR platform.

## Domains

- [Databases](databases.md) — Connect, manage, and monitor Snowflake database connections (7 tools)
- [Tags](tags.md) — Connect and manage Snowflake tags for masking policies (8 tools)
- [Policies & Rules](policies.md) — Create masking policies and configure per-role masking rules (8 tools)
- [Classification](classification.md) — Run automated data classification scans and manage classifiers (12 tools)
- [Access Management](access-management.md) — Create and manage Snowflake and OLTP access policies (4 tools)
- [Access Requests](access-requests.md) — Submit and manage data access approval requests (6 tools)
- [Audits](audits.md) — Search sidecar, Snowflake query, and system audit logs (6 tools)
- [Telemetry](telemetry.md) — Monitor agent and sidecar instance health (9 tools)
- [Sidecar Configuration](sidecar-config.md) — Manage agents, repos, sidecars, listeners, bindings, and tasks (37 tools)

## Reference

- [Error Handling](error-handling.md) — Error types, retry behavior, and response structure

## Common Patterns

All tools return structured responses:

```json
{"success": true, "data": {...}, "error": null}
```

On failure:

```json
{"success": false, "data": null, "error": "error message"}
```

Parameters that accept lists (rules, classifier names, audit filters) also accept JSON strings for CLI compatibility.
