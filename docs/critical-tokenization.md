# Critical Tokenization Tools (4 tools)

Tokenize and detokenize sensitive values using ALTR critical tokenization. Critical tokens have the format `token_XXXX...` (64+ characters). Unlike vaulted tokenization, invalid tokens are silently ignored during deletion.

Maximum 1024 values per call. Each value must be under 128 UTF-8 code units.

## Tool Summary

| Tool | Description |
|------|-------------|
| `critical_tokenize` | Tokenize plaintext values to critical tokens |
| `critical_detokenize` | Detokenize critical tokens to recover plaintext |
| `critical_partial_detokenize` | Detokenize tokens, passing non-tokens through unchanged |
| `critical_delete_tokens` | Delete critical tokens (invalid tokens silently ignored) |

## Workflow

All four tools accept a `dict[str, str]` where keys are user-defined identifiers (e.g. `"ssn"`, `"email"`) and values are the plaintext or token strings. The API uses positional field names (`field000`, `field001`, ...) internally; the tools translate automatically so responses are returned with the original keys.

1. Tokenize plaintext with `critical_tokenize` — returns a dict with the same keys mapped to critical tokens.
2. Detokenize later with `critical_detokenize` or `critical_partial_detokenize`.
3. Delete tokens with `critical_delete_tokens` when they are no longer needed. Invalid tokens are silently ignored.

## Token format comparison

| Service | Token format | Max values per call | Max value size |
|---------|-------------|---------------------|----------------|
| Vault | `vaultd_XXXX...` | 4096 | 1024 chars |
| Critical | `token_XXXX...` (64+ chars) | 1024 | 128 UTF-8 code units |

## Tool Details

### critical_tokenize

Tokenize plaintext values. Each value must be under 128 UTF-8 code units.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `values` | dict[str, str] | yes | Keys are user-defined labels; values are plaintext strings to tokenize (e.g. `{"ssn": "123-45-6789"}`) |
| `deterministic` | bool | no | If `true`, the same plaintext always produces the same token. Default `false` |

---

### critical_detokenize

Detokenize critical tokens to recover plaintext. Fails if any value is not a valid critical token. Use `critical_partial_detokenize` for mixed inputs.

Tokens are case-sensitive.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tokens` | dict[str, str] | yes | Keys are user-defined labels; values are critical tokens to detokenize (e.g. `{"ssn": "token_abc123..."}`) |

---

### critical_partial_detokenize

Detokenize critical tokens, passing non-token values through unchanged. Valid tokens are detokenized; all other values are returned as-is.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `values` | dict[str, str] | yes | Keys are user-defined labels; values are critical tokens or plaintext strings |

---

### critical_delete_tokens

Delete critical tokens. Invalid tokens are silently ignored (no failure). If a deleted deterministic token is re-tokenized with the same plaintext, a new token is generated.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tokens` | dict[str, str] | yes | Keys are user-defined labels; values are critical tokens to delete |
