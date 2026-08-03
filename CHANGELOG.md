# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- The release gate treated any `## [...]` heading as a release, so a
  `## [Unreleased]` section at the top of `CHANGELOG.md` would have failed
  every release — with an error suggesting the tag be `Unreleased`. That
  heading is the standard Keep a Changelog convention, which this file's own
  header says the project follows, so it was a trap waiting for whoever
  adopted it. Only `MAJOR.MINOR.PATCH` headings count as releases now, and a
  changelog with no release section names the rename in the error rather than
  reporting the section merely absent.

  This also makes the two readers of this file agree. The `server.json` guard
  already matched semver headings only; the release gate did not, so they
  would have disagreed about which section was newest.

## [0.5.6]

### Security
- `mcp-publisher` is now pinned to a specific release (`v1.8.0`) and verified
  against a committed SHA-256 digest before it runs. It was fetched from
  `releases/latest` with no version pin, no checksum, and no `curl --fail`,
  then piped straight into `tar` and executed — in the job that holds
  `id-token: write` for the `io.github.altrsoftware` registry namespace. Any
  upstream release, or a replaced asset on an existing one, silently changed
  what we ran with permission to publish as us. Without `--fail`, an error
  page would also have been fed to `tar` as if it were the binary.

  The digest is committed here rather than taken from the release's
  `checksums.txt`, which would only have caught a corrupt download: anyone
  able to replace the tarball can replace the checksum file beside it.

### Fixed
- The `publish` and `publish-mcp` jobs ran with different permissions for no
  stated reason: both check out the repository, but only `publish-mcp`
  declared `contents: read`. A job-level permissions block replaces the
  workflow-level one outright, so this was a real difference rather than a
  cosmetic one. They now match.

## [0.5.5]

### Added
- Documentation is now checked against the live tool registry in CI. Tool names
  in `README.md`, `docs/`, `.env.example`, and `altr_mcp/instructions.md` must
  resolve to a registered tool, and every "N tools" claim must match what
  `register_all` actually registers. A new tool module fails the suite until it
  has a domain doc and a row in both documentation tables.
- `server.json` is now checked against the newest `CHANGELOG.md` section, so the
  version recorded there can no longer drift. It was stale going into this
  release, as it has been going into most of them.
- `verify-release` now requires the tag's `CHANGELOG.md` section to be the
  newest one, not merely present somewhere in the file. The old check would
  have passed a `v0.5.4` tag today, re-releasing an already-published version,
  because a non-empty `## [0.5.4]` section still exists further down. The
  check moved out of the workflow YAML into
  [`scripts/check_changelog.py`](scripts/check_changelog.py) so it can be unit
  tested — as inline shell it only ever ran during a live release, which is why
  the gap survived.

### Fixed
- The MCP handshake reported FastMCP's own version as `serverInfo.version`
  (3.2.4) rather than the package version (0.5.4). The server is now
  constructed with `version=`, so every client sees the real version. Anyone
  who read the server version from a client — to check an upgrade landed, or
  in a bug report — was reading the framework's version number.
- `altr-mcp --version` and `--help` were silently ignored: the flags were never
  parsed, so the server started on stdio instead. Interactively that looked
  like a hang, since the process sat waiting for MCP traffic on stdin. Both
  flags now work, and neither requires `ORG_ID`/`MAPI_*` to be set. An
  unrecognized flag is now an error rather than an unexpected server start.
- The PyPI package summary advertised "135 tools across 13 domains"; the server
  registers 156.
- The README domain table listed 9 of 13 domains and summed to 93 tools under a
  heading claiming 156. Access Requests, Audit Reports, Vault Tokenization,
  Critical Tokenization, and Key Management were missing entirely, and
  Classification was listed as 13 tools instead of 36.

## [0.5.4]

### Added
- Tag pushes now run a `verify-release` job that fails the release if the built
  version disagrees with the tag, or if `CHANGELOG.md` has no non-empty section
  for it. `publish` depends on it and `publish-mcp` depends on `publish`, so
  nothing downstream runs when it fails.
- A `RESTRICTED_TOOLS` entry matching no registered tool is now logged as a
  warning naming the entries, the first time a client lists tools, instead of
  being silently ignored.

### Fixed
- The `RESTRICTED_TOOLS` example in `.env.example` still listed
  `delete_database` and `delete_tag`, renamed to `disconnect_*` in 0.4.0. The
  middleware matches names exactly, so an operator who copied that example
  restricted two of the four tools they asked for and left the other two fully
  callable.

## [0.5.3]

### Fixed
- The package version is now derived from the git tag at build time
  (`uv-dynamic-versioning`) instead of being hardcoded in `pyproject.toml`.
  Tagging a release no longer requires a separate version bump commit, and the
  PyPI upload can no longer fail because `pyproject.toml` still carries the
  previously published version — which is what happened to `v0.5.2`. Builds
  outside a git checkout fall back to version `0.0.0+unknown`. The local version
  segment is deliberate: PyPI rejects any version carrying one, so a build
  environment that cannot read the tag fails the release rather than publishing
  a wrong version.

### Changed
- The release workflow now stamps the tag into `server.json` (`.version` and
  `.packages[].version`) before publishing to the MCP Registry, so the git tag
  is the single source of truth for the PyPI version and the registry entry
  alike. The values committed in `server.json` record the next intended
  release; they are not an input to the publish job.
- Documented the release procedure and its `git` prerequisite in
  [docs/releasing.md](docs/releasing.md).
- Removed broken documentation links from the README.

### Security
- Bumped the transitive `mcp` (MCP Python SDK) dependency 1.27.1 → 1.28.1 to
  resolve three HIGH severity CVEs flagged by the Trivy scan: CVE-2026-59950
  (WebSocket transport lacks Host/Origin validation), CVE-2026-52870
  (experimental task handlers allow cross-client task access/cancel), and
  CVE-2026-52869 (HTTP transports serve sessions without verifying the
  principal).

> `v0.5.2` was tagged but never published to PyPI or the MCP Registry — its
> changes ship in 0.5.3.

## [0.5.1]

### Added
- Published to the official MCP Registry (`io.github.altrsoftware/altr-mcp-server`).
  Added the `mcp-name` ownership token to the README so the registry can verify
  the PyPI package, and a `publish-mcp` GitHub Actions job that publishes to the
  registry via GitHub OIDC on each `v*` tag.

### Changed
- Migrated `server.json` to the current registry schema
  (`2025-12-11`): camelCase package fields, string `repository.id`, and a
  registry-compliant description (≤100 chars).

## [0.5.0]

### Fixed
- `create_gdlp_job` (Snowflake GDLP) posted to the removed `POST /v1/jobs/gdlp`
  endpoint, causing every call to fail with HTTP 500 after retry exhaustion. It
  now posts to `POST /v1/jobs/snowflake` with `classification_type: "gdlp"`, the
  current Classification API contract.
- `create_job` (ALTR-native Snowflake) posted to the deprecated generic
  `POST /v1/jobs` endpoint. It now posts to `POST /v1/jobs/snowflake` with
  `classification_type: "altr_native"`.

### Added
- `create_gdlp_job` now accepts optional `collection_name` (to scope which
  Google DLP infoTypes are inspected), `sample_size`, and `sample_type`.
- `create_databricks_job` now accepts optional `collection_name` to scope the
  GDLP infoTypes evaluated for a Databricks workspace scan.

### Security
- Bumped transitive/direct dependencies flagged by the Trivy vulnerability
  scan: `joserfc` 1.6.5 → 1.7.2 (CVE-2026-48990, JWS payload resource
  exhaustion) and `pydantic-settings` 2.14.1 → 2.14.2 (GHSA-4xgf-cpjx-pc3j,
  `NestedSecretsSettingsSource` symlink traversal outside `secrets_dir`).

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
