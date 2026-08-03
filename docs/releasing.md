title: ALTR MCP Server Releasing

# Releasing

The git tag is the single source of truth for a release version. `pyproject.toml`
declares `dynamic = ["version"]` and reads the version from the tag through
[`uv-dynamic-versioning`](https://github.com/ninoseki/uv-dynamic-versioning), so
there is no version to bump by hand.

## Steps

1. Land the change on `main`. **Do not edit [CHANGELOG.md](../CHANGELOG.md)** —
   it is generated. Write [Conventional Commit](https://www.conventionalcommits.org/)
   messages instead; those are what the entries are built from. See
   [What lands in the changelog](#what-lands-in-the-changelog) below.
2. Tag the commit and push the tag:

   ```bash
   git tag v0.5.3
   git push origin v0.5.3
   ```

   Only numeric tags (`v[0-9]+.[0-9]+.[0-9]+`) trigger the release. Pre-release
   tags such as `v0.5.3-rc1` are ignored by the workflow.

3. Watch [Publish to PyPI](https://github.com/altrsoftware/altr-mcp-server/actions/workflows/publish.yml).
   After the PyPI upload succeeds, the `changelog` job writes the new section to
   `CHANGELOG.md`, commits it to `main`, and opens the GitHub release with the
   same notes.

`server.json` needs no bump. The `publish-mcp` job stamps the tag into
`version` and `packages[].version` before publishing to the registry, so the
committed values are a convenience; the test suite only checks that they agree
with each other.

## What lands in the changelog

Entries come from Conventional Commit messages in the tag range, grouped by
type. Configuration lives in [`cliff.toml`](../cliff.toml).

| Commit type | Section | |
|---|---|---|
| `feat:` | Added | |
| `fix:` | Fixed | |
| `perf:` | Performance | |
| `revert:` | Removed | |
| `ci:`, `build:`, `chore(deps):` | Changed | operator-visible |
| anything with `!` or `BREAKING CHANGE` | Changed | listed first |
| `chore:`, `docs:`, `test:`, `refactor:`, `style:` | *omitted* | internal-only |
| non-Conventional (e.g. merge commits) | *omitted* | |

The commit subject becomes the entry verbatim, so write subjects that read as
release notes. If a change matters to users, give it a `feat:` or `fix:` type —
a `test:` or `chore:` commit will not appear, however user-visible its effect.

To preview what a tag would produce, before tagging:

```bash
uvx git-cliff --unreleased --tag v0.5.6
```

Sections above the newest generated one were written by hand before the switch
to generation. `git-cliff` only ever prepends, so that history stays as it is.

Never reuse a version number, even for a release that failed to publish: PyPI
and the MCP Registry both reject a version that was already uploaded, and
version numbers are immutable per AES-0006. `v0.5.2` failed to publish, so the
next release was `0.5.3`, not a retry of `0.5.2`.

## What the workflow does

| Job | Purpose |
|-----|---------|
| `test` | Runs the test suite against the tagged commit. |
| `verify-release` | Builds the package and fails if the built version differs from the tag. Gates everything below — nothing downstream runs if it fails. |
| `publish` | Builds and uploads to PyPI via OIDC trusted publishing. |
| `publish-mcp` | Stamps the tag into `server.json` and publishes to the MCP Registry via GitHub OIDC. |
| `changelog` | Generates the new `CHANGELOG.md` section with `git-cliff`, commits it to `main`, and creates the GitHub release. Runs after `publish`, so notes only appear for an artifact that is actually public. |

## Build environment prerequisite

Building a *real* version needs **`git` on `PATH` and a `.git` directory with
the tags fetched**. Neither failure mode breaks the build — each yields an
unpublishable version instead:

- Tags missing, repo readable: `0.0.0.post<N>.dev0+<sha>`
- VCS unreadable — no `.git` (source zips, Docker contexts), no `git` binary, a
  dubious-ownership refusal, any failing git command: the `fallback-version` of
  `0.0.0+unknown`

`verify-release` is what stops either from shipping, by comparing the built
version against the tag. PyPI independently rejects both, since it refuses any
PEP 440 local segment — but that only covers versions carrying one. A `v0.5.4`
tag on a commit already tagged `v0.5.3` builds a clean, publishable `0.5.3`;
only the tag comparison catches that.

Consumers installing from a published sdist are unaffected, and need neither
`git` nor `.git`: the sdist carries a static `PKG-INFO`, which is authoritative
when rebuilding a wheel from it.
