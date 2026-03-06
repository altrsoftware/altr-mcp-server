# Technology Stack: Production-Grade Python MCP Server

**Project:** altr-mcp
**Researched:** 2026-03-06
**Research mode:** Ecosystem — upgrading existing FastMCP server to production quality

---

## Context

This is a stack research for an upgrade, not a greenfield project. The existing server uses `mcp[cli]` (the MCP Python SDK, which bundles FastMCP 1.x under `mcp.server.fastmcp`). The reference implementation (pycti-mcp) uses the standalone `fastmcp` package (2.10.x). These are different packages that have diverged.

---

## Critical Finding: Two FastMCP Packages

| Package | Import | Current Version | Notes |
|---------|--------|-----------------|-------|
| `mcp[cli]` | `from mcp.server.fastmcp import FastMCP` | 1.17.0 | Official SDK; bundles FastMCP 1.0 fork; what altr-mcp currently uses |
| `fastmcp` | `from fastmcp import FastMCP` | 3.1.0 (Mar 3, 2026) | Standalone, active development; 2.x was what pycti-mcp uses; 3.0 is GA |

**Recommendation: Stay on `mcp[cli]`** for this upgrade milestone. Rationale:

1. The PROJECT.md explicitly lists "keep hatchling build backend" and no build backend switch — same conservative logic applies here. Migrating to standalone fastmcp while refactoring 900-line server.py and restructuring the package layout creates unnecessary compounding risk.
2. `mcp.server.fastmcp.FastMCP` supports `Annotated[Type, "description"]`, `Context`, tool decorators, and `asyncio.run(mcp.run_stdio_async())` — all the patterns used in the upgrade work.
3. FastMCP 3.0 has breaking changes (constructor kwargs removed, state methods async, auth provider changes). Migrating is a separate milestone decision.
4. Confidence: MEDIUM (based on pycti-mcp's usage of standalone fastmcp and the FastMCP 3.0 migration notes — upgrading is feasible but scoped out of this milestone).

If standalone `fastmcp` is desired later, migration is documented: update import, address breaking constructor changes, update `mcp.server.fastmcp` to `fastmcp` in pyproject.toml dependencies.

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `mcp[cli]` | `>=1.17.0` (pinned to `1.17.0` in lockfile) | MCP server framework via bundled FastMCP | Already in use, stable, no migration cost; provides `FastMCP`, `Context`, stdio/SSE transports |
| Python | 3.11, 3.12, 3.13 | Runtime | `requires-python = ">=3.11"` matches current pyproject.toml; 3.13t (free-threaded) tested in pycti-mcp but not required here |

### Build System

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| hatchling | current (from PyPI) | Build backend | Already configured and working; `src/` layout is natively supported via `[tool.hatch.build.targets.wheel] packages = ["src/altr_mcp"]`; keep per PROJECT.md decision |
| uv | latest via `astral-sh/setup-uv@v7` | Package manager and build runner | `uv build` produces wheel + sdist in CI; `uv publish --trusted-publishing always` handles PyPI OIDC; 10-35x faster than pip |

**Do NOT switch to `uv_build` backend** — pycti-mcp uses it but PROJECT.md explicitly says to keep hatchling. uv_build is best for zero-config new projects; hatchling offers more control for existing setups.

### Package Layout

| Pattern | Implementation | Why |
|---------|---------------|-----|
| `src/` layout | Move `altr_mcp/` to `src/altr_mcp/` | Standard Python packaging best practice; prevents accidental import of un-installed package during dev/CI; official Python Packaging User Guide recommended approach |
| Tool modules | `src/altr_mcp/tools/__init__.py` with `__all__` | Matches pycti-mcp plugin pattern; `importlib.import_module` loop in server startup; each module exports a `tool_init()` or registers via decorator |

Update `pyproject.toml` for `src/` layout with hatchling:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/altr_mcp"]
```

### CLI Framework

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `argparse` | stdlib | CLI argument parsing | Standard library — no dependency added; pycti-mcp reference pattern; sufficient for `--verbose`, credential overrides; avoid `click` or `typer` (adds dependencies, overkill for a single entrypoint) |

Pattern from pycti-mcp (use directly):

```python
from argparse import ArgumentParser

def main():
    ap = ArgumentParser(description="Execute the ALTR MCP Server")
    ap.add_argument("-v", "--verbose", action="store_true", default=False,
                    help="Run in VERBOSE mode (INFO level). Default: off (WARN)")
    ap.add_argument("--mapi-key", default=os.getenv("MAPI_KEY", ""),
                    help="ALTR API key — also via MAPI_KEY env var")
    ap.add_argument("--mapi-secret", default=os.getenv("MAPI_SECRET", ""),
                    help="ALTR API secret — also via MAPI_SECRET env var")
    args = ap.parse_args()
```

### Logging

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `logging` | stdlib | Server-level logging | Standard library; no dependency; pycti-mcp reference pattern; configure at entrypoint, not in library code |
| `ctx.info()`, `ctx.error()`, `ctx.debug()` | FastMCP `Context` | In-tool MCP protocol logging | Sends log messages via MCP protocol to clients (Claude Desktop shows these); distinct from server-level logging |

**Critical:** Configure `logging` in `main()` before creating `FastMCP()` instance. FastMCP configures its own logging on initialization which can conflict — set the root logger level first. Known issue: FastMCP SDK version configures logging on `FastMCP()` init (GitHub issue #1656 on python-sdk). Pattern:

```python
if args.verbose:
    logging.basicConfig(level="INFO")
else:
    logging.basicConfig(level="WARN")

log = logging.getLogger(__name__)
mcp = FastMCP("altr")
```

**Do NOT use `structlog`, `loguru`, or other third-party loggers** — stdlib logging is what the reference implementation uses, it integrates correctly with the MCP SDK, and there is no benefit to adding a dependency here.

### Type Annotations

| Pattern | Implementation | Why |
|---------|---------------|-----|
| `Annotated[Type, "description"]` | `from typing import Annotated` (stdlib 3.11+) | Auto-generates MCP JSON schema from type annotations; FastMCP reads the string metadata as the parameter description; eliminates duplicating descriptions in docstrings |

Example (from pycti-mcp reference):

```python
from typing import Annotated

async def get_policy(
    policy_id: Annotated[str, "The ALTR policy UUID to retrieve"],
    ctx: Context,
) -> Annotated[dict, "Policy object with id, name, rules"]:
    ...
```

`typing.Annotated` is stdlib in Python 3.9+. No additional import from `typing_extensions` needed for Python 3.11+ target.

### Error Handling

| Pattern | Implementation | Why |
|---------|---------------|-----|
| `try/except` with `ctx.error()` + re-raise | Consistent across all tools | `ctx.error()` sends the error to the MCP client (visible in Claude Desktop); re-raise lets the framework surface it as a tool failure; pattern from pycti-mcp |

```python
try:
    result = await some_api_call()
    return result
except Exception as e:
    await ctx.error(f"Failed: {e}")
    raise
```

---

## CI/CD Stack

### GitHub Actions Tooling

| Tool | Version | Purpose | Why |
|------|---------|---------|-----|
| `astral-sh/setup-uv` | `@v7` | Install uv in CI | Official action; v7 is current (2025); auto-caches uv binary |
| `actions/setup-node` | `@v4` | Install Node.js for MCP Inspector | Required for `npx @modelcontextprotocol/inspector` |
| `actions/checkout` | `@v4` | Checkout code | Current version |
| `actions/upload-artifact` | `@v4` | Pass build artifacts between jobs | Required for separated build/publish jobs |
| `actions/download-artifact` | `@v4` | Consume build artifacts | Counterpart to upload |
| `pypa/gh-action-pypi-publish` | `release/v1` | Publish to PyPI via OIDC | Official PyPA action; handles OIDC token exchange; already in existing workflow |
| `lewagon/wait-on-check-action` | `@v1.4.0` | Gate publish on test matrix | Used by pycti-mcp; polls GitHub API until named check passes; needed because test matrix and publish are separate workflows |

**On gating across workflows:** GitHub's `needs:` keyword only gates within the same workflow file. Since tests run on push/PR and publish runs on tag, cross-workflow gating requires either `lewagon/wait-on-check-action` (pycti-mcp pattern) or the `workflow_run` event. Use `lewagon/wait-on-check-action@v1.4.0` to match the reference implementation — it is still actively maintained. Set `wait-interval: 30` to stay within GitHub API rate limits.

Confidence: MEDIUM — `lewagon/wait-on-check-action` has an open issue about Ruby 2.7 bundle compatibility (#98). Monitor for failures; the `workflow_run` event is a viable alternative if it breaks.

### MCP Schema Validation

| Tool | Version | Purpose | Why |
|------|---------|---------|-----|
| `@modelcontextprotocol/inspector` | `latest via npx -y` | Validate tool list in CI | `npx -y @modelcontextprotocol/inspector --cli --method tools/list <server>` outputs JSON; pipe through `jq -r '.tools[].name' \| sort \| diff` against committed `tests/tools_list.txt`; catches tool registration regressions |
| `jq` | system package | Parse inspector JSON output | Available on `ubuntu-latest` runners |

Pattern from pycti-mcp CI (adapt for altr-mcp):

```yaml
- name: Install Node.js for MCP Inspector
  uses: actions/setup-node@v4

- name: Validate tool list
  run: |
    npx -y @modelcontextprotocol/inspector --cli --method tools/list \
      uvx --from dist/altr_mcp-*.tar.gz altr-mcp \
      | jq -r '.tools[].name' | sort | diff -u ./tests/tools_list.txt -
```

This requires the server to be launchable without credentials for the inspector call to work — tools/list is answered before any tool is invoked. Credential absence during startup must not crash the server.

### Test Matrix

| Dimension | Values | Why |
|-----------|--------|-----|
| Python versions | 3.11, 3.12, 3.13 | Matches `requires-python = ">=3.11"` in pyproject.toml; catches version-specific issues |
| Trigger | push (all branches) and pull_request | Matches pycti-mcp pattern |
| Test steps | `uv build` then `uvx --from dist/*.tar.gz altr-mcp --help` then MCP Inspector tool list check | Build from sdist ensures install integrity; `--help` is the smoke test; tool list diff is the schema regression test |

**No pytest for this milestone.** The test pattern is: build, smoke test, schema validation. Unit testing individual tools requires mocking ALTR and Snowflake APIs — a separate milestone concern. The reference implementation (pycti-mcp) uses the same build+smoke+schema-diff pattern without pytest.

### Publishing

| Step | Implementation | Why |
|------|---------------|-----|
| PyPI OIDC | `uv publish --trusted-publishing always` | No tokens stored; OIDC token is ephemeral and workflow-scoped; requires `id-token: write` permission |
| MCP Registry | `mcp-publisher publish server.json` after `mcp-publisher login github-oidc` | Already in existing workflow; keep as-is |
| Version guard | Check `uv version --short` matches pushed tag before publishing | Prevents tag/version mismatch; pycti-mcp pattern |
| Gating | `lewagon/wait-on-check-action` waiting for each matrix Python version job | Publish does not run if any test job fails |

Current workflow uses `pypa/gh-action-pypi-publish` — can keep or migrate to `uv publish`. Both work with OIDC. `uv publish` is simpler and avoids a separate action dependency.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Build backend | hatchling | uv_build | Already working; PROJECT.md explicit decision to keep hatchling; no benefit justifies migration risk |
| FastMCP package | `mcp[cli]` (bundled) | `fastmcp` (standalone) | Standalone has 3.0 breaking changes; migration is scoped to a future milestone; bundled version supports all required patterns |
| CLI framework | `argparse` (stdlib) | `click`, `typer` | No dependencies added; sufficient for the use case; matches reference implementation |
| Logger | stdlib `logging` | `structlog`, `loguru` | Adds dependency; stdlib integrates correctly with MCP SDK; reference implementation uses stdlib |
| Test framework | build+smoke+schema-diff | pytest + mocked ALTR API | pytest mocking of external APIs is a separate concern; build-level testing is the correct scope for this milestone |
| Cross-workflow gating | `lewagon/wait-on-check-action` | `workflow_run` event | wait-on-check is simpler to configure and matches reference implementation; workflow_run has ordering edge cases |

---

## Installation Notes

No new production dependencies are added by this upgrade. All changes are:

- Layout reorganization (`src/` layout)
- Modularization (tools into subpackages)
- Adding `argparse`/`logging` patterns (stdlib, already available)
- CI workflow additions (GitHub Actions config only)

```toml
# pyproject.toml changes needed for src/ layout
[tool.hatch.build.targets.wheel]
packages = ["src/altr_mcp"]

# Add Python 3.13 classifier
"Programming Language :: Python :: 3.13",
```

```bash
# Dev: install from src/ layout
uv sync

# CI build command (unchanged)
uv build

# CI smoke test (using built sdist)
uvx --from dist/altr_mcp-*.tar.gz altr-mcp --help
```

---

## Confidence Assessment

| Area | Confidence | Basis |
|------|------------|-------|
| `mcp[cli]` version (1.17.0) | HIGH | uv.lock file in repo |
| `fastmcp` standalone version (3.1.0 as of Mar 2026) | HIGH | Multiple web sources including PyPI |
| FastMCP 3.0 breaking changes | MEDIUM | Blog posts and changelog; not verified against full upgrade guide |
| `astral-sh/setup-uv@v7` current | HIGH | Web search confirmed v7 is current |
| `lewagon/wait-on-check-action@v1.4.0` stability | MEDIUM | Active issue about Ruby 2.7 compatibility; functionally works per pycti-mcp usage |
| MCP Inspector CLI `--cli --method tools/list` syntax | HIGH | Directly observed in pycti-mcp workflow file |
| argparse vs click for CLI | HIGH | Pycti-mcp direct reference + standard Python practice |
| `src/` layout with hatchling | HIGH | Official Python Packaging User Guide; hatchling documentation |
| logging before FastMCP init required | MEDIUM | GitHub issue #1656 on python-sdk; workaround is well-documented |

---

## Sources

- pycti-mcp reference implementation: `/Users/parker/altr-claude/mcp-publish/pycti-mcp/` (local checkout, version 0.3.0)
- [uv in GitHub Actions — Astral docs](https://docs.astral.sh/uv/guides/integration/github/)
- [uv build backend stable — Python Developer Tooling Handbook](https://pydevtools.com/blog/uv-build-backend/)
- [src layout vs flat layout — Python Packaging User Guide](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
- [FastMCP 3.0 GA announcement](https://www.jlowin.dev/blog/fastmcp-3-launch)
- [FastMCP 3.0 What's New](https://www.jlowin.dev/blog/fastmcp-3-whats-new)
- [FastMCP Tools docs](https://gofastmcp.com/servers/tools)
- [FastMCP Client Logging docs](https://gofastmcp.com/servers/logging)
- [MCP Inspector — modelcontextprotocol.io](https://modelcontextprotocol.io/docs/tools/inspector)
- [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/)
- [lewagon/wait-on-check-action](https://github.com/lewagon/wait-on-check-action)
- [FastMCP logs logging conflict — python-sdk issue #1656](https://github.com/modelcontextprotocol/python-sdk/issues/1656)
- [FastMCP v2.12.5 Safety Pin release notes](https://github.com/jlowin/fastmcp/releases/tag/v2.12.5)
