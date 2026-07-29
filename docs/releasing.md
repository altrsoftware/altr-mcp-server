title: ALTR MCP Server Releasing

# Releasing

The git tag is the single source of truth for a release version. `pyproject.toml`
declares `dynamic = ["version"]` and reads the version from the tag through
[`uv-dynamic-versioning`](https://github.com/ninoseki/uv-dynamic-versioning), so
there is no version to bump by hand.

## Steps

1. Land the change on `master`, including a `## [MAJOR.MINOR.PATCH]` section in
   [CHANGELOG.md](../CHANGELOG.md). The release fails without it.
2. Bump `version` and `packages[].version` in `server.json` to the version you
   are about to release. These committed values are documentation — the publish
   job stamps the tag over them — but keeping them current avoids confusion.
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
| `publish` | Builds, re-checks that the artifacts carry the tagged version, and uploads to PyPI via OIDC trusted publishing. |
| `publish-mcp` | Waits for the version to appear on PyPI, stamps the tag into `server.json`, and publishes to the MCP Registry via GitHub OIDC. |

## Build environment prerequisite

Any environment that builds this project needs **`git` on `PATH` and a `.git`
directory with the tags fetched**. When the version cannot be read from VCS,
`fallback-version` in `pyproject.toml` yields `0.0.0` instead of failing the
build, so a broken build environment produces a wrong version rather than an
error. That is why the release path asserts the built version against the tag
instead of trusting it.

Consumers installing from a published sdist are unaffected: the sdist carries a
static `PKG-INFO`, which is authoritative when rebuilding a wheel from it.
