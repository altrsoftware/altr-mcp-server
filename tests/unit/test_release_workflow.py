"""Invariants for the release workflow that CI would not otherwise catch.

publish.yml only ever executes on a tag push, so nothing here runs during
a normal CI build. These are cheap static assertions about the file, aimed
at the properties that are easy to lose in an edit and expensive to
discover during a release.
"""
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLISH_YML = REPO_ROOT / ".github" / "workflows" / "publish.yml"


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
