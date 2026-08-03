#!/usr/bin/env python3
"""Verify CHANGELOG.md documents the version being released.

Run by the ``verify-release`` job in .github/workflows/publish.yml, which
gates every tag push.

This lives here rather than inline in the workflow so it can be unit
tested. The check it replaces was shell embedded in YAML and therefore
only ever executed during a live release -- which is how it went unnoticed
that it accepted the tag's section anywhere in the file, not just as the
newest one. A release could document 0.5.5 three sections down while the
newest section said something else entirely.

Standard library only, and it imports nothing from ``altr_mcp``: it runs
against a bare checkout, before and independently of the package being
built or installed.
"""
import pathlib
import re
import sys

# "## [0.5.5]" or "## [0.5.5] - 2026-07-29".
#
# Only MAJOR.MINOR.PATCH counts as a release heading. Keep a Changelog --
# which this project's CHANGELOG header says it follows -- puts a
# "## [Unreleased]" section at the top to collect work that has not shipped,
# and the release workflow only fires on numeric v[0-9]+.[0-9]+.[0-9]+ tags.
# Treating a non-numeric heading as the newest release would block every
# release the moment anyone adopted that convention.
#
# The closing bracket is part of the pattern, so 0.5.1 does not match a
# "## [0.5.10]" heading -- the same prefix trap the awk this replaced
# avoided by matching the literal "]".
SECTION = re.compile(r"^## \[(\d+\.\d+\.\d+)\]")

USAGE = "usage: check_changelog.py VERSION [CHANGELOG_PATH]"


def _headings(text):
    """Every release heading, as (line index, version), newest first.

    Newest first because Keep a Changelog puts the most recent release at
    the top; this reads the file in order and does not sort. A file whose
    sections are out of order is a problem for a human, not for this.

    Non-release headings -- ``## [Unreleased]``, or a pre-release such as
    ``## [1.0.0-rc1]`` that no numeric tag can match -- are skipped, not
    rejected. They are allowed to sit above the release being tagged.
    """
    return [
        (i, match.group(1))
        for i, line in enumerate(text.splitlines())
        for match in [SECTION.match(line)]
        if match
    ]


def newest_section(text):
    """Version of the topmost release heading, or None if there is none."""
    headings = _headings(text)
    return headings[0][1] if headings else None


def check(text, version):
    """Return a list of problems. Empty means the changelog is releasable."""
    lines = text.splitlines()
    headings = _headings(text)

    if not headings:
        return [
            f"CHANGELOG.md has no '## [{version}]' section. Only "
            "MAJOR.MINOR.PATCH headings count as releases -- if the notes "
            "for this release are under '## [Unreleased]', rename that "
            f"heading to '## [{version}]'."
        ]

    index, newest = headings[0]
    if newest != version:
        where = (
            "it is not the newest"
            if any(v == version for _, v in headings)
            else "it is not present at all"
        )
        return [
            f"the newest CHANGELOG.md section is '## [{newest}]' but the tag "
            f"is {version} -- {where}. The release being tagged must be the "
            f"topmost section; move '## [{version}]' above '## [{newest}]', "
            f"or tag {newest} instead."
        ]

    # Content between this heading and the next one. Require something
    # non-blank: adding an empty section is the easiest way to turn this
    # check green without actually documenting the release.
    for line in lines[index + 1:]:
        if line.startswith("## "):
            break
        if line.strip():
            return []
    return [f"the '## [{version}]' section in CHANGELOG.md is empty"]


def main(argv):
    if not 2 <= len(argv) <= 3:
        print(USAGE, file=sys.stderr)
        return 2

    version = argv[1]
    path = pathlib.Path(argv[2] if len(argv) == 3 else "CHANGELOG.md")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"::error::cannot read {path}: {exc}", file=sys.stderr)
        return 1

    problems = check(text, version)
    for problem in problems:
        print(f"::error::{problem}", file=sys.stderr)
    if not problems:
        print(f"CHANGELOG.md documents {version} as the newest section")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
