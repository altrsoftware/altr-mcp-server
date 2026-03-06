# Project Research Summary

**Project:** altr-mcp
**Domain:** Production Python MCP server — upgrade from functional prototype to published PyPI package
**Researched:** 2026-03-06
**Confidence:** HIGH

## Executive Summary

The altr-mcp server is a functional MCP tool server (20+ tools, working ALTR API integration) that fails to meet the standards expected of a published PyPI package. The recommended upgrade path is a four-phase productization: structural refactoring first (src/ layout, tool modularization, credentials extraction), followed by schema and error quality improvements, then CI hardening, and finally documentation polish. This ordering is non-negotiable — each phase has hard technical dependencies on the previous one, particularly the src/ layout migration which changes import paths and must precede all modularization work.

The primary model is the pycti-mcp reference implementation, a directly inspectable local codebase using identical technology choices (FastMCP via `mcp[cli]`, hatchling, uv, argparse, stdlib logging, Annotated type annotations). All recommended patterns are proven and observable in that reference, not derived from documentation alone. The key conservative decision is to remain on `mcp[cli]` (bundled FastMCP 1.x) rather than migrating to standalone `fastmcp` 3.x, which has breaking constructor changes and would compound refactoring risk unnecessarily.

The critical risks in this upgrade are packaging-level silent failures: a misconfig of hatchling's src/ layout produces wheels that install silently but fail at runtime; dynamic tool loading can drop tools without raising errors; and the current publish workflow has no test gate, meaning a broken refactor can reach PyPI before detection. These risks are fully preventable with known mitigations (explicit hatchling package directive, tools_list.txt CI diff, gated publish job), but all three mitigations must be in place before any new PyPI release is cut.

---

## Key Findings

### Recommended Stack

The stack requires no new production dependencies — all changes are layout, modularization, and CI. The existing `mcp[cli]>=1.17.0` dependency provides FastMCP with full support for `Annotated[Type, "description"]`, `Context`, tool decorators, and stdio transport. Python 3.11-3.13 is the target matrix. hatchling is the build backend (explicitly retained per PROJECT.md decision). uv handles CI build and publish via PyPI OIDC with no stored tokens.

**Core technologies:**
- `mcp[cli]` 1.17.0: MCP server framework (bundled FastMCP 1.x) — already in use, no migration risk, supports all required patterns
- Python 3.11/3.12/3.13: runtime matrix — claimed in pyproject.toml, must be verified in CI
- hatchling: build backend — already configured, keep over uv_build (explicit PROJECT.md decision)
- uv: package manager and CI build runner — 10-35x faster than pip, handles OIDC publish
- argparse (stdlib): CLI argument parsing — zero dependency cost, sufficient for `--verbose` and credential overrides
- logging (stdlib): server-level logging — integrates correctly with MCP SDK, must be initialized before `FastMCP()` instantiation

The one technology watch item: standalone `fastmcp` 3.x has diverged from `mcp.server.fastmcp` with breaking constructor changes. Do not mix import paths. If migration to standalone fastmcp is desired later, treat it as a separate dedicated milestone.

### Expected Features

The research identified ten table-stakes features (currently absent) and eight differentiators. The ordering and grouping from FEATURES.md is the definitive guide.

**Must have (table stakes):**
- `Annotated[Type, "description"]` on all tool parameters — without this, the LLM receives no parameter descriptions and cannot use tools reliably
- Consistent try-except with `ctx.error()` / `ctx.info()` in all tool bodies — bare exceptions produce opaque MCP protocol errors
- `logging` module with configurable level via `--verbose` — MCP servers run as subprocesses; logging to stderr is the only debug surface
- `argparse` CLI with `--verbose` and credential override args — users need both env var and CLI credential paths
- `src/` layout migration — Python packaging best practice; prevents import-before-install bugs
- Multi-Python CI test matrix (3.11, 3.12, 3.13) — required to honor `requires-python = ">=3.11"` claim
- `uv build` + `--help` smoke test in CI — catches broken entry points before PyPI
- MCP Inspector schema validation (`tools/list` diff against golden file) — primary regression guard for tool count during modularization
- Gated publish (publish only after test matrix passes) — current workflow publishes broken builds
- Tag/version consistency hard-fail (currently a warning only)

**Should have (differentiators):**
- Tool modularization: one module per domain under `altr_tools/` with dynamic loading
- MCP tool annotations (`read_only_hint`, `destructive_hint`) — improves UX for human-in-the-loop confirmation on write operations
- Expanded README with `<details>` collapsible tool reference sections
- Multi-client config examples (Claude Desktop, Cursor, mcp-hub, VSCode)
- `uvx altr-mcp@latest` as the primary no-install invocation in docs
- `tests/tools_list.txt` golden file committed to repo
- TestPyPI publish step before production PyPI

**Defer (v2+):**
- SSE / streamable-HTTP transport — PROJECT.md explicit deferral
- Docker / OCI image — only relevant for remote transport
- Plugin extensibility / user-authored tools — no addressable audience
- Build backend migration to uv_build
- pytest unit tests for tool logic (ALTR API mocking is a separate concern)

### Architecture Approach

The target architecture transforms a 900-line monolithic `server.py` into a layered structure: `server.py` handles only FastMCP initialization, argparse, and a dynamic tool loader loop; `credentials.py` owns all auth concerns; `altr_tools/` contains one module per domain with a `tool_init()` factory pattern; and `utils/` remains as raw API client code. The five tool domains map 1:1 with existing `utils/` modules (policies, tags, classification, databases, snowflake), making the migration mechanical rather than creative. A critical fix is embedded in this work: `utils/classification.py` uses synchronous `requests.get()` inside an async context — this blocks the event loop and must be replaced with `httpx.AsyncClient`.

**Major components:**
1. `src/altr_mcp/server.py` — FastMCP instance, argparse CLI, dynamic loader loop (`importlib` over `altr_tools.__all__`), `main()` entry point
2. `src/altr_mcp/credentials.py` — `Creds` class, `build_auth(key_override, secret_override)`, `get_org_id()`, `load_dotenv()` — separated from server.py to eliminate circular imports and enable CLI credential overrides
3. `src/altr_mcp/altr_tools/` — domain modules (`policies.py`, `tags.py`, `classification.py`, `databases.py`, `snowflake.py`), each exposing `tool_init(auth, **kwargs)` that returns a list of tool functions and captures auth in module-level `ToolConfig`
4. `src/altr_mcp/utils/` — unchanged raw ALTR API clients and Snowflake connector helpers
5. `tests/tools_list.txt` — golden file of sorted tool names, diff'd in CI via MCP Inspector

### Critical Pitfalls

1. **Hatchling src/ layout installs as "src" without explicit directive** — add `[tool.hatch.build.targets.wheel] packages = ["src/altr_mcp"]` to pyproject.toml before moving any files; this pitfall produces a wheel that builds and installs silently but fails at runtime

2. **Dynamic tool loading drops tools silently** — modules in `altr_tools/` that are not in `__all__` are never loaded, no error raised; the `tools_list.txt` CI diff is the only guard against silent regressions during modularization

3. **Circular import when extracting auth from server.py** — current module-level `Auth = creds.get_auth()` in server.py creates circular dependency if tool modules try to import it; fix by extracting to `credentials.py` before splitting tool modules

4. **FastMCP import path divergence** — `from mcp.server.fastmcp import FastMCP` (SDK bundled, current) vs `from fastmcp import FastMCP` (standalone 3.x, different API); mixing these causes silent failures in CI clean installs; enforce consistent import path throughout

5. **Current publish workflow has no test gate** — `publish-pypi` job runs on tag with zero test execution; adding `needs: [test]` is mandatory before the next release

---

## Implications for Roadmap

All four research files independently converge on the same four-phase sequence. The ordering is driven by hard technical dependencies, not arbitrary grouping preference.

### Phase 1: Structural Foundation

**Rationale:** The src/ layout migration changes import paths for every subsequent file. Credentials extraction eliminates the circular import risk before tools are split. Tool modularization depends on stable package boundaries. All other phases depend on this work being complete and verified. This is the highest-risk phase (packaging pitfalls 1, 2, 10) and the one where mistakes silently reach production if CI is not also updated.

**Delivers:** A `src/`-layout package with clean module boundaries — `credentials.py`, `altr_tools/` with five domain modules, `server.py` as a loader-only orchestrator, argparse CLI, stdlib logging. Server behavior is identical to current; no tool logic changes.

**Addresses (from FEATURES.md table stakes):** src/ layout, argparse CLI, logging module, tool modularization

**Avoids:** Pitfall 1 (hatchling src/ misconfiguration), Pitfall 2 (entry point breaks on clean install), Pitfall 10 (circular auth import), Pitfall 4 (FastMCP import divergence)

**Build order within phase:**
1. Add hatchling `packages = ["src/altr_mcp"]` directive to pyproject.toml
2. Move `altr_mcp/` to `src/altr_mcp/` and verify `uv build` + clean install
3. Extract `credentials.py` and verify server starts
4. Create `altr_tools/` modules with `tool_init()` factories (move tool functions, not logic)
5. Refactor `server.py` to dynamic loader + argparse + logging
6. Fix `utils/classification.py` sync-in-async (`requests` → `httpx.AsyncClient`)
7. Verify: MCP Inspector tool list matches current, CLI flags work

**Research flag:** LOW — all patterns are directly verified in pycti-mcp reference; no additional research needed

### Phase 2: Schema and Error Quality

**Rationale:** `Annotated[Type, "description"]` annotations and consistent error handling are independent of structural changes, but must follow Phase 1 because the annotations must be applied per-module (the module structure must be stable first). These changes are the primary quality improvement visible to LLM clients using the server.

**Delivers:** All 20+ tool parameters annotated with descriptions; consistent try-except + `ctx.error()` / `ctx.info()` in every tool body; MCP tool annotations (`read_only_hint`, `destructive_hint`) on all tools.

**Addresses (from FEATURES.md table stakes):** Annotated type annotations, consistent error handling. Also delivers: MCP tool annotations (differentiator)

**Avoids:** Pitfall 5 (Context stored outside request scope), Pitfall 11 (annotation changes schema unexpectedly — preserve docstring descriptions verbatim), Pitfall 12 (Python 3.13 annotation syntax — use `Optional[X]` not `X | None`)

**Research flag:** LOW — patterns are mechanical and reference implementation is available

### Phase 3: CI Hardening

**Rationale:** CI changes should follow structural and quality work, not precede it. The MCP Inspector tool list validation depends on a stable modular structure (Phase 1). The gated publish depends on the test job existing. The multi-Python matrix depends on the package being installable without errors. This phase converts CI from a publish-only workflow into a verified, gated release pipeline.

**Delivers:** Multi-Python test matrix (3.11, 3.12, 3.13); `tests/tools_list.txt` golden file; MCP Inspector schema validation in CI; gated publish (`needs: [test]`); version/tag hard-fail; `[tool.pytest.ini_options] pythonpath = ["src"]` for future test compatibility.

**Addresses (from FEATURES.md table stakes):** Multi-Python matrix, smoke test, MCP Inspector validation, gated publish, tag/version hard-fail

**Avoids:** Pitfall 7 (no test gate on publish), Pitfall 3 (tool registration regression), Pitfall 8 (MCP Inspector requires Node.js — use `actions/setup-node@v4`), Pitfall 13 (version mismatch), Pitfall 6 (pytest ModuleNotFoundError with src layout)

**Research flag:** LOW for gating and matrix patterns. MEDIUM for `lewagon/wait-on-check-action` (open Ruby 2.7 compatibility issue — monitor or substitute Python-native tool list check)

### Phase 4: Documentation and Discoverability

**Rationale:** Documentation is the last phase because it references stable tool names, accurate CLI flags, and verified client configuration snippets — all of which are outputs of Phases 1-3. Writing docs before the structure is stable requires rewriting them after.

**Delivers:** Tool reference section in README (`<details>` collapsible blocks per tool with inputs/outputs); multi-client config examples (Claude Desktop, Cursor, mcp-hub, VSCode) including both `uvx altr-mcp@latest` and installed variants; `uvx altr-mcp@latest` positioned as the primary invocation path.

**Addresses (from FEATURES.md differentiators):** Tool reference docs, multi-client configs, uvx positioning

**Research flag:** LOW — documentation work with no technical unknowns

### Phase Ordering Rationale

- Phase 1 before Phase 2: import paths must be stable before per-function annotation work begins; annotating a function that will be moved creates double-touch
- Phase 1 before Phase 3: CI schema validation requires the final tool set to be registered in the modular structure
- Phase 2 before Phase 3: the tool schema produced by annotations is what the CI diff validates; annotations must be applied first so the golden file captures the final schema
- Phase 3 before Phase 4: accurate docs require CI to confirm the package is installable on all platforms before publishing client configuration examples

### Research Flags

Phases likely needing deeper research during planning:
- None identified. All patterns are directly available in the pycti-mcp reference implementation or well-documented official sources. No external API research, no niche library integrations.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Python packaging with hatchling src/ layout is well-documented; pycti-mcp is a direct model
- **Phase 2:** FastMCP Annotated parameters and Context usage are documented and observable in pycti-mcp
- **Phase 3:** GitHub Actions test matrix and gated publish are standard patterns; MCP Inspector usage observed in pycti-mcp CI
- **Phase 4:** Documentation is content work, not technical research

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | `mcp[cli]` version from uv.lock; uv/hatchling from official docs; all patterns verified in pycti-mcp |
| Features | HIGH | Primary sources: direct codebase inspection of current altr-mcp-server and pycti-mcp reference; gap analysis is ground-truth |
| Architecture | HIGH | All patterns directly inspected in pycti-mcp — not inferred from docs. Component boundaries and data flow are observable |
| Pitfalls | HIGH (packaging), MEDIUM (FastMCP specifics), LOW (MCP Inspector CI) | Hatchling pitfalls verified via official docs + community issues; FastMCP pitfalls from docs + GitHub issues; Inspector CI from WebSearch only |

**Overall confidence:** HIGH

### Gaps to Address

- **`lewagon/wait-on-check-action` stability:** Open Ruby 2.7 compatibility issue (#98). Validate in Phase 3 CI setup; fallback is Python-native tool list validation without Node.js (simpler, avoids the dependency entirely)
- **FastMCP 3.0 migration path:** Not researched in detail — deliberately out of scope. If migration to standalone fastmcp is considered in a future milestone, full migration guide research is needed before starting
- **TestPyPI trusted publisher setup:** Publishing to TestPyPI via OIDC requires a separate trusted publisher configuration on TestPyPI (distinct from the production PyPI config). Verify this is configured before adding the TestPyPI step in Phase 3 or defer it
- **Annotated description quality:** The `Annotated[Type, "description"]` strings need to be written for all 20+ tool parameters. This is content work requiring domain knowledge of the ALTR API — factor in review time

---

## Sources

### Primary (HIGH confidence)
- pycti-mcp reference implementation (local): `/Users/parker/altr-claude/mcp-publish/pycti-mcp/` — architecture patterns, CI configuration, argparse CLI, tool modularization, tools_list.txt, Annotated usage
- altr-mcp-server current codebase (local): `/Users/parker/altr-claude/mcp-publish/altr-mcp-server/` — baseline state, existing utils structure, tool inventory
- [Hatchling build configuration](https://hatch.pypa.io/latest/config/build/) — src/ layout packaging directive
- [Python Packaging User Guide — src layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/) — layout rationale
- [uv in GitHub Actions — Astral docs](https://docs.astral.sh/uv/guides/integration/github/) — CI integration patterns

### Secondary (MEDIUM confidence)
- [FastMCP Tools docs](https://gofastmcp.com/servers/tools) — Annotated parameters, tool annotations
- [FastMCP Context docs](https://gofastmcp.com/servers/context) — ctx.info/error/debug, request-scoped lifecycle
- [FastMCP 3.0 GA announcement](https://www.jlowin.dev/blog/fastmcp-3-launch) — breaking changes, migration considerations
- [FastMCP logging conflict — python-sdk issue #1656](https://github.com/modelcontextprotocol/python-sdk/issues/1656) — logging.basicConfig before FastMCP() init
- [pypa/hatch Discussion #1051](https://github.com/pypa/hatch/discussions/1051) — package installs as "src" pitfall
- [lewagon/wait-on-check-action](https://github.com/lewagon/wait-on-check-action) — cross-workflow gating

### Tertiary (LOW confidence)
- [MCP Inspector CLI mode](https://modelcontextprotocol.io/docs/tools/inspector) — `--cli --method tools/list` syntax (WebSearch only, not directly executed)

---

*Research completed: 2026-03-06*
*Ready for roadmap: yes*
