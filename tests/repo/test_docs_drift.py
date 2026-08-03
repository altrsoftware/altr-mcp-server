"""Guard the documentation against drifting from the live tool registry.

Nothing else in the suite compares prose to code, which is how the 0.4.0
``delete_* -> disconnect_*`` rename shipped green while ``.env.example``
kept advertising names that no longer resolved.

Two classes of drift are covered:

* **Names** — every tool-shaped identifier in the docs must resolve to a
  registered tool.
* **Counts** — every "N tools" claim must match what is actually
  registered, per domain and in total.

Both derive their expectations from ``register_all``, so a new tool or a
rename fails here until the docs are updated.
"""
import asyncio
import json
import os
import re
import tomllib
from importlib import import_module
from pathlib import Path

import pytest
from fastmcp import FastMCP

from altr_mcp.tools import register_all

# parents[2] walks this file up to the repo root:
# tests/repo/test_docs_drift.py -> tests/repo -> tests -> altr-mcp-server
REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = REPO_ROOT / "docs"

# One row per tool module: (display name, domain doc, module name).
# Display names must match both the README table and the docs/index.md
# bullet list; the module name must match a file in altr_mcp/tools/.
DOMAINS = (
    ("Databases", "databases.md", "database"),
    ("Tags", "tags.md", "tag"),
    ("Policies & Rules", "policies.md", "policy"),
    ("Classification", "classification.md", "classification"),
    ("Access Management", "access-management.md", "access_management"),
    ("Access Requests", "access-requests.md", "access_request"),
    ("Audits", "audits.md", "audit"),
    ("Audit Reports", "audit-report.md", "audit_report"),
    ("Telemetry", "telemetry.md", "telemetry"),
    ("Sidecar Configuration", "sidecar-config.md", "sidecar_config"),
    ("Vault Tokenization", "vault-tokenization.md", "vault_tokenization"),
    ("Critical Tokenization", "critical-tokenization.md",
     "critical_tokenization"),
    ("Key Management", "key-management.md", "key_management"),
)

# Files that name tools in prose, config samples, or the LLM instructions.
# CHANGELOG.md is deliberately absent: it documents the historical
# ``delete_* -> disconnect_*`` names on purpose, and those must not resolve.
DOC_SOURCES = (
    "README.md",
    ".env.example",
    "altr_mcp/instructions.md",
)

# A snake_case identifier: two or more lowercase segments.
SNAKE_CASE = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\b")

# "156 tools across 13 domains", wherever it is claimed.
TOTALS_CLAIM = re.compile(r"(\d+) tools across (\d+) domains")

# A trailing "(9 tools)" on a heading or a list item.
COUNT_SUFFIX = re.compile(r"\((\d+) tools\)")


def _tools_of(register):
    """Register into a throwaway server and return its tool list."""
    mcp = FastMCP("test")
    register(mcp)
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(mcp.list_tools())
    finally:
        loop.close()


@pytest.fixture(scope="module")
def registry():
    """Live tool names, parameter names, and per-domain counts."""
    os.environ.setdefault("ORG_ID", "test")
    os.environ.setdefault("MAPI_KEY", "test")
    os.environ.setdefault("MAPI_SECRET", "test")

    tools = _tools_of(register_all)
    names = {t.name for t in tools}
    params = set()
    for tool in tools:
        params |= set((tool.parameters or {}).get("properties", {}) or {})

    counts = {}
    for _, _, module_name in DOMAINS:
        module = import_module(f"altr_mcp.tools.{module_name}")
        counts[module_name] = len(_tools_of(module.register))

    return {
        "names": names,
        "params": params,
        "counts": counts,
        # First segment of every tool name: get_, create_, disconnect_, ...
        # Derived rather than hard-coded so a new verb needs no edit here.
        "prefixes": {n.split("_")[0] for n in names},
    }


def _read(relative_path):
    return (REPO_ROOT / relative_path).read_text()


def _doc_paths():
    return [f"docs/{p.name}" for p in sorted(DOCS_DIR.glob("*.md"))]


def test_domain_table_covers_every_tool_module():
    """DOMAINS lists exactly the modules that register_all imports.

    A new tool module fails here until it is given a domain doc and a row
    in both documentation tables.
    """
    on_disk = {
        p.stem for p in (REPO_ROOT / "altr_mcp" / "tools").glob("*.py")
        if p.stem != "__init__"
    }
    declared = {module_name for _, _, module_name in DOMAINS}
    assert declared == on_disk, (
        f"Modules with no DOMAINS row: {sorted(on_disk - declared)}\n"
        f"DOMAINS rows with no module: {sorted(declared - on_disk)}"
    )


@pytest.mark.parametrize("source", DOC_SOURCES + tuple(_doc_paths()))
def test_documented_tool_names_are_registered(registry, source):
    """Every tool-shaped identifier in the docs resolves to a real tool.

    A token counts as tool-shaped when its first segment is one that some
    registered tool uses (``get_``, ``disconnect_``, ...). Parameter names
    are excluded: ``search_uuid`` is an argument, not a tool, and no
    parameter currently shares a name with a tool.
    """
    unknown = sorted(
        token
        for token in set(SNAKE_CASE.findall(_read(source)))
        if token.split("_")[0] in registry["prefixes"]
        and token not in registry["names"]
        and token not in registry["params"]
    )
    assert not unknown, (
        f"{source} names tools that are not registered: {unknown}\n"
        "Rename them to the current tool names, or add the missing tool."
    )


@pytest.mark.parametrize(
    "source", ("README.md", "docs/index.md", "pyproject.toml"))
def test_total_count_claims_match_registry(registry, source):
    """Every "N tools across M domains" claim matches the registry.

    pyproject's copy is the PyPI package summary, which is why it is
    checked alongside the prose.
    """
    if source == "pyproject.toml":
        data = tomllib.loads(_read(source))
        text = data["project"]["description"]
    else:
        text = _read(source)

    claims = TOTALS_CLAIM.findall(text)
    assert claims, f"{source} makes no 'N tools across M domains' claim"

    expected = (str(len(registry["names"])), str(len(DOMAINS)))
    assert all(claim == expected for claim in claims), (
        f"{source} claims {claims}, registry has "
        f"{expected[0]} tools across {expected[1]} domains"
    )


@pytest.mark.parametrize("display,doc,module_name", DOMAINS)
def test_domain_doc_heading_count(registry, display, doc, module_name):
    """Each domain doc's "(N tools)" heading matches its module."""
    headings = COUNT_SUFFIX.findall(
        "\n".join(
            line for line in _read(f"docs/{doc}").splitlines()
            if line.startswith("#")
        )
    )
    assert headings, f"docs/{doc} heading has no '(N tools)' count"
    assert int(headings[0]) == registry["counts"][module_name], (
        f"docs/{doc} heading says {headings[0]} tools, "
        f"{module_name}.py registers {registry['counts'][module_name]}"
    )


def _parse_index_bullets():
    """Map domain display name -> count from the docs/index.md bullets."""
    found = {}
    pattern = re.compile(r"^- \[([^\]]+)\]\([^)]+\).*\((\d+) tools\)\s*$")
    for line in _read("docs/index.md").splitlines():
        match = pattern.match(line)
        if match:
            found[match.group(1)] = int(match.group(2))
    return found


def _readme_tools_section():
    """The README body between the '## Tools' heading and the next one.

    Scoped deliberately: other README tables (credentials, configuration,
    platform support) must not be mistaken for domain rows.
    """
    lines = _read("README.md").splitlines()
    for start, line in enumerate(lines):
        if line.strip() == "## Tools":
            break
    else:
        raise AssertionError("README.md has no '## Tools' section")
    rest = lines[start + 1:]
    for end, line in enumerate(rest):
        if line.startswith("## "):
            return rest[:end]
    return rest


def _parse_readme_table():
    """Map domain display name -> count from the README domain table."""
    found = {}
    # | [Databases](./docs/databases.md) | 8 | Connect ... |
    pattern = re.compile(r"^\|\s*(?:\[([^\]]+)\]\([^)]+\)|([^|]+?))\s*\|"
                         r"\s*(\d+)\s*\|")
    for line in _readme_tools_section():
        match = pattern.match(line)
        if match:
            name = (match.group(1) or match.group(2)).strip()
            found[name] = int(match.group(3))
    return found


@pytest.mark.parametrize(
    "label,parse", (("docs/index.md", _parse_index_bullets),
                    ("README.md", _parse_readme_table)))
def test_domain_listing_matches_registry(registry, label, parse):
    """Both domain listings cover all 13 domains with the right counts.

    This is what catches a partial table: the README once summed to 93
    under a heading claiming 156, with five domains missing outright.
    """
    listed = parse()
    expected = {
        display: registry["counts"][module_name]
        for display, _, module_name in DOMAINS
    }

    assert set(listed) == set(expected), (
        f"{label} domains missing: {sorted(set(expected) - set(listed))}\n"
        f"{label} domains unexpected: {sorted(set(listed) - set(expected))}"
    )

    wrong = {
        name: (count, expected[name])
        for name, count in listed.items() if count != expected[name]
    }
    assert not wrong, (
        f"{label} counts wrong (listed, actual): {wrong}"
    )

    assert sum(listed.values()) == len(registry["names"]), (
        f"{label} counts sum to {sum(listed.values())}, "
        f"registry has {len(registry['names'])} tools"
    )


# "## [0.5.5]" -- the newest section is the release being prepared.
CHANGELOG_SECTION = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", re.MULTILINE)


def test_server_json_matches_newest_changelog_section():
    """server.json tracks the newest release section in the CHANGELOG.

    Between releases that is the last released version, and nobody has to
    touch it: work accumulates under ``## [Unreleased]``, which is not a
    release heading. Renaming that section to a version at release time is
    what makes server.json stale, and this is what then requires the bump.

    These values are what gets published to the MCP Registry -- publish-mcp
    no longer rewrites them from the tag, so a stale one is a wrong registry
    entry rather than a cosmetic detail. It used to be stamped over, which is
    exactly why it went unnoticed release after release.

    Checked against the CHANGELOG rather than the git tags because CI
    checkouts do not fetch tags by default.
    """
    versions = CHANGELOG_SECTION.findall(_read("CHANGELOG.md"))
    assert versions, "CHANGELOG.md has no '## [x.y.z]' section"
    expected = versions[0]

    data = json.loads(_read("server.json"))
    found = {"version": data["version"]}
    for i, package in enumerate(data.get("packages", [])):
        found[f"packages[{i}].version"] = package["version"]

    wrong = {k: v for k, v in found.items() if v != expected}
    assert not wrong, (
        f"server.json {wrong} should be {expected!r}, the newest CHANGELOG "
        "section. See docs/releasing.md step 2."
    )
