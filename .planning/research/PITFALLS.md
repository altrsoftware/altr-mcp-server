# Domain Pitfalls

**Domain:** MCP server productization — Python package refactoring (src/ layout, tool modularization, CI testing, FastMCP)
**Researched:** 2026-03-06
**Confidence:** HIGH for hatchling/packaging pitfalls (verified via official docs + community issues), MEDIUM for FastMCP-specific pitfalls (verified via official docs), LOW for MCP Inspector CI specifics (WebSearch only)

---

## Critical Pitfalls

Mistakes that cause silent breakage or require full rewrites.

---

### Pitfall 1: hatchling src/ Layout — Package Installs as "src" Instead of "altr_mcp"

**What goes wrong:** Moving `altr_mcp/` to `src/altr_mcp/` without explicitly configuring hatchling causes the package to be installed at `site-packages/src/altr_mcp/` rather than `site-packages/altr_mcp/`. The `[project.scripts]` entry point `altr-mcp = "altr_mcp.server:main"` then fails with `ModuleNotFoundError` at runtime because the import path is wrong.

**Why it happens:** Hatchling's auto-detection walks the project root looking for Python packages. Without an explicit `[tool.hatch.build.targets.wheel]` `packages` directive, it finds `src/` as the top-level package and includes it verbatim.

**Consequences:** `uv build` succeeds and produces a wheel. `pip install altr-mcp` succeeds. `altr-mcp` CLI entry point fails immediately on first run. The failure is silent during the build step — it only surfaces at install+run time. CI that only runs `uv build` (like the current publish workflow) will not catch this.

**Prevention:** Add this to `pyproject.toml` before migrating:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/altr_mcp"]
```
This explicitly tells hatchling that `src/altr_mcp` should be installed as the `altr_mcp` package at the wheel root.

**Detection warning signs:**
- After `pip install -e .` or `uv sync`, `python -c "import altr_mcp"` works but running the entry point from a clean install fails
- `pip show altr-mcp` shows no installed files matching `altr_mcp/`
- `site-packages/src/` directory appears after install

**Phase:** src/ layout migration (Phase 1 of productization work)

---

### Pitfall 2: Entry Point Survives Build But Breaks After Install

**What goes wrong:** The current `pyproject.toml` has `altr-mcp = "altr_mcp.server:main"`. After the src/ migration, if `hatchling` is not configured (see Pitfall 1), the entry point string remains correct but the installed module path does not match it. This breaks `altr-mcp` for every end user who installs from PyPI.

**Why it happens:** Entry point strings are stored in wheel metadata verbatim. The packaging step does not validate that the referenced module path actually exists in the wheel.

**Consequences:** Users who `pip install altr-mcp` and then run `altr-mcp` get an import error. The PyPI release is broken. Fixing it requires a patch release (0.1.1 or similar) with a bump to pyproject.toml version — wasted release slot.

**Prevention:**
1. After building the wheel (`uv build`), unzip and inspect: `unzip -l dist/*.whl | grep altr_mcp` — confirm `altr_mcp/` appears at the wheel root, not `src/altr_mcp/`
2. Install from the wheel into a fresh virtualenv before publishing: `pip install dist/*.whl && altr-mcp --help`
3. Add a smoke test job in CI that installs the built wheel and verifies the entry point executes

**Detection warning signs:**
- `python -m altr_mcp.server` raises `ModuleNotFoundError` after clean install
- `which altr-mcp` resolves but running it fails immediately

**Phase:** src/ layout migration + CI smoke test (Phases 1 and 3)

---

### Pitfall 3: Tool Registration Regression During Modularization

**What goes wrong:** Splitting `server.py` into per-tool modules and loading them dynamically means the `@mcp.tool()` decorator must execute at import time. If a module is never imported, its tools are never registered. Silent failures: `altr-mcp` starts and responds to health checks, but `tools/list` returns fewer tools than expected.

**Why it happens:** The pycti-mcp pattern uses `__all__` in `tools/__init__.py` to enumerate modules, then imports them all at server startup. If a new tool module is added to `tools/` but not added to `__all__`, it simply never loads. No error is raised.

**Consequences:** Tools silently disappear from the MCP tool list. Claude or Cursor cannot call them. Downstream agents fail with "tool not found" errors that are hard to trace back to a missing import.

**Prevention:**
1. Use the `tools_list.txt` pattern from pycti-mcp: maintain a reference file listing every expected tool name. In CI, run `tools/list` via MCP Inspector CLI and diff against the reference file. A mismatch fails the build.
2. In `tools/__init__.py`, make `__all__` the single source of truth: every module file in the directory should be in `__all__`, and a unit test should assert `len(__all__) == len(glob("tools/*.py")) - 1` (excluding `__init__.py`).
3. Add an integration test that instantiates the FastMCP server and calls `mcp.list_tools()` directly (no subprocess needed), asserting exact count and names.

**Detection warning signs:**
- Tool count from `tools/list` differs between branches
- After adding a module, tool count is unchanged

**Phase:** Tool modularization + CI schema validation (Phases 1 and 3)

---

### Pitfall 4: FastMCP Import Path Divergence — mcp.server.fastmcp vs fastmcp

**What goes wrong:** The current server.py uses `from mcp.server.fastmcp import FastMCP` (the MCP SDK's bundled FastMCP 1.x). The standalone `fastmcp` package (jlowin/fastmcp) has evolved independently and is now at version 3.x with a different import path, different `Context` injection API, and new features. These two packages are not the same thing.

**Why it happens:** FastMCP 1.0 was incorporated into the official `mcp` SDK in 2024. The original author continued developing the standalone `fastmcp` package beyond what the SDK includes. As of 2025, the two have diverged significantly:
- `mcp.server.fastmcp.FastMCP` — SDK-bundled, stable, fewer features
- `fastmcp.FastMCP` — standalone package, more features, different Context API

**Consequences:** If any refactoring work adds `from fastmcp import ...` imports (e.g., following a tutorial or AI suggestion) while the `pyproject.toml` only declares `mcp[cli]>=1.17.0`, the server may fail to start in some environments. Worse, some Context methods work differently or have moved modules between the two packages.

**Prevention:**
- Pick one and be consistent. This project uses `mcp[cli]` as the declared dependency, so all imports should use `from mcp.server.fastmcp import FastMCP` and `from mcp.server.fastmcp import Context`.
- Add a linting rule (grep in CI) that flags `from fastmcp import` if the standalone package is not in `pyproject.toml` dependencies.
- If upgrading to standalone `fastmcp` is desired, treat it as a distinct upgrade task with a dedicated PR and test pass.

**Detection warning signs:**
- `ImportError: cannot import name 'Context' from 'mcp.server.fastmcp'` after someone adds a `ctx: Context` parameter
- Tests pass locally (where both packages are installed) but fail in CI (clean install)

**Phase:** Tool modularization / type annotations (Phase 1)

---

### Pitfall 5: FastMCP Context Object Is Request-Scoped — Cannot Carry State Across Tool Calls

**What goes wrong:** When adding `ctx: Context` parameters to tool functions for logging (`await ctx.info(...)`, `await ctx.error(...)`), developers sometimes store the context object in a module-level variable or class attribute to pass it to utility functions in `utils/`. This causes hard-to-debug errors: the context from a prior request is used, or the context is `None` because no request is active.

**Why it happens:** Each MCP request gets a fresh `Context` object. Attempting to store it outside the tool function scope violates the context lifecycle. The FastMCP docs explicitly state: "state or data set in one request will not be available in subsequent requests."

**Consequences:** Tools that store context globally appear to work during development (single sequential calls), but fail under concurrent use or in CI runners that spawn multiple requests. Errors are non-deterministic and hard to reproduce.

**Prevention:**
- Pass `ctx` as a parameter through the call chain to utility functions that need it, rather than storing it on a shared object.
- Utility functions in `utils/` that need logging should accept `ctx: Context | None = None` and guard with `if ctx:` — this keeps them testable without a live MCP context.
- The current `Auth = creds.get_auth()` module-level pattern is fine for credentials (static); do not apply the same pattern to Context.

**Detection warning signs:**
- Tests that call utility functions directly (without an MCP context) raise `RuntimeError` about missing context
- Intermittent failures when multiple tools execute near-simultaneously

**Phase:** Error handling / Context logging additions (Phase 1)

---

## Moderate Pitfalls

---

### Pitfall 6: pytest Cannot Find altr_mcp After src/ Migration Without pythonpath Config

**What goes wrong:** After moving to `src/altr_mcp/`, running `uv run pytest` or `python -m pytest` raises `ModuleNotFoundError: No module named 'altr_mcp'` even though `uv sync` completed successfully. This is a well-documented uv + pytest + src-layout interaction.

**Why it happens:** pytest adds the project root to `sys.path` by default, not `src/`. Without an editable install or explicit `pythonpath` configuration, Python finds no `altr_mcp` package at the root.

**Prevention:** Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
```
This tells pytest to add `src/` to the path before running tests. Alternatively, `uv sync` with a properly configured `pyproject.toml` installs the package in editable mode, which also resolves this — but the explicit `pythonpath` is a safety net for environments where the editable install is not used.

**Phase:** CI testing setup (Phase 3)

---

### Pitfall 7: CI Publish Workflow Has No Test Gate — Currently Publishes Broken Builds

**What goes wrong:** The existing `.github/workflows/publish-mcp.yml` runs `uv build` and publishes directly to PyPI with zero test execution. A broken refactor (wrong imports, missing tool registrations, bad entry point) can be published to PyPI before anyone notices.

**Why it happens:** The original workflow was scaffolded for publish-only with no test infrastructure yet.

**Consequences:** A broken PyPI release that affects every user who installs the package. The MCP Registry publication also runs on the same tag, so the registry points to the broken version. Recovery requires a hotfix release.

**Prevention:** Add a `test` job that runs before `publish-pypi`:
```yaml
publish-pypi:
  needs: [test]  # Add this
```
The test job should: (1) build the wheel, (2) install it into a clean virtualenv, (3) run `altr-mcp --help` or equivalent smoke test, (4) run pytest. The `publish-pypi` job only runs if `test` passes.

**Phase:** CI/CD gated publishing (Phase 3)

---

### Pitfall 8: MCP Inspector CLI Requires Node.js in CI — Not Available by Default

**What goes wrong:** Using `npx @modelcontextprotocol/inspector --cli` in GitHub Actions requires Node.js to be installed. Ubuntu runners have Node.js available, but specific version requirements for the Inspector may not be met, causing `npx` to download a large package on every CI run (slow) or fail silently when the version is mismatched.

**Why it happens:** The MCP Inspector is a Node.js application distributed as an npm package. Python CI workflows do not typically include Node.js setup steps.

**Prevention:**
- Use `actions/setup-node@v4` before any `npx` step in CI.
- Alternatively, implement tool list validation using Python directly: instantiate `FastMCP`, call `mcp.list_tools()` in a test script without the Node.js inspector. This is simpler and avoids the Node.js dependency entirely.
- The pycti-mcp approach uses a flat `tools_list.txt` diff against the output of `npx @modelcontextprotocol/inspector` — if adopting this, pin the inspector version to avoid version drift.

**Phase:** CI schema validation (Phase 3)

---

### Pitfall 9: PyPI Package Name "altr-mcp" — Already Claimed, Cannot Be Changed

**What goes wrong:** The package name `altr-mcp` is already published on PyPI (by this project). This is actually the desired state — but it creates a constraint: the package name, import name (`altr_mcp`), and entry point (`altr-mcp`) must not change. Any refactoring that renames the package directory or import path will break existing user installations silently (they can still import the old version, but upgrading to the new version breaks their scripts).

**Why it happens:** PyPI names are globally unique and permanent. Renaming requires deprecating the old name and publishing under a new name.

**Prevention:**
- The `src/` migration must preserve the import name: `src/altr_mcp/` not `src/altr-mcp/` or `src/altrmcp/`.
- After migration, run `python -c "import altr_mcp; print(altr_mcp.__file__)"` and verify it resolves to `site-packages/altr_mcp/`, not `site-packages/src/altr_mcp/`.
- The entry point string `altr_mcp.server:main` must remain unchanged after modularization (the `main()` function in `server.py` must still exist and still call `mcp.run()`).

**Phase:** src/ layout migration (Phase 1) — this is a backward-compatibility constraint on all phases

---

### Pitfall 10: Dynamic Tool Loading and the Global Auth Object

**What goes wrong:** Currently, `server.py` constructs a module-level `Auth` object from environment variables at import time (`creds = Creds(); Auth = creds.get_auth()`). When tools are split into separate modules that import `Auth` from `server.py`, a circular import arises: `server.py` imports tool modules, tool modules import `Auth` from `server.py`.

**Why it happens:** Module-level initialization that depends on other modules creates import-order coupling. Python's import system cannot resolve circular imports unless one side uses a lazy import or a shared state module.

**Prevention:** Extract `Auth` and `Creds` into a dedicated `altr_mcp/auth.py` (or `altr_mcp/config.py`) module that neither `server.py` nor tool modules import from each other — both import from `auth.py`. The dependency graph becomes: `server.py` → `tools/*.py` → `auth.py`, with no cycle.

**Detection warning signs:**
- `ImportError: cannot import name 'Auth' from partially initialized module 'altr_mcp.server'`
- Server starts but some tools have `Auth = None`

**Phase:** Tool modularization (Phase 1)

---

## Minor Pitfalls

---

### Pitfall 11: Annotated Type Annotations Change Tool Schema Unexpectedly

**What goes wrong:** Migrating from plain type annotations (`policy_id: str`) to `Annotated[str, "description"]` changes how FastMCP generates the JSON schema for tool parameters. If the description string in `Annotated` does not match what was previously in the docstring, the MCP client (Claude/Cursor) may interpret the parameter differently.

**Prevention:** When adding `Annotated` annotations, preserve the exact parameter description from the existing docstring `Args:` section. The `tools_list.txt` diff in CI will catch schema changes — treat any unexpected diff as a regression, not just a missing tool.

**Phase:** Type annotations work (Phase 1)

---

### Pitfall 12: Python 3.13 Compatibility — Type Annotation Syntax Changes

**What goes wrong:** The CI matrix targets Python 3.11, 3.12, and 3.13. Some newer type annotation syntax (e.g., `X | Y` union syntax) is valid in 3.10+ but behaves differently when used at runtime in older Python versions. FastMCP uses type annotations at runtime for schema generation — invalid annotations crash tool registration.

**Prevention:** Stick to `Optional[X]` or `Union[X, Y]` from `typing` for parameters that need to support None, rather than `X | None` bare syntax. Test the full tool list on 3.11 in CI (the minimum supported version), not just 3.13.

**Phase:** CI testing / type annotations (Phases 1 and 3)

---

### Pitfall 13: MCP Registry Version Not Updated Before Publish

**What goes wrong:** The current workflow updates `server.json` version in CI from the git tag. If the version in `pyproject.toml` does not match the git tag (e.g., tag is `v0.2.0` but `pyproject.toml` still says `0.1.0`), the workflow logs a WARNING but does not fail. PyPI gets the wheel built from `pyproject.toml` (version 0.1.0), but the MCP Registry entry points to version 0.2.0 — a mismatch.

**Prevention:** Change the version check step from a warning to a hard failure:
```bash
if [ "$TAG_VERSION" != "$PYPROJECT_VERSION" ]; then
  echo "ERROR: tag/pyproject.toml version mismatch"
  exit 1
fi
```

**Phase:** CI/CD (Phase 3)

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| src/ layout migration | Package installs as "src" not "altr_mcp" (Pitfall 1) | Add `[tool.hatch.build.targets.wheel] packages = ["src/altr_mcp"]` first |
| src/ layout migration | Entry point breaks on clean install (Pitfall 2) | Wheel inspection + clean-install smoke test before any publish |
| Tool modularization | Circular import with Auth object (Pitfall 10) | Extract `auth.py` before splitting tools |
| Tool modularization | Tools silently drop from registry (Pitfall 3) | tools_list.txt diff in CI before any other work |
| Type annotations | FastMCP import path divergence (Pitfall 4) | Enforce `from mcp.server.fastmcp import` consistently |
| Context logging | Context stored outside request scope (Pitfall 5) | Pass ctx through call chain; utils accept `ctx: Context | None = None` |
| CI setup | pytest ModuleNotFoundError with src layout (Pitfall 6) | Add `pythonpath = ["src"]` to `[tool.pytest.ini_options]` |
| CI setup | Inspector requires Node.js (Pitfall 8) | Use Python-native tool list check instead |
| Publish gate | No test gate on publish (Pitfall 7) | Add `needs: [test]` to `publish-pypi` job before first refactor release |
| Publish gate | Version mismatch tag vs pyproject.toml (Pitfall 13) | Harden version check to exit 1 |

---

## Sources

- Hatchling src/ layout issue (package installs as "src"): [pypa/hatch Discussion #1051](https://github.com/pypa/hatch/discussions/1051)
- Hatchling build configuration reference: [Hatch Build Configuration](https://hatch.pypa.io/latest/config/build/)
- FastMCP Context documentation: [FastMCP — Context](https://gofastmcp.com/servers/context)
- FastMCP server composition (mount/prefix): [FastMCP — Server Composition](https://gofastmcp.com/servers/composition)
- pycti-mcp tools_list.txt pattern: [ckane/pycti-mcp on GitHub](https://github.com/ckane/pycti-mcp)
- MCP Inspector CLI mode: [Model Context Protocol — Inspector](https://modelcontextprotocol.io/docs/tools/inspector)
- pytest pythonpath with src layout: [pytest import mechanisms](https://docs.pytest.org/en/stable/explanation/pythonpath.html)
- uv + pytest src layout issues: [uv issue #9291](https://github.com/astral-sh/uv/issues/9291)
- GitHub Actions gated PyPI publish: [Python Packaging User Guide — Publishing with GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- FastMCP modular tools discussion: [jlowin/fastmcp Discussion #948](https://github.com/jlowin/fastmcp/discussions/948)
