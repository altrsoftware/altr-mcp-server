# Requirements: ALTR MCP Server

**Defined:** 2026-03-06
**Core Value:** Users can install one package, provide ALTR and Snowflake credentials, and have Claude orchestrate their entire data security configuration

## v1 Requirements

### Structural Foundation

- [ ] **STRUC-01**: Package uses `src/altr_mcp/` layout with hatchling `[tool.hatch.build.targets.wheel] packages` config
- [ ] **STRUC-02**: Credentials extracted to `src/altr_mcp/auth.py` (ALTR auth + env var loading) to prevent circular imports when tools are modularized
- [ ] **STRUC-03**: Tools split from 900-line `server.py` into domain modules under `src/altr_mcp/tools/` (policy, tag, classification, database, snowflake)
- [ ] **STRUC-04**: Dynamic tool loading via `__all__` list in `tools/__init__.py` + `importlib.import_module` in server startup
- [ ] **STRUC-05**: CLI entry point uses `argparse` with `--verbose` flag for log level control
- [ ] **STRUC-06**: Python `logging` module configured at server startup with level based on `--verbose` flag
- [ ] **STRUC-07**: `server.py` reduced to thin orchestrator: parse args, configure logging, load tools dynamically, start FastMCP

### Schema & Error Quality

- [ ] **QUAL-01**: All tool parameters use `Annotated[Type, "description"]` pattern for MCP schema generation
- [ ] **QUAL-02**: All tools have consistent try-except error handling with `ctx: Context` logging (not bare returns)
- [ ] **QUAL-03**: Tools annotated with MCP hints: `read_only_hint=True` on get/list tools, `destructive_hint=True` on delete tools, `idempotent_hint=True` where applicable

### CI/CD Hardening

- [ ] **CI-01**: GitHub Actions test workflow runs on push/PR with Python 3.11, 3.12, 3.13 matrix
- [ ] **CI-02**: Test workflow builds package with `uv build` and runs smoke test (`altr-mcp --help`)
- [ ] **CI-03**: `tests/tools_list.txt` golden file lists all expected tool names (alphabetical)
- [ ] **CI-04**: Test workflow validates tool list matches golden file (schema regression guard)
- [ ] **CI-05**: Publish workflow requires all test matrix jobs to pass before PyPI upload
- [ ] **CI-06**: Publish workflow validates tag version matches `pyproject.toml` version (hard fail, not warning)

### Documentation

- [ ] **DOC-01**: README has tool reference section documenting all tools with inputs, outputs, and descriptions
- [ ] **DOC-02**: README has integration examples for Claude Desktop, Cursor, and mcp-hub configurations

## v2 Requirements

### Remote Deployment

- **REMOTE-01**: Terraform infrastructure for Lambda hosting with SSE/streamable-http transport
- **REMOTE-02**: `remotes` section in server.json with Lambda endpoint URL
- **REMOTE-03**: Server transport supports remote connection mode

### Extended Distribution

- **DIST-01**: Docker/OCI image published to GHCR
- **DIST-02**: Automated version bump PR on release tag

## Out of Scope

| Feature | Reason |
|---------|--------|
| Remote Lambda deployment | Deferred — stdio/PyPI distribution first |
| SSE/HTTP transport | Deferred — requires remote infrastructure |
| npm wrapper package | Server is Python; npm adds complexity without benefit |
| Switch to standalone `fastmcp` 3.x | Current `mcp[cli]` works; migration is separate risk |
| Build backend switch to `uv_build` | Hatchling works; no benefit to switching |
| Plugin extensibility docs | Tools are internal to ALTR, not user-extensible |
| Docker image | Deferred to v2 |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| STRUC-01 | Phase ? | Pending |
| STRUC-02 | Phase ? | Pending |
| STRUC-03 | Phase ? | Pending |
| STRUC-04 | Phase ? | Pending |
| STRUC-05 | Phase ? | Pending |
| STRUC-06 | Phase ? | Pending |
| STRUC-07 | Phase ? | Pending |
| QUAL-01 | Phase ? | Pending |
| QUAL-02 | Phase ? | Pending |
| QUAL-03 | Phase ? | Pending |
| CI-01 | Phase ? | Pending |
| CI-02 | Phase ? | Pending |
| CI-03 | Phase ? | Pending |
| CI-04 | Phase ? | Pending |
| CI-05 | Phase ? | Pending |
| CI-06 | Phase ? | Pending |
| DOC-01 | Phase ? | Pending |
| DOC-02 | Phase ? | Pending |

**Coverage:**
- v1 requirements: 18 total
- Mapped to phases: 0 (pending roadmap)
- Unmapped: 18

---
*Requirements defined: 2026-03-06*
