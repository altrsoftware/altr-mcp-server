title: ALTR MCP Server Releasing

# Releasing

The git tag is the single source of truth for a release version. `pyproject.toml`
declares `dynamic = ["version"]` and reads the version from the tag through
[`uv-dynamic-versioning`](https://github.com/ninoseki/uv-dynamic-versioning), so
there is no version to bump by hand.

## Steps

1. Land the change on `main`, including a `## [MAJOR.MINOR.PATCH]` section in
   [CHANGELOG.md](../CHANGELOG.md). The release fails without it.
2. Bump `version` and `packages[].version` in `server.json` to the version you
   are about to release. These committed values are documentation — the
   `publish-mcp` job stamps the tag over them before publishing to the registry
   — but the test suite checks them against the newest `CHANGELOG.md` section,
   so they cannot silently fall behind. In practice step 1 fails CI until this
   is done.
3. Tag the commit and push the tag:

   ```bash
   git tag v0.5.3
   git push origin v0.5.3
   ```

   Only numeric tags (`v[0-9]+.[0-9]+.[0-9]+`) trigger the release. Pre-release
   tags such as `v0.5.3-rc1` are ignored by the workflow.

4. Watch [Publish to PyPI](https://github.com/altrsoftware/altr-mcp-server/actions/workflows/publish.yml).

Never reuse a version number, even for a release that failed to publish: PyPI
and the MCP Registry both reject a version that was already uploaded, and
version numbers are immutable per AES-0006. `v0.5.2` failed to publish, so the
next release was `0.5.3`, not a retry of `0.5.2`.

## What the workflow does

| Job | Purpose |
|-----|---------|
| `test` | Runs the test suite against the tagged commit. |
| `verify-release` | Builds the package and fails if the built version differs from the tag, or if `CHANGELOG.md` has no non-empty section for it. Gates everything below — nothing downstream runs if it fails. |
| `publish` | Builds and uploads to PyPI via OIDC trusted publishing. |
| `publish-mcp` | Stamps the tag into `server.json` and publishes to the MCP Registry via GitHub OIDC. |

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
