# Vault Tokenization Tools (4 tools)

Tokenize and detokenize sensitive values using ALTR vaulted tokenization. Vault tokens have the format `vaultd_XXXX...`. Plaintext is stored in the ALTR vault and can be recovered from the token at any time.

Rate limits: 492 requests/month, 50 requests/second. Maximum 4096 values per call.

## Tool Summary

| Tool | Description |
|------|-------------|
| `vault_tokenize` | Tokenize plaintext values to vault tokens |
| `vault_detokenize` | Detokenize vault tokens to recover plaintext |
| `vault_partial_detokenize` | Detokenize tokens, passing non-tokens through unchanged |
| `vault_delete_tokens` | Permanently delete vault tokens |

## Workflow

All four tools accept a `dict[str, str]` where keys are user-defined identifiers (e.g. `"ssn"`, `"email"`) and values are the plaintext or token strings. The API uses positional field names (`field000`, `field001`, ...) internally; the tools translate automatically so responses are returned with the original keys.

1. Tokenize plaintext with `vault_tokenize` — returns a dict with the same keys mapped to vault tokens.
2. Detokenize later with `vault_detokenize` or `vault_partial_detokenize`.
3. Delete tokens permanently with `vault_delete_tokens` when they are no longer needed.

## Tool Details

### vault_tokenize

Tokenize plaintext values. Each value must be under 1024 characters.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `values` | dict[str, str] | yes | Keys are user-defined labels; values are plaintext strings to tokenize (e.g. `{"ssn": "123-45-6789"}`) |
| `deterministic` | bool | no | If `true`, the same plaintext always produces the same token. Default `false` |

---

### vault_detokenize

Detokenize vault tokens to recover plaintext. Fails if any value is not a valid vault token. Use `vault_partial_detokenize` for mixed inputs.

Tokens are case-sensitive.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tokens` | dict[str, str] | yes | Keys are user-defined labels; values are vault tokens to detokenize (e.g. `{"ssn": "vaultd_abc123..."}`) |

---

### vault_partial_detokenize

Detokenize vault tokens, passing non-token values through unchanged. Valid tokens are detokenized; all other values are returned as-is.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `values` | dict[str, str] | yes | Keys are user-defined labels; values are vault tokens or plaintext strings |

---

### vault_delete_tokens

Permanently delete vault tokens. Deleted tokens cannot be detokenized. If a deleted deterministic token is re-tokenized with the same plaintext, a new token is generated.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tokens` | dict[str, str] | yes | Keys are user-defined labels; values are vault tokens to delete |
