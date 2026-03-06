# Roadmap: ALTR MCP Server

## Overview

Transform a functional-but-monolithic MCP server into a production-grade PyPI package. The work proceeds in four phases with hard technical dependencies: restructure the package layout and modularize tools first, then improve schema and error quality within the stable module structure, then harden CI with test gates and schema regression guards, and finally write accurate documentation against the verified, stable package.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Structural Foundation** - Migrate to src/ layout, modularize tools into domain modules, extract credentials, add CLI and logging
- [ ] **Phase 2: Schema and Error Quality** - Annotate all tool parameters, add consistent error handling, apply MCP tool hints
- [ ] **Phase 3: CI Hardening** - Multi-Python test matrix, schema golden file, gated publish, version/tag hard-fail
- [ ] **Phase 4: Documentation** - Tool reference section, multi-client integration examples

## Phase Details

### Phase 1: Structural Foundation
**Goal**: Package has a clean, modular structure — src/ layout, domain tool modules with dynamic loading, extracted credentials, argparse CLI, and stdlib logging — with behavior identical to current
**Depends on**: Nothing (first phase)
**Requirements**: STRUC-01, STRUC-02, STRUC-03, STRUC-04, STRUC-05, STRUC-06, STRUC-07
**Success Criteria** (what must be TRUE):
  1. `uv build` produces a wheel that installs cleanly and `altr-mcp --help` prints usage on Python 3.11, 3.12, and 3.13
  2. All 20+ tools appear in MCP Inspector tool list — count and names match the pre-refactor baseline
  3. `altr-mcp --verbose` produces log output to stderr; running without the flag produces no log output
  4. `server.py` contains only FastMCP init, argparse, dynamic loader loop, and `main()` — no tool definitions
  5. `credentials.py` owns all auth and env var loading; tool modules import from it without circular dependency errors
**Plans**: TBD

### Phase 2: Schema and Error Quality
**Goal**: All tools are correctly annotated for LLM consumption and fail gracefully with structured error context
**Depends on**: Phase 1
**Requirements**: QUAL-01, QUAL-02, QUAL-03
**Success Criteria** (what must be TRUE):
  1. MCP Inspector shows parameter descriptions for every tool parameter — no parameters lack descriptions
  2. Invoking a tool with invalid credentials returns a structured error message via ctx.error(), not a raw exception traceback
  3. Read/list tools show `read_only_hint=True` and delete tools show `destructive_hint=True` in the MCP schema
**Plans**: TBD

### Phase 3: CI Hardening
**Goal**: Every push and tag runs a verified test gate — the package cannot reach PyPI unless it builds, installs, starts, and passes schema validation on all supported Python versions
**Depends on**: Phase 2
**Requirements**: CI-01, CI-02, CI-03, CI-04, CI-05, CI-06
**Success Criteria** (what must be TRUE):
  1. A pull request with a broken import or missing tool registration fails CI before merge — the failure is visible in the PR check list
  2. Pushing a `v*` tag where the tag version does not match `pyproject.toml` version causes the publish workflow to hard-fail with an explicit error, not a warning
  3. The PyPI publish job does not start unless all three Python version jobs (3.11, 3.12, 3.13) pass
  4. `tests/tools_list.txt` is committed and the CI diff step detects when a tool is added or removed without updating the golden file
**Plans**: TBD

### Phase 4: Documentation
**Goal**: Users can find, install, configure, and use the MCP server from the README alone — no external knowledge required
**Depends on**: Phase 3
**Requirements**: DOC-01, DOC-02
**Success Criteria** (what must be TRUE):
  1. README contains a tool reference section covering all 20+ tools with their input parameters and expected outputs
  2. README contains working configuration blocks for Claude Desktop, Cursor, and mcp-hub that a user can copy and paste without modification
  3. `uvx altr-mcp@latest` is shown as the primary no-install invocation path in the README
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Structural Foundation | 0/TBD | Not started | - |
| 2. Schema and Error Quality | 0/TBD | Not started | - |
| 3. CI Hardening | 0/TBD | Not started | - |
| 4. Documentation | 0/TBD | Not started | - |
