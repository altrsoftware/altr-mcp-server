"""Unit tests for the release CHANGELOG gate (scripts/check_changelog.py).

The logic these cover used to live inline in the verify-release job, where
nothing ran it except a live release. That is why it went unnoticed that it
accepted the tag's section anywhere in the file.
"""
import importlib.util
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
    assert "no '## [0.5.5]' section" in problems[0]


UNRELEASED = HEADER + "## [Unreleased]\n\n### Added\n- not shipped yet\n\n"


def test_unreleased_section_above_the_release_is_ignored():
    """`## [Unreleased]` on top must not block a release.

    Keep a Changelog -- which this project's CHANGELOG header says it
    follows -- keeps an Unreleased section at the top to collect work in
    progress. Treating it as the newest release would fail every release
    the moment anyone adopted the convention, and the error would suggest
    tagging "Unreleased".
    """
    text = UNRELEASED + "## [0.5.6]\n\n### Fixed\n- something\n"
    assert check_changelog.check(text, "0.5.6") == []
    assert check_changelog.newest_section(text) == "0.5.6"


def test_unreleased_with_no_release_section_says_how_to_fix_it():
    """Notes written under Unreleased and never renamed."""
    problems = check_changelog.check(UNRELEASED, "0.5.6")
    assert len(problems) == 1
    assert "Unreleased" in problems[0]
    assert "rename" in problems[0]


def test_unreleased_does_not_hide_a_stale_newest_release():
    """Unreleased on top, but the newest *release* is the previous one."""
    text = UNRELEASED + "## [0.5.5]\n\n### Fixed\n- older\n"
    problems = check_changelog.check(text, "0.5.6")
    assert len(problems) == 1
    assert "0.5.5" in problems[0]


def test_unreleased_content_does_not_satisfy_the_empty_check():
    """An empty release section is still empty.

    The content scan runs forward from the release heading and stops at the
    next `## `, so content sitting under Unreleased above it must not count.
    """
    text = UNRELEASED + "## [0.5.6]\n\n## [0.5.5]\n\n### Fixed\n- older\n"
    problems = check_changelog.check(text, "0.5.6")
    assert len(problems) == 1
    assert "is empty" in problems[0]


def test_prerelease_heading_is_not_treated_as_a_release():
    """`## [1.0.0-rc1]` is skipped: no numeric tag can ever match it.

    The workflow only triggers on v[0-9]+.[0-9]+.[0-9]+, so a pre-release
    heading is never the thing being tagged.
    """
    text = (HEADER + "## [1.0.0-rc1]\n\n- release candidate\n\n"
            "## [0.5.6]\n\n### Fixed\n- something\n")
    assert check_changelog.check(text, "0.5.6") == []


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
