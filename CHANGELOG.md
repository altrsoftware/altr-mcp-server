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
