"""Unit tests for the release CHANGELOG gate (scripts/check_changelog.py).

The logic these cover used to live inline in the verify-release job, where
nothing ran it except a live release. That is why it went unnoticed that it
accepted the tag's section anywhere in the file.
"""
import importlib.util
import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_changelog.py"


def _load():
    """Import the script by path.

    scripts/ is deliberately not a package -- it holds standalone release
    tooling that must run against a bare checkout, so it should not gain an
    __init__.py just to be importable here.
    """
    spec = importlib.util.spec_from_file_location("check_changelog", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_changelog = _load()


HEADER = """# Changelog

All notable changes to this project will be documented in this file.

"""


def _changelog(*sections):
    """Build a changelog from (version, body) pairs, newest first."""
    out = HEADER
    for version, body in sections:
        out += f"## [{version}]\n\n{body}\n\n"
    return out


GOOD = _changelog(
    ("0.5.5", "### Fixed\n- something"),
    ("0.5.4", "### Added\n- something older"),
)


def test_newest_section_reads_the_topmost_heading():
    assert check_changelog.newest_section(GOOD) == "0.5.5"


def test_newest_section_is_none_when_there_are_no_sections():
    assert check_changelog.newest_section("# Changelog\n\nnothing yet\n") is None


def test_passes_when_the_tag_is_the_newest_section():
    assert check_changelog.check(GOOD, "0.5.5") == []


def test_fails_when_a_newer_section_sits_above_the_tag():
    """The bug this script exists to fix.

    Someone opens a 0.5.6 heading before 0.5.5 ships. The old awk found the
    non-empty [0.5.5] section further down and passed, so the release went
    out with the changelog and server.json disagreeing about the version.
    """
    text = _changelog(
        ("0.5.6", "### Added\n- next release, started early"),
        ("0.5.5", "### Fixed\n- something"),
    )
    problems = check_changelog.check(text, "0.5.5")
    assert len(problems) == 1
    assert "not the newest" in problems[0]
    assert "0.5.6" in problems[0]


def test_fails_when_the_newest_section_is_empty():
    text = _changelog(("0.5.5", ""), ("0.5.4", "### Added\n- older"))
    problems = check_changelog.check(text, "0.5.5")
    assert len(problems) == 1
    assert "is empty" in problems[0]


def test_fails_when_the_version_is_absent_entirely():
    problems = check_changelog.check(GOOD, "0.9.9")
    assert len(problems) == 1
    assert "not present at all" in problems[0]


def test_fails_when_there_are_no_sections():
    problems = check_changelog.check("# Changelog\n\nnothing\n", "0.5.5")
    assert len(problems) == 1
    assert "no '## [x.y.z]' section" in problems[0]


def test_accepts_a_trailing_date_on_the_heading():
    """`## [0.5.3] - 2026-07-29` is valid Keep a Changelog, and the awk
    this replaces accepted it. Do not regress that."""
    text = HEADER + "## [0.5.5] - 2026-07-29\n\n### Fixed\n- something\n"
    assert check_changelog.check(text, "0.5.5") == []


def test_does_not_prefix_match_a_longer_version():
    """0.5.1 must not satisfy a `## [0.5.10]` heading."""
    text = _changelog(("0.5.10", "### Fixed\n- something"))
    problems = check_changelog.check(text, "0.5.1")
    assert len(problems) == 1
    assert "0.5.10" in problems[0]


@pytest.mark.parametrize("argv,expected", [
    (["check_changelog.py"], 2),
    (["check_changelog.py", "a", "b", "c"], 2),
])
def test_main_rejects_bad_arguments(argv, expected, capsys):
    assert check_changelog.main(argv) == expected


def test_main_reports_a_missing_file(tmp_path, capsys):
    missing = tmp_path / "nope.md"
    assert check_changelog.main(["x", "0.5.5", str(missing)]) == 1
    assert "cannot read" in capsys.readouterr().err


def test_main_exit_codes(tmp_path, capsys):
    path = tmp_path / "CHANGELOG.md"
    path.write_text(GOOD)
    assert check_changelog.main(["x", "0.5.5", str(path)]) == 0
    assert check_changelog.main(["x", "0.5.4", str(path)]) == 1
    assert "::error::" in capsys.readouterr().err


def test_real_changelog_is_releasable_at_the_server_json_version():
    """The repo as it stands could be tagged right now.

    Ties this gate to the server.json guard in test_docs_drift.py: that one
    pins server.json to the newest CHANGELOG section, this one requires the
    release to be that same section. If they ever disagree, one of the two
    fails here rather than during a release.
    """
    version = json.loads((REPO_ROOT / "server.json").read_text())["version"]
    text = (REPO_ROOT / "CHANGELOG.md").read_text()
    assert check_changelog.check(text, version) == [], (
        f"CHANGELOG.md is not releasable as {version}"
    )


def test_workflow_calls_this_script():
    """verify-release must actually invoke the script these tests cover.

    Without this, the workflow could keep its own inline copy of the logic
    and these tests would pass while the real gate stayed broken.
    """
    workflow = (REPO_ROOT / ".github" / "workflows" / "publish.yml").read_text()
    assert "scripts/check_changelog.py" in workflow
    assert not re.search(r"awk .*want=", workflow), (
        "the inline awk changelog check is still in publish.yml"
    )
