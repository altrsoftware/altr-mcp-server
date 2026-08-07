"""Invariants for the release workflow that CI would not otherwise catch.

publish.yml only ever executes on a tag push, so nothing here runs during
a normal CI build. These are cheap static assertions about the file, aimed
at the properties that are easy to lose in an edit and expensive to
discover during a release.
"""
import importlib.util
import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLISH_YML = REPO_ROOT / ".github" / "workflows" / "publish.yml"
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"


@pytest.fixture(scope="module")
def workflow():
    """publish.yml with comment-only lines stripped.

    The comments explain what these tests enforce and quote the very
    strings being banned, so matching against them would be circular.
    """
    return "\n".join(
        line for line in PUBLISH_YML.read_text().splitlines()
        if not line.lstrip().startswith("#")
    )


def test_mcp_publisher_is_pinned_to_a_release(workflow):
    """The publisher binary must not track releases/latest.

    It runs in the job holding id-token: write for the
    io.github.altrsoftware namespace, so whatever this downloads can publish
    to the registry as us. `latest` means an upstream release changes what
    we execute without anything in this repo changing.
    """
    assert "releases/latest" not in workflow, (
        "mcp-publisher is tracking releases/latest again; pin a version"
    )
    version = re.search(r"MCP_PUBLISHER_VERSION:\s*(v[\d.]+)", workflow)
    assert version, "no pinned MCP_PUBLISHER_VERSION in publish.yml"


def test_mcp_publisher_download_is_checksummed(workflow):
    """A committed digest, verified after download.

    Checked against a value in this repo rather than the checksums.txt from
    the same release: anyone who can replace the tarball can replace the
    checksum file next to it.
    """
    digest = re.search(r"MCP_PUBLISHER_SHA256:\s*([0-9a-f]{64})\b", workflow)
    assert digest, "no 64-hex MCP_PUBLISHER_SHA256 pinned in publish.yml"
    assert "sha256sum --check --strict" in workflow, (
        "the pinned digest is never verified against the download"
    )


def test_publisher_download_fails_loudly(workflow):
    """curl must use --fail.

    Without it curl exits 0 on a 404 and writes the error page to the output
    file, which then gets fed to tar. The previous version of this step
    piped curl straight into tar with no --fail at all.
    """
    install = workflow[workflow.index("- name: Install mcp-publisher"):]
    install = install[:install.index("- name:", 1)]
    assert "--fail" in install, "curl in the install step is missing --fail"
    assert "| tar" not in install, (
        "do not pipe curl into tar; download, verify the digest, then extract"
    )


def test_every_job_that_checks_out_has_contents_read():
    """A job-level permissions block replaces the workflow-level one.

    So a job that declares only id-token: write runs actions/checkout with
    no contents permission. That works today only because the repo is
    public; it breaks the day it goes private.
    """
    data = yaml.safe_load(PUBLISH_YML.read_text())

    missing = []
    for name, job in data["jobs"].items():
        uses_checkout = any(
            "actions/checkout" in str(step.get("uses", ""))
            for step in job.get("steps", [])
        )
        perms = job.get("permissions")
        # No job-level block at all means the workflow-level one applies.
        if uses_checkout and perms and perms.get("contents") != "read":
            missing.append(name)

    assert not missing, (
        f"jobs check out the repo without contents: read: {missing}"
    )


def test_publish_is_gated_on_tests_and_verify_release():
    """The dependency chain is what makes the committed server.json safe.

    publish-mcp publishes the committed server.json rather than rewriting it
    from the tag. That is only sound because, by the time it runs:

      * `test` has asserted server.json matches the newest CHANGELOG section
        (test_server_json_matches_newest_changelog_section)
      * `verify-release` has asserted the tag matches that same section
      * `publish` needs both, and `publish-mcp` needs `publish`

    Drop a link and server.json could reach the registry disagreeing with the
    tag, with nothing having checked. Publishing is irreversible, so the chain
    is asserted here rather than assumed.
    """
    data = yaml.safe_load(PUBLISH_YML.read_text())

    publish_needs = set(data["jobs"]["publish"]["needs"])
    assert {"test", "verify-release"} <= publish_needs, (
        f"publish must need test and verify-release; needs {publish_needs}"
    )

    mcp_needs = data["jobs"]["publish-mcp"]["needs"]
    mcp_needs = {mcp_needs} if isinstance(mcp_needs, str) else set(mcp_needs)
    assert "publish" in mcp_needs, (
        f"publish-mcp must need publish; needs {mcp_needs}"
    )

    assert "pytest tests/" in str(data["jobs"]["test"]["steps"]), (
        "the test job must run the full suite, which is what checks server.json"
    )


def test_server_json_is_not_rewritten_at_publish_time(workflow):
    """publish-mcp checks server.json; it must not overwrite it.

    Stamping the tag over the committed value is what let it rot unnoticed
    for several releases: a wrong value had no consequence, so nothing ever
    surfaced it. The committed file is now what publishes.
    """
    assert ".version = $v" not in workflow, (
        "publish-mcp is rewriting server.json again; it should assert instead"
    )
    assert "server.json.tmp" not in workflow, (
        "publish-mcp is writing a modified server.json"
    )
    assert "jq -e" in workflow, (
        "the server.json/tag agreement check is missing from publish-mcp"
    )


def _load_changelog_gate():
    """Load scripts/check_changelog.py, the script verify-release runs.

    Its own unit tests live in tests/unit/test_check_changelog.py. What is
    asserted here is repo state -- that the committed CHANGELOG and
    server.json are releasable -- rather than the script's behaviour.
    """
    script = REPO_ROOT / "scripts" / "check_changelog.py"
    spec = importlib.util.spec_from_file_location("check_changelog", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_real_changelog_is_releasable_at_the_server_json_version():
    """The repo as it stands could be tagged right now.

    Ties the release gate to the server.json guard in test_docs_drift.py:
    that one pins server.json to the newest CHANGELOG section, this one
    requires the release to be that same section. If they ever disagree, one
    of the two fails here rather than during a release.
    """
    version = json.loads((REPO_ROOT / "server.json").read_text())["version"]
    text = (REPO_ROOT / "CHANGELOG.md").read_text()
    assert _load_changelog_gate().check(text, version) == [], (
        f"CHANGELOG.md is not releasable as {version}"
    )


def test_workflow_calls_the_changelog_gate(workflow):
    """verify-release must actually invoke the script that is unit tested.

    Without this the workflow could keep its own inline copy of the logic
    and tests/unit/test_check_changelog.py would pass while the real gate
    stayed broken.
    """
    assert "scripts/check_changelog.py" in workflow
    assert not re.search(r"awk .*want=", workflow), (
        "the inline awk changelog check is back in publish.yml"
    )


def test_python_support_is_claimed_tested_and_classified_alike():
    """requires-python, the CI matrix and the classifiers agree.

    These drifted: requires-python allowed >=3.11, the classifiers stopped
    at 3.12, and CI tested only 3.11 -- so 3.13 and 3.14 were permitted by
    the metadata, advertised nowhere, and never run. The wheel is
    py3-none-any, so this is about whether the code works on what is
    claimed, not about the artifact.
    """
    import tomllib

    pyproject = tomllib.loads(_read_text(REPO_ROOT / "pyproject.toml"))
    project = pyproject["project"]

    classified = {
        c.rsplit("::", 1)[1].strip()
        for c in project["classifiers"]
        if c.startswith("Programming Language :: Python :: ")
        and c.rsplit("::", 1)[1].strip()[0].isdigit()
        and "." in c.rsplit("::", 1)[1]
    }

    ci = yaml.safe_load(CI_YML.read_text())
    matrix = set(ci["jobs"]["test"]["strategy"]["matrix"]["python-version"])

    assert matrix == classified, (
        f"CI tests {sorted(matrix)} but pyproject classifies "
        f"{sorted(classified)}"
    )

    floor = project["requires-python"].lstrip(">=").strip()
    assert floor in matrix, (
        f"requires-python is {project['requires-python']!r} but CI never "
        f"tests {floor}; it tests {sorted(matrix)}"
    )
    lowest = min(matrix, key=lambda v: tuple(int(p) for p in v.split(".")))
    assert lowest == floor, (
        f"requires-python allows {floor} but the lowest tested version is "
        f"{lowest}; either raise the floor or test it"
    )


def _read_text(path):
    return path.read_text()
