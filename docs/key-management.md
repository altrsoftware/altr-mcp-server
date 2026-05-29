title: ALTR MCP Server Key Management

# Key Management (9 tools)

Manage FPE (format-preserving encryption) keys and tweaks via the ALTR Key Management API. Keys and tweaks are the cryptographic material used by FPE operations. Both resources are versioned — each create or rotate produces a new `sequence`, while prior versions can be deactivated individually.

## Tool Summary

| Tool | Description |
|------|-------------|
| `list_tweaks` | List all FPE tweaks for the organization |
| `get_tweak` | Get a single FPE tweak by name |
| `create_tweak` | Create a new named FPE tweak |
| `deactivate_tweak` | Deactivate a specific version of a tweak |
| `list_keys` | List FPE keys within a namespace |
| `get_key` | Get a single FPE key by namespace and name |
| `create_key` | Create a new FPE encryption key |
| `deactivate_key` | Deactivate a specific version of a key |
| `rotate_key` | Rotate the envelope key for a specific key version |

## Concepts

- **Tweak** — A named random value that adds uniqueness to FPE outputs for the same plaintext. Tweaks are scoped to the organization.
- **Key** — A named encryption key within a namespace (typically `fpe`). Keys are the primary cryptographic material for FPE.
- **Sequence** — A version identifier for each tweak or key. Each creation or rotation produces a new sequence. Pass `sequence` to target a specific version; omit it to get the latest.
- **Namespace** — Keys are organized into namespaces. The `fpe` namespace is standard for format-preserving encryption keys.

## Pagination

`list_tweaks` and `list_keys` return a `contiguous_id` when there are more results. Pass it back as `contiguous_id` on the next call to continue paginating.

## Tool Details

### list_tweaks

List all FPE tweaks for the organization. Results are paginated.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `contiguous_id` | str | no | Pagination cursor from a prior response |
| `limit` | int | no | Max tweaks to return |
| `contain` | str | no | Filter tweaks whose name contains this substring |
| `status` | str | no | Filter by status: `"active"`, `"deactivated"`, or `"any"` (default `"any"`) |

---

### get_tweak

Get a single FPE tweak by name.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | str | yes | Name of the tweak |
| `sequence` | str | no | Version sequence identifier. Omit to get the latest version |

---

### create_tweak

Create a new named FPE tweak. The name must not have leading or trailing spaces.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | str | yes | Name for the new tweak (1–256 characters, trimmed) |

---

### deactivate_tweak

Deactivate a specific version of an FPE tweak. Deactivated tweaks cannot be used for new FPE operations. Use `get_tweak` to discover the `sequence` for a version.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | str | yes | Name of the tweak |
| `sequence` | str | yes | Version sequence identifier to deactivate |

---

### list_keys

List FPE keys within a namespace. Results are paginated.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `namespace` | str | yes | Namespace to list keys from (e.g. `"fpe"`) |
| `contiguous_id` | str | no | Pagination cursor from a prior response |
| `limit` | int | no | Max keys to return |
| `contain` | str | no | Filter keys whose name contains this substring |
| `status` | str | no | Filter by status: `"active"`, `"deactivated"`, or `"any"` (default `"any"`) |

---

### get_key

Get a single FPE key by namespace and name.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `namespace` | str | yes | Namespace where the key resides (e.g. `"fpe"`) |
| `name` | str | yes | Name of the key |
| `sequence` | str | no | Version sequence identifier. Omit to get the latest version |

---

### create_key

Create a new FPE encryption key. Both `name` and `namespace` must not have leading or trailing spaces.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `namespace` | str | yes | Namespace for the key (e.g. `"fpe"`) |
| `name` | str | yes | Name for the new key (1–256 characters, trimmed) |

---

### deactivate_key

Deactivate a specific version of an FPE key. Deactivated keys cannot be used for new encryption operations. Use `get_key` to discover the `sequence` for a version.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `namespace` | str | yes | Namespace where the key resides |
| `name` | str | yes | Name of the key |
| `sequence` | str | yes | Version sequence identifier to deactivate |

---

### rotate_key

Rotate the envelope key for a specific FPE key version. Envelope rotation re-wraps the data key under a new envelope key without changing the underlying encryption material. Use for key rotation compliance requirements.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `namespace` | str | yes | Namespace where the key resides |
| `name` | str | yes | Name of the key |
| `sequence` | str | yes | Version sequence identifier of the key to rotate |
