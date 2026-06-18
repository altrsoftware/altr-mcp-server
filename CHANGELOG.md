# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0]

### Added
- `create_oltp_job` tool for running on-demand classification scans on OLTP
  databases (Oracle, MSSQL, MySQL, PostgreSQL) via a sidecar classification
  agent, wired to `POST /v1/jobs/oltp`. `create_job` remains Snowflake-only
  (it requires a numeric `database_id`, which OLTP sidecar repos do not have).
- `create_gdlp_job` tool for Snowflake GDLP (Google DLP) classification scans,
  wired to `POST /v1/jobs/gdlp`. A separate job type from ALTR-native
  `create_job` — it does not use a classifier collection.

### Changed
- Renamed 11 tools from `delete_*` to `disconnect_*` to distinguish removing an
  object from ALTR's view (the object still exists externally) from destroying
  the object itself:

  | Old name | New name |
  |----------|----------|
  | `delete_database` | `disconnect_database` |
  | `delete_tag` | `disconnect_tag` |
  | `delete_tag_by_details` | `disconnect_tag_by_details` |
  | `delete_sc_agent` | `disconnect_sc_agent` |
  | `delete_sc_repo` | `disconnect_sc_repo` |
  | `delete_sc_repo_user` | `disconnect_sc_repo_user` |
  | `delete_sc_service_user` | `disconnect_sc_service_user` |
  | `delete_sc_sidecar` | `disconnect_sc_sidecar` |
  | `delete_sc_sidecar_binding` | `disconnect_sc_sidecar_binding` |
  | `delete_agent_instance` | `disconnect_agent_instance` |
  | `delete_sidecar_instance` | `disconnect_sidecar_instance` |

  Truly destructive tools keep `delete_*` (`delete_policy`, `delete_rule`,
  `delete_classifier`, `delete_collection`, `delete_sc_agent_task`,
  `vault_delete_tokens`, `critical_delete_tokens`, `delete_task_telemetry`).
  Migration: update any `RESTRICTED_TOOLS` configuration or client code that
  references the old `delete_*` names.

### Security
- Bumped transitive dependencies flagged by the Trivy vulnerability scan:
  `starlette` 1.0.0 → 1.3.1 (CVE-2026-48710), `cryptography` 48.0.0 → 49.0.0
  (GHSA-537c-gmf6-5ccf), `pyjwt` 2.12.1 → 2.13.0 (CVE-2026-48526), and
  `python-multipart` 0.0.28 → 0.0.32 (CVE-2026-53539).
