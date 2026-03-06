# Feature Landscape

**Domain:** Production-grade Python MCP server, published to PyPI and MCP Registry
**Project:** altr-mcp
**Researched:** 2026-03-06
**Sources:** pycti-mcp reference implementation (local), FastMCP docs, MCP Registry schema docs, live codebase analysis

---

## Current Baseline

The server is functional but not production-grade. It has:
- 20+ working tools registered via `@mcp.tool()` in a single 899-line `server.py`
- No type annotations on tool parameters (parameters lack `Annotated[Type, "description"]`)
- No `argparse` CLI — `main()` just calls `mcp.run(transport='stdio')`
- No `logging` module usage — errors surface only if the MCP client propagates them
- No error handling in tool bodies — unhandled exceptions propagate raw to the LLM
- No `src/` layout — package is `altr_mcp/` at repo root
- CI publishes on `v*` tag with no test gate, no multi-Python matrix, no schema validation
- README has install instructions and env vars table but no CLI usage, no tool reference,
  no integration configs beyond Claude Desktop / Cursor basics

---

## Table Stakes

Features that users (developers integrating this server, and end users running it) expect from a published PyPI MCP server. Absence causes distrust, breakage, or immediate uninstall.

| Feature | Why Expected | Complexity | Current State |
|---------|--------------|------------|---------------|
| `Annotated[Type, "description"]` type annotations on all tool parameters | FastMCP uses these to auto-generate the MCP tool schema sent to the client. Without them, the LLM receives no parameter descriptions and cannot use the tools reliably. This is the primary schema mechanism in FastMCP. | Low — mechanical change, no logic involved | Missing. Parameters are bare `str`, `int`, etc. |
| Consistent try-except with `ctx.error()` / `ctx.info()` in all tool bodies | Tools that throw unhandled exceptions produce opaque MCP protocol errors. The MCP client (Claude, Cursor) may hang or show cryptic errors. Production pattern: catch, log via `ctx`, return a structured error string. | Low-Medium — each tool needs a wrapping pattern | Missing. Tools have no error handling. |
| `logging` module with configurable level | MCP servers run as subprocesses. Operators need a way to see what the server is doing without dumping noise to stdout (which corrupts the MCP stdio wire format). `logging` to stderr with level controlled by `--verbose` is the standard pattern. | Low — add `logging.basicConfig` + propagate to CLI flag | Missing. No logging at all. |
| `argparse` CLI with `--verbose` flag and credential override args | Users who can't or don't want to set env vars need a CLI fallback. `--verbose` is the de-facto way to enable debug logging. The pattern: `--verbose` sets `logging.INFO`, default is `logging.WARN`. Credential args must fall back to env vars so both paths work. | Low — 20 lines of argparse, verified in pycti-mcp | Missing. `main()` has no CLI. |
| `src/` layout (`src/altr_mcp/`) | Python packaging best practice since PEP 517. Prevents test runs from importing the local directory instead of the installed package. Required to catch "works locally, broken after install" bugs. Hatchling supports it with no config change. | Low-Medium — directory move + update pyproject.toml paths | Missing. Package is at repo root. |
| Multi-Python CI test matrix (3.11, 3.12, 3.13) | `requires-python = ">=3.11"` is a claim to users. Verifying it requires actually running the build on each version. Users on Python 3.13 will report broken installs if this isn't tested. | Low — add `strategy.matrix.python-version` to existing workflow | Missing. No test jobs at all. |
| `uv build` + `--help` smoke test in CI | Confirms the package builds and the entry point resolves. Costs ~20 seconds in CI and catches import errors, missing dependencies, and broken entry point configurations before they reach PyPI. | Low — one workflow step | Missing. |
| MCP Inspector schema validation (`tools/list` check against golden file) | Confirms all 20+ tools are registered with correct names after refactoring. This is the primary regression guard when splitting `server.py` into modules. The pycti-mcp pattern (npx @modelcontextprotocol/inspector --cli | jq | diff tools_list.txt) is proven and costs ~30 seconds in CI. | Low-Medium — requires Node.js setup step + golden file | Missing. |
| Gated publish (publish only after all test jobs pass) | Publishing a broken package to PyPI is not reversible (the version is burned). The gate pattern using `lewagon/wait-on-check-action` or `needs:` job dependencies ensures the test matrix must green before any upload. | Low — `needs: [test-matrix]` in workflow | Missing. `publish-pypi` depends only on `build`, not on tests. |
| Tag/version consistency check in publish workflow | Pushing `v0.2.0` while `pyproject.toml` says `0.1.0` publishes the wrong version. The current workflow warns but does not fail. Should hard-fail if versions don't match. | Low — change `WARNING` to `exit 1` in existing step | Partial. Currently a warning, not a failure. |

---

## Differentiators

Features that distinguish a well-maintained, discoverable MCP server from a functional-but-rough one. Not required for basic operation, but valued by users and increases adoption.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Tool modularization: one module per logical group under `altr_tools/` | Makes the codebase navigable. Adding a new ALTR feature means creating one file, not scrolling a 900-line file. Matches the pycti-mcp `pycti_tools/` pattern exactly. Dynamic loading via `__all__` + `importlib.import_module` means the server file never changes when tools are added. | Medium — requires splitting 899 lines into ~5-8 modules and wiring dynamic loading | Defined in PROJECT.md as the target. Groups: `policy`, `tag`, `snowflake`, `classification`, `database`, `rules` map naturally to existing utils. |
| MCP tool annotations (`read_only_hint`, `destructive_hint`, `idempotent_hint`) | MCP spec 2025-03-26 added annotations. Claude and Cursor read `read_only_hint` to decide whether to show confirmation prompts. Marking `get_*` tools as `read_only_hint=True` and `create_*`/`add_*` tools as `destructive_hint=True` improves UX for users who want human-in-the-loop confirmation on write operations. | Low — one annotation dict per tool, set at `@mcp.tool()` registration | Not in pycti-mcp (added after its last update). FastMCP supports via `annotations=` kwarg. |
| Expanded README: tool reference with inputs/outputs and `<details>` blocks | The pycti-mcp README pattern of `<details><summary>Tool Name</summary>` collapsible sections makes 20+ tools browsable on GitHub without overwhelming the page. Each block documents: tool name, inputs with types, what it returns, typical workflow position. | Medium — documentation work, no code | Current README has no tool reference. |
| Multi-client config examples in README: Claude Desktop, Cursor, mcp-hub, VSCode | Users copy-paste MCP config blocks. Having configs for all four major clients in the README reduces support burden and increases adoption. Include both `uvx altr-mcp@latest` (no-install) and `altr-mcp` (installed) variants. | Low — documentation only | Current README has only Claude Desktop / Cursor basics. Missing mcp-hub and VSCode. |
| `uvx altr-mcp@latest` as the primary invocation in docs | `uvx` runs without a global install, always uses the latest version, and avoids PATH issues with Claude Desktop on macOS. Positioning this as the primary install path reduces user friction. It works today — the docs just don't foreground it. | Low — documentation positioning change | README mentions `uvx altr-mcp` but doesn't emphasize `@latest`. |
| Credential override via CLI args (`--key`, `--secret`, `--org`) | Allows use in environments where setting env vars is awkward (e.g., mcp-hub's `cmd` injection, scripted testing). The pycti-mcp pattern: CLI args take precedence, env vars are the fallback default. This is already standard in the FastMCP ecosystem. | Low — add args to argparse, thread into `Creds` class | Not implemented. `Creds` reads only from env. |
| `tests/tools_list.txt` golden file committed to repo | Serves as documentation (lists all registered tool names) and as a CI gate. When a tool is renamed or accidentally dropped, the diff catches it immediately. Side benefit: contributors see at a glance what tools exist. | Low — create file, populate with 20+ tool names sorted | Not present. Needs to be created alongside CI validation step. |
| TestPyPI publish step before production PyPI | Catching packaging errors (missing files, bad metadata) at TestPyPI before burning the production version number. The pycti-mcp pattern publishes to TestPyPI first in the same workflow run. | Low — add `uv publish --index testpypi` step before production publish | Not present in current workflow. |

---

## Anti-Features

Things to deliberately not build in this milestone. Either out of scope, counterproductive, or solving problems that don't exist yet.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| SSE / streamable-HTTP transport | PROJECT.md explicitly defers remote transport. Adding it now introduces a new credential management surface (port exposure, auth tokens) that distracts from the core productization work. Users running altr-mcp are local developers using Claude Desktop or Cursor — all of which use stdio. | Keep `mcp.run(transport='stdio')`. Note SSE is deferred in README under a "Coming soon" or "Future" section if desired. |
| Plugin extensibility / user-authored tools | ALTR tools are internal. There's no user community writing custom tools against the altr-mcp framework. Adding plugin docs creates maintenance burden with zero addressable audience right now. | Document the internal `altr_tools/` module structure in CONTRIBUTING.md so internal developers can add tools, but don't market it as a plugin system. |
| Docker / OCI image | PROJECT.md defers this. Docker is useful for remote/SSE deployments, which are also deferred. Building a Docker image for a stdio server adds no value. | Note it as a future milestone item if SSE is ever enabled. |
| Build backend switch to `uv_build` | `hatchling` is already working. `uv_build` is the pycti-mcp choice but it is not universally better — hatchling has more ecosystem tooling (hatch version bump) and is already configured correctly. Switching creates a non-zero chance of regression with no benefit. | Keep `hatchling`. Document this decision in KEY DECISIONS (already in PROJECT.md). |
| `npm` wrapper / npx invocation | altr-mcp is Python-only. The `uvx` invocation path already provides a zero-install experience equivalent to `npx`. Adding an npm wrapper for a Python package is unnecessary complexity. | Use `uvx altr-mcp@latest` as the zero-install path in all docs. |
| Pytest unit tests for tool logic | ALTR API calls and Snowflake queries cannot be usefully unit-tested without either mocking the entire ALTR API or running against a live instance. The value is low relative to the cost of maintaining mocks. The CI smoke test (build + `--help` + `tools/list` schema check) provides the critical regression coverage. | Rely on the MCP Inspector schema validation as the primary automated test. Add unit tests only if a specific bug requires regression coverage. |
| Version pinning of transitive dependencies in `pyproject.toml` | MCP servers are installed into user environments alongside many other packages. Over-constraining transitive deps causes resolution failures. `fastmcp>=2.x`, `httpx>=0.28`, etc. with lower bounds only is correct. | Keep current loose lower-bound pinning. Only tighten if a specific incompatibility is discovered. |

---

## Feature Dependencies

```
src/ layout
  └── required before → Tool modularization (can't restructure modules without clean package boundaries)

Tool modularization
  └── required before → tests/tools_list.txt golden file (tool names must be stable)
  └── required before → MCP Inspector schema validation in CI (tests the final registered set)

argparse CLI (--verbose)
  └── required before → logging module (the --verbose flag controls the log level)

Annotated[Type, "description"] on all parameters
  └── required before → MCP tool annotations on @mcp.tool() (annotations are per-tool registration, not per-parameter — these are independent but both should land together for clean schema output)

MCP Inspector schema validation in CI (tools_list.txt diff)
  └── required before → Gated publish (the gate depends on this test job existing)

uv build + --help smoke test
  └── required before → Gated publish (part of the test matrix the gate waits on)
```

---

## MVP Recommendation

The "production-grade" milestone should deliver in this order:

**Phase 1 — Structural foundation (unblocks everything else):**
1. `src/` layout migration
2. Tool modularization with dynamic loading
3. `argparse` CLI with `--verbose` and credential overrides
4. `logging` module integration

**Phase 2 — Schema and error quality:**
5. `Annotated[Type, "description"]` on all tool parameters
6. Consistent try-except + `ctx.error()` / `ctx.info()` in all tools

**Phase 3 — CI hardening:**
7. Multi-Python test matrix (3.11, 3.12, 3.13)
8. `tests/tools_list.txt` golden file
9. MCP Inspector schema validation step
10. Gated publish (`needs: test-matrix`)
11. Tag/version consistency hard-fail

**Phase 4 — Documentation and discoverability:**
12. Tool reference section in README (`<details>` blocks per tool)
13. Multi-client config examples (Claude Desktop, Cursor, mcp-hub, VSCode)
14. MCP tool annotations (`read_only_hint`, `destructive_hint`)

**Defer:** TestPyPI step, SSE transport, Docker, plugin docs.

---

## Sources

- pycti-mcp reference implementation (local): `/Users/parker/altr-claude/mcp-publish/pycti-mcp/` — HIGH confidence (authoritative reference)
- altr-mcp-server current codebase (local): `/Users/parker/altr-claude/mcp-publish/altr-mcp-server/` — HIGH confidence (ground truth)
- FastMCP Context docs (gofastmcp.com/servers/context) — MEDIUM confidence (WebSearch verified, consistent with pycti-mcp usage)
- FastMCP tool annotations support (`read_only_hint`, `destructive_hint`) — MEDIUM confidence (WebSearch, confirmed in FastMCP GitHub issue #289 and current gofastmcp.com/servers/tools)
- MCP Registry server.json schema requirements — MEDIUM confidence (WebSearch, Glama blog 2026-01-24 confirmed required fields)
- MCP Specification tool annotations (2025-03-26 version) — MEDIUM confidence (WebSearch from official modelcontextprotocol.io)
