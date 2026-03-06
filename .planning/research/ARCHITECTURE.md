# Architecture Patterns

**Domain:** Production Python MCP server — modular tool loading, src/ layout
**Researched:** 2026-03-06
**Confidence:** HIGH (primary source: direct inspection of pycti-mcp reference implementation at /Users/parker/altr-claude/mcp-publish/pycti-mcp and current altr-mcp-server at /Users/parker/altr-claude/mcp-publish/altr-mcp-server)

---

## Current State vs Target State

### Current layout (flat, monolithic)

```
altr-mcp-server/
├── altr_mcp/
│   ├── __init__.py          # empty
│   ├── server.py            # 900-line monolith: all 20+ tools + FastMCP init + Creds class + main()
│   └── utils/
│       ├── __init__.py
│       ├── api.py           # Generic httpx HTTP helper
│       ├── classification.py # ALTR classification API calls + formatting
│       ├── column.py        # Column-level helpers
│       ├── database.py      # ALTR database API calls
│       ├── policy.py        # ALTR policy/rules API calls + formatting
│       ├── snowflake.py     # Snowflake connector operations
│       └── tag.py           # ALTR tag API calls + formatting
├── pyproject.toml
└── server.json
```

Problem: `server.py` does everything — credential loading, FastMCP instantiation, tool registration, and 900 lines of tool implementations. Adding a new tool requires editing the same file as framework setup.

### Target layout (src/, modular tools, dynamic loading)

```
altr-mcp-server/
├── src/
│   └── altr_mcp/
│       ├── __init__.py
│       ├── server.py        # FastMCP init + dynamic tool loading loop + argparse + main()
│       ├── credentials.py   # Creds class, load_dotenv, env var access
│       ├── altr_tools/
│       │   ├── __init__.py  # __all__ = ["policies", "tags", "classification", "databases", "snowflake"]
│       │   ├── policies.py  # get_policies, create_policy, delete_policy, get_rules, add_rules, delete_rule
│       │   ├── tags.py      # get_tags, delete_tag, get_tag_values, connect_tag
│       │   ├── classification.py  # get_classifiers, create_classifier, delete_classifier,
│       │   │                      # get_collections, create_collection, delete_collection,
│       │   │                      # get_jobs, create_job, update_job_status, get_classification_report
│       │   ├── databases.py # get_databases, get_database_id
│       │   └── snowflake.py # create_snowflake_tags
│       └── utils/
│           ├── __init__.py
│           ├── api.py           # (unchanged — generic httpx helper)
│           ├── classification.py # (renamed: altr_classification_client.py or kept)
│           ├── database.py
│           ├── policy.py
│           ├── snowflake.py
│           └── tag.py
├── tests/
│   └── tools_list.txt       # sorted list of expected tool names, checked in CI
├── pyproject.toml           # entry: altr-mcp = "altr_mcp.server:main", packages = ["src/altr_mcp"]
└── server.json
```

---

## Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `server.py` | FastMCP instance, argparse CLI, dynamic tool loading loop, `main()` entry point | `altr_tools/__init__.__all__`, each tool module via `importlib`, `credentials.py` |
| `credentials.py` | `load_dotenv()`, `Creds` class (MAPI_KEY / MAPI_SECRET → httpx.BasicAuth), `ORG_ID` env access | Called by `server.py` at startup; auth object passed into each `tool_init()` |
| `altr_tools/__init__.py` | `__all__` list — the single source of truth for which tool modules exist | Read by `server.py` dynamic loader |
| `altr_tools/policies.py` | Tool functions for policy/rules domain; `tool_init(auth)` factory | `utils/policy.py`, FastMCP via `mcp.tool()` |
| `altr_tools/tags.py` | Tool functions for tag domain; `tool_init(auth)` factory | `utils/tag.py` |
| `altr_tools/classification.py` | Tool functions for classification jobs domain; `tool_init(auth, org_id)` factory | `utils/classification.py` |
| `altr_tools/databases.py` | Tool functions for database discovery; `tool_init(auth)` factory | `utils/database.py` |
| `altr_tools/snowflake.py` | Tool function for Snowflake tag creation; `tool_init(auth)` factory | `utils/snowflake.py` |
| `utils/api.py` | Generic async httpx HTTP helper; single reusable request function | All `utils/` domain modules |
| `utils/policy.py` | Raw ALTR policy API calls + response formatting | `utils/api.py` |
| `utils/tag.py` | Raw ALTR tag API calls + response formatting | `utils/api.py` |
| `utils/classification.py` | Raw ALTR classification API calls + response formatting | `utils/api.py` |
| `utils/database.py` | Raw ALTR database API calls | `utils/api.py` |
| `utils/snowflake.py` | Snowflake connector operations | snowflake-connector-python |

---

## Data Flow

### Startup flow

```
User runs: altr-mcp [--verbose] [--mapi-key KEY] [--mapi-secret SECRET]
     │
     ▼
server.py: main()
  1. argparse: parse --verbose, credential override flags
  2. logging.basicConfig(level=INFO if verbose else WARN)
  3. credentials.py: load_dotenv(), build Creds (httpx.BasicAuth), read ORG_ID
  4. FastMCP("altr") instance created
  5. Dynamic loader loop:
       for m in altr_tools.__all__:
           mod = importlib.import_module(f"altr_mcp.altr_tools.{m}")
           mcp.tool(mod.tool_init(auth=auth, org_id=org_id))
  6. mcp.run(transport='stdio')
```

### Per-tool-call flow (at runtime)

```
MCP client (Claude/Cursor) → stdio → FastMCP dispatcher
     │
     ▼
tool function (e.g., get_policies)
  - Tool function has closure over auth/org_id (captured at init)
  - Calls utils/policy.py make_altr_policy_request(params, auth)
     │
     ▼
  utils/api.py request(method, url, auth, params)
     │
     ▼
  httpx.AsyncClient → ALTR REST API (api.live.altr.com or ORG_ID.classification.live.altr.com)
     │
     ▼
  Response dict returned up the chain
     │
     ▼
  Tool function formats result → returns string to FastMCP → stdio to MCP client
```

---

## Patterns to Follow

### Pattern 1: tool_init() factory function

Each tool module exposes a `tool_init()` function that captures credentials in a closure and returns the tool function. The tool function itself is what gets registered with FastMCP.

```python
# src/altr_mcp/altr_tools/policies.py
from typing import Annotated
from fastmcp import Context
from altr_mcp.utils import policy


class ToolConfig:
    auth = None


async def get_policies(ctx: Context) -> str:
    """List all masking policies configured in your ALTR organization."""
    policies = await policy.make_altr_policy_request({}, ToolConfig.auth)
    formatted = policy.format_policies(policies)
    return "\n---\n".join(formatted)


async def create_policy(
    tag: Annotated[str, "Tag name (UPPERCASE) as returned by get_tags"],
    ctx: Context,
) -> str:
    """Create a masking policy for a specific tag."""
    return await policy.create_altr_policy({}, ToolConfig.auth, tag)


def tool_init(auth, **kwargs):
    ToolConfig.auth = auth
    return [get_policies, create_policy, delete_policy, get_rules, add_rules, delete_rule]
```

Key distinction from pycti-mcp: each altr_tools module owns multiple related tools (pycti-mcp has one tool per file because they are unrelated lookups). `tool_init` should return a list of functions, and the loader should call `mcp.tool()` on each.

### Pattern 2: Dynamic loader in server.py

```python
# src/altr_mcp/server.py
import altr_mcp.altr_tools
import importlib
import logging
from argparse import ArgumentParser
from fastmcp import FastMCP
from altr_mcp.credentials import build_auth, get_org_id


def main():
    ap = ArgumentParser(description="ALTR MCP Server")
    ap.add_argument("-v", "--verbose", action="store_true", default=False)
    ap.add_argument("--mapi-key", default=None, help="Override MAPI_KEY env var")
    ap.add_argument("--mapi-secret", default=None, help="Override MAPI_SECRET env var")
    args = ap.parse_args()

    logging.basicConfig(level="INFO" if args.verbose else "WARN")
    log = logging.getLogger(__name__)

    auth = build_auth(key_override=args.mapi_key, secret_override=args.mapi_secret)
    org_id = get_org_id()

    mcp = FastMCP("altr")

    for m in altr_mcp.altr_tools.__all__:
        mod = importlib.import_module(f"altr_mcp.altr_tools.{m}")
        try:
            tools = mod.tool_init(auth=auth, org_id=org_id)
            for tool_fn in tools:
                mcp.tool(tool_fn)
                log.info(f"Registered tool: {tool_fn.__name__}")
        except Exception as e:
            log.critical(f"Failed to load tools from altr_tools.{m}: {e}")
            raise e

    mcp.run(transport='stdio')
```

### Pattern 3: Annotated[Type, "description"] for parameters

Replace bare type annotations with `Annotated` to auto-generate MCP schema without duplicating descriptions in docstrings.

```python
# Before
async def add_rules(policy_id: str, masking_policy: int, role: str, tag_value: str) -> str:

# After
async def add_rules(
    policy_id: Annotated[str, "URL-encoded policy ID from get_policies"],
    masking_policy: Annotated[int, "Masking level (10000=none, 10001=full, 10002=email, 10003=last4, 10004=constant)"],
    role: Annotated[str, "Target user group name from get_roles"],
    tag_value: Annotated[str, "Exact tag value this rule applies to (case-sensitive)"],
    ctx: Context,
) -> str:
```

### Pattern 4: Context logging (FastMCP)

Tools should accept `ctx: Context` as a parameter and use `await ctx.error()` / `await ctx.info()` / `await ctx.debug()` for structured MCP-level logging rather than print statements.

```python
async def get_policies(ctx: Context) -> str:
    try:
        policies = await policy.make_altr_policy_request({}, ToolConfig.auth)
        await ctx.debug(f"Fetched {len(policies)} policies")
        ...
    except Exception as e:
        await ctx.error(f"Failed to fetch policies: {e}")
        raise
```

### Pattern 5: credentials.py separation

Move `Creds` class and `load_dotenv()` call out of `server.py` into a dedicated `credentials.py`. This separates framework concerns from auth concerns and enables CLI credential override.

```python
# src/altr_mcp/credentials.py
import os
import httpx
from dotenv import load_dotenv


def build_auth(key_override=None, secret_override=None):
    load_dotenv(override=True)
    key = key_override or os.getenv('MAPI_KEY')
    secret = secret_override or os.getenv('MAPI_SECRET')
    return httpx.BasicAuth(username=key, password=secret)


def get_org_id():
    return os.getenv('ORG_ID')
```

### Pattern 6: src/ layout with hatchling

Hatchling needs explicit package path configuration for `src/` layout.

```toml
# pyproject.toml additions
[tool.hatch.build.targets.wheel]
packages = ["src/altr_mcp"]

[project.scripts]
altr-mcp = "altr_mcp.server:main"
```

No change to the entry point name (`altr-mcp`) or the function reference (`server:main`) — only the package location changes.

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Module-level credential initialization

**What:** Instantiating `Creds()` at module import time (current pattern in server.py lines 29-30).

```python
# Current — BAD
creds = Creds()
Auth = creds.get_auth()
```

**Why bad:** Fails at import time if env vars are missing. Makes CLI credential overrides impossible. Blocks testing without real credentials.

**Instead:** Defer credential loading to `main()`, pass auth as argument to `tool_init()`.

### Anti-Pattern 2: Single monolithic server.py

**What:** All tool implementations, credential logic, FastMCP setup, and `main()` in one file.

**Why bad:** Any tool edit requires touching the same file as framework code. Merge conflicts on every tool change. Cannot test tools in isolation. 900 lines becomes 1200 lines as tools are added.

**Instead:** One `altr_tools/` module per domain. `server.py` only does setup + loading.

### Anti-Pattern 3: Shadowing stdlib names

**What:** Current `server.py` has `import tag` from utils then uses `tag` as a parameter name in `create_policy(tag: str)`. Also `create_policy` imports the `tag` module via `from altr_mcp.utils import tag` at the top, then shadows it as a parameter.

**Why bad:** Python silently uses the parameter inside the function body, masking the module reference. In modular tool files this becomes obvious and breaks.

**Instead:** Name parameters unambiguously (`tag_name: str`) or qualify imports (`utils.tag`).

### Anti-Pattern 4: Inline `import json` inside tool functions

**What:** `get_databases()` has `import json` inside the function body.

**Why bad:** Minor performance cost on every call, signals unreviewed code.

**Instead:** Top-level imports in each module.

### Anti-Pattern 5: Mixed sync/async (requests inside async functions)

**What:** `utils/classification.py` uses `requests.get(job_url["url"])` inside `get_job_report` which is called from an async tool. This blocks the event loop.

**Why bad:** Blocks the asyncio event loop for the duration of the HTTP call. Can cause timeouts on other concurrent MCP tool calls.

**Instead:** Replace `requests.get()` with `await httpx.AsyncClient().get()` or route through the existing `utils/api.py` helper.

---

## Tool Grouping for altr_tools/

Based on the 20+ tools in the current server.py, the natural domain groupings are:

| Module | Tools | Existing utils dependency |
|--------|-------|--------------------------|
| `policies.py` | get_policies, get_rules, create_policy, add_rules, delete_policy, delete_rule, get_roles | utils/policy.py |
| `tags.py` | get_tags, get_tag_values, connect_tag, delete_tag | utils/tag.py |
| `classification.py` | get_classifiers, create_classifier, delete_classifier, get_collections, create_collection, delete_collection, get_jobs, create_job, update_job_status, get_classification_report | utils/classification.py |
| `databases.py` | get_databases, get_database_id | utils/database.py |
| `snowflake.py` | create_snowflake_tags | utils/snowflake.py |

These groupings are 1:1 with the existing `utils/` modules, which makes the migration mechanical.

---

## Build Order (Phase Dependencies)

The modular refactor must happen in a specific sequence because each step has hard dependencies on the previous one:

```
Step 1: src/ layout migration
        Move altr_mcp/ → src/altr_mcp/
        Update pyproject.toml hatch config
        Verify: uv build succeeds, entry point works
        No logic changes yet
        │
        ▼
Step 2: credentials.py extraction
        Extract Creds class from server.py → credentials.py
        Add build_auth(key_override, secret_override) and get_org_id()
        Move load_dotenv() call out of module scope
        Verify: server still starts, tools still work
        │
        ▼
Step 3: altr_tools/ module creation + tool migration
        Create altr_tools/__init__.py with __all__
        Create one module per domain (policies, tags, classification, databases, snowflake)
        Each module: move tool functions in, add ToolConfig class, add tool_init() factory
        Fix: Annotated[Type, "desc"] on all parameters
        Fix: ctx: Context on all tool functions
        Fix: requests → httpx in classification.py utils
        Fix: stdlib name shadowing (tag parameter)
        Verify: tools registered correctly, MCP Inspector tool list matches
        │
        ▼
Step 4: server.py refactor
        Replace static tool decorators with dynamic loader loop
        Add argparse (--verbose, --mapi-key, --mapi-secret)
        Wire credentials.py into loader
        Verify: all tools still present, CLI flags work
        │
        ▼
Step 5: tests/tools_list.txt + CI schema validation
        Generate expected tool list from current working server
        Add CI step: npx @modelcontextprotocol/inspector --cli --method tools/list | diff tests/tools_list.txt
        Protects against accidental tool regressions
```

Each step has a clear "verify" checkpoint. Steps 1-2 are pure structure moves with no behavior change. Steps 3-4 change how tools are wired. Step 5 adds the safety net.

**Why this order:** The `src/` layout migration must come first because it changes import paths. Extracting credentials comes second so the tool modules can import from a stable `credentials.py`. Tool migration comes before server refactor because the loader needs the tool modules to exist before it can import them.

---

## pyproject.toml Changes Required

```toml
# Add this section (hatchling src/ layout declaration)
[tool.hatch.build.targets.wheel]
packages = ["src/altr_mcp"]

# Entry point is UNCHANGED — backward compatibility preserved
[project.scripts]
altr-mcp = "altr_mcp.server:main"
```

No build backend change (keep hatchling). No package name change (`altr-mcp`). Only the package source directory declaration changes.

---

## Scalability Considerations

| Concern | Now (20 tools) | After refactor (20 tools, modular) | Future (30+ tools) |
|---------|---------------|-----------------------------------|-------------------|
| Adding a new tool | Edit 900-line server.py | Add function to domain module, register in tool_init | Same — zero friction |
| Finding a tool's implementation | Search 900 lines | Open domain module directly | Same |
| Testing a single tool | Must mock entire server | Import domain module, mock ToolConfig.auth | Same |
| New tool domain (e.g., audit logs) | Add to server.py | Create altr_tools/audit.py, add to __all__ | Same pattern |
| Credential schemes (e.g., OAuth) | Requires server.py edit | Edit credentials.py only | Same |

The dynamic loader pattern means adding a new tool domain is always two steps: create the module, add its name to `__all__`. The server does not need to change.

---

## Sources

- Direct code inspection: `/Users/parker/altr-claude/mcp-publish/pycti-mcp/` (reference implementation)
- Direct code inspection: `/Users/parker/altr-claude/mcp-publish/altr-mcp-server/` (current state)
- pycti-mcp patterns observed: `src/` layout, `tool_init()` factory, `__all__` dynamic loader, `Annotated[Type, "desc"]`, `ctx: Context`, argparse CLI, tools_list.txt CI validation
- FastMCP Context logging: observed in `lookup_observables.py` and `lookup_adversary.py` — `ctx.debug()`, `ctx.info()`, `ctx.error()` are all async methods
- Confidence: HIGH — all patterns verified by reading actual implementation files
