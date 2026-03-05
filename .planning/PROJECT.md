# ALTR MCP Server

## What This Is

A production-grade Python MCP server that automates ALTR data security setup — reading security requirements documents, connecting Snowflake tags to ALTR, and creating masking policies and rules. Published to PyPI as `altr-mcp` and discoverable via the MCP Registry so any user can install, configure credentials, and start automating ALTR through Claude or Cursor.

## Core Value

Users can install one package (`altr-mcp`), provide their ALTR and Snowflake credentials, and have Claude orchestrate their entire data security configuration — no manual UI work required.

## Requirements

### Validated

- Source code migrated from GitLab to GitHub (`altrsoftware/altr-mcp-server`) — existing
- 20+ MCP tools covering policies, tags, Snowflake integration, classification jobs, and rules — existing
- `pyproject.toml` with hatchling build system, entry point, classifiers — existing
- `server.json` for MCP Registry with correct repo ID and OIDC auth — existing
- GitHub Actions publish workflow (PyPI + MCP Registry on `v*` tag) — existing
- README with install instructions, env vars table, MCP client config block — existing

### Active

- [ ] Tool modularization: break 900-line server.py into separate tool modules with dynamic loading (matching pycti-mcp plugin pattern)
- [ ] `src/` layout: move `altr_mcp/` to `src/altr_mcp/` for Python packaging best practice
- [ ] Type annotations: use `Annotated[Type, "description"]` pattern for MCP schema generation
- [ ] Error handling: consistent try-except with FastMCP `Context` logging across all tools
- [ ] Python logging: add `logging` module usage with configurable verbosity
- [ ] CLI: add `argparse` with `--verbose` flag and credential overrides
- [ ] CI testing: multi-Python matrix (3.11, 3.12, 3.13) with `uv build` + smoke test
- [ ] Schema validation: MCP Inspector tool list check in CI (like pycti-mcp `tests/tools_list.txt`)
- [ ] Gated publishing: publish workflow requires all test jobs to pass before PyPI upload
- [ ] README expansion: CLI usage docs, integration examples (Claude Desktop, Cursor, mcp-hub), tool reference with input/output docs

### Out of Scope

- Remote/SSE transport — deferred; stdio-only for now
- Plugin extensibility docs — ALTR tools are internal, not user-extensible
- Docker/OCI image — deferred to future milestone
- Build backend switch to uv_build — keeping hatchling (already working)
- npm wrapper — server is Python-only

## Context

- **Reference implementation**: `pycti-mcp` (ckane/pycti-mcp on GitHub) — production MCP server for OpenCTI with modular tools, dynamic loading, multi-version CI, schema validation, and OIDC publishing
- **Current state**: Source migrated from GitLab, package builds with `uv build`, CI publishes on tag but has no tests or quality gates
- **GitHub repo**: `altrsoftware/altr-mcp-server` (canonical source going forward)
- **GitLab repo**: `application-engineering/altr-mcp` (original, now secondary)
- **MCP Registry name**: `io.github.altrsoftware/altr-mcp-server`
- **PyPI package name**: `altr-mcp`

## Constraints

- **Tech stack**: Python 3.11+, FastMCP framework, hatchling build backend, uv package manager
- **GitHub OIDC**: Use OIDC auth for both PyPI and MCP Registry publishing (no PAT/tokens)
- **Backward compatibility**: Entry point `altr-mcp` and package name `altr-mcp` must not change
- **Tool behavior**: Refactoring must not change tool signatures, descriptions, or API behavior

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Adopt `src/` layout | Python packaging best practice, prevents accidental local imports during dev | — Pending |
| Keep hatchling build backend | Already working, well-supported, no benefit to switching | — Pending |
| Dynamic tool loading via `__all__` | Matches pycti-mcp pattern, makes tool addition low-friction | — Pending |
| `Annotated[Type, "description"]` for tool params | Auto-generates MCP schema without duplicating descriptions in docstrings | — Pending |
| Multi-Python CI matrix (3.11-3.13) | Matches `requires-python >= 3.11`, catches version-specific issues | — Pending |
| MCP Inspector schema validation in CI | Catches tool registration regressions automatically | — Pending |
| GitHub as canonical source | MCP Registry links land on GitHub, community contributions happen there | — Pending |

---
*Last updated: 2026-03-05 after initialization*
