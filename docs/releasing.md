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
   — but keeping them current avoids confusion.
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
| `verify-release` | Builds the package and fails if the built version differs from the tag, or if `CHANGELOG.md` has no non-empty section for it. `publish` needs it. |
| `publish` | Builds and uploads to PyPI via OIDC trusted publishing. |
| `publish-mcp` | Stamps the tag into `server.json` and publishes to the MCP Registry via GitHub OIDC. |

## Build environment prerequisite

Any environment that needs a *real* version from this project needs **`git` on
`PATH` and a `.git` directory with the tags fetched**. Neither failure mode is
fatal to the build — both produce a version rather than an error:

- **Tags missing, repo readable** (a shallow clone without tags):
  `0.0.0.post<N>.dev0+<sha>`.
- **VCS unreadable** — no `.git` (source zips, Docker contexts), no `git`
  binary, a dubious-ownership refusal, or any failing git command:
  `fallback-version` in `pyproject.toml` yields `0.0.0+unknown`.

`verify-release` is what stops either from being released: it compares the built
version against the tag, and `publish` depends on it, so the upload never runs.
PyPI is a second line rather than the first — it rejects any version carrying a
PEP 440 local segment, which both strings above have, but that only covers the
cases that produce one. A `v0.5.3` tag pushed onto a commit already tagged
`v0.5.2` builds a clean, publishable `0.5.2`; only the tag comparison catches
that.

Consumers installing from a published sdist are unaffected, and need neither
`git` nor `.git`: the sdist carries a static `PKG-INFO`, which is authoritative
when rebuilding a wheel from it.
