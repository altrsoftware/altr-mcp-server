# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-03-23

### Added

- **Multi-transport support**: `MCP_TRANSPORT` env var selects `stdio` (default), `sse`, or `streamable-http` transport; `MCP_HOST` and `MCP_PORT` configure bind address and port for HTTP transports
- **Tool restriction middleware**: `RESTRICTED_TOOLS` env var accepts comma-separated tool names to hide from `tools/list` and block on `tools/call`
- **Structured JSON logging**: `LOG_FORMAT=json` emits structured JSON log lines via structlog; `LOG_FORMAT=console` (default) emits human-readable output
- **Correlation IDs**: every tool invocation generates a unique correlation ID (`func_name:hex8`) carried through all log entries for that invocation
- **HTTP retry with backoff**: transient API errors (429, 503) are retried up to 3 times with exponential backoff, jitter, and Retry-After header support via tenacity
- **Tool annotations**: get/list tools carry `readOnlyHint: true` and delete tools carry `destructiveHint: true` in MCP tool definitions
- **Pydantic input validation**: complex tool parameters (rule lists, policy configs, sidecar bindings, threshold objects) validated by Pydantic models before API calls
- **Integration test suite**: pytest-httpx based integration tests for all 9 tool domains with mocked HTTP responses

### Changed

- **BREAKING — Structured responses**: all tools now return `{success, data, error}` dicts instead of formatted strings:
  - tag tools (8): `get_tags`, `delete_tag`, `get_tag_values`, `get_tag_details_by_group_id`, `get_tag_details`, `connect_tag_by_group_id`, `delete_tag_by_details`, `connect_tag`
  - policy tools (8): `get_policies`, `get_rules`, `create_policy`, `add_rules`, `delete_policy`, `update_rule`, `delete_rule`, `get_roles`
  - classification tools (10): `get_classifiers`, `create_classifier`, `delete_classifier`, `get_collections`, `create_collection`, `delete_collection`, `get_jobs`, `create_job`, `update_job_status`, `get_classification_report`
  - database tools (2): `get_databases`, `get_database_id`
  - access management tools (4): `create_snowflake_access_policy`, `create_oltp_access_policy`, `update_snowflake_access_policy`, `trigger_access_policy_check`
  - access request tools (6): `create_access_request`, `get_access_requests`, `get_access_request`, `approve_access_request`, `deny_access_request`, `cancel_access_request`
  - telemetry tools (9): `get_agent_instances`, `get_agent_instance`, `delete_agent_instance`, `get_agent_task_telemetry`, `get_sidecar_instances`, `get_sidecar_instance`, `delete_sidecar_instance`, `get_task_telemetry`, `delete_task_telemetry`
  - audit tools (2): `search_audits`, `get_audit_results`
  - sidecar config tools (33): `list_sc_agents`, `create_sc_agent`, `get_sc_agent`, `update_sc_agent`, `delete_sc_agent`, `list_sc_repos`, `create_sc_repo`, `get_sc_repo`, `update_sc_repo`, `delete_sc_repo`, `list_sc_repo_users`, `create_sc_repo_user`, `get_sc_repo_user`, `update_sc_repo_user`, `delete_sc_repo_user`, `list_sc_service_users`, `create_sc_service_user`, `get_sc_service_user`, `update_sc_service_user`, `delete_sc_service_user`, `list_sc_sidecars`, `create_sc_sidecar`, `get_sc_sidecar`, `update_sc_sidecar`, `delete_sc_sidecar`, `list_sc_sidecar_listeners`, `deregister_sc_sidecar_listener`, `list_sc_sidecar_bindings`, `list_sc_repo_bindings`, `get_sc_sidecar_binding`, `create_sc_sidecar_binding`, `delete_sc_sidecar_binding`
- **BREAKING — Error handling**: tool errors now set MCP `isError: true` flag and return `{success: false, data: null, error: "message"}` instead of plain error strings
- **BREAKING — Architecture**: tool handlers moved from monolithic `server.py` (2,600+ lines) to 9 domain modules in `altr_mcp/tools/`; `server.py` reduced to ~60 lines of server configuration and tool registration
- **BREAKING — FastMCP upgrade**: migrated from `mcp[cli]` bundled FastMCP to standalone `fastmcp>=2.0,<3.0`
- **Logging**: replaced ad-hoc print-based logging with structlog-based structured logging via `@log_tool` decorator
- **Instructions**: server instructions extracted from inline string to `altr_mcp/instructions.md`

### Removed

- `mcp[cli]` dependency replaced by standalone `fastmcp>=2.0,<3.0`
- Inline tool handlers in `server.py` (moved to `altr_mcp/tools/` modules)
- Plain string tool responses (replaced by structured `{success, data, error}` dicts)

## [0.1.0] - 2026-03-13

### Added

- 83 MCP tools covering tags, masking policies, rules, classification, access management, sidecar config, telemetry, and audits
- Pydantic Settings singleton for validated configuration with fail-fast startup
- Structured logging to stderr with configurable LOG_LEVEL
- `@log_tool` decorator for universal invocation logging and error handling
- Pydantic validation models for `access_rate_thresholds` and `time_window_thresholds`
- Configurable base URLs for all ALTR API endpoints
- SecretStr masking for MAPI_KEY and MAPI_SECRET
