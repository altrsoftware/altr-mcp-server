title: ALTR MCP Server Logging

# Logging

Every tool call is logged to stderr at `INFO` with its arguments, which is
what makes a session traceable. `LOG_LEVEL` sets the threshold and
`LOG_FORMAT` chooses between `console` (default) and `json`.

## What gets redacted

An argument is redacted when its value is a credential or user-supplied free
text. Identifiers, enums, and pagination cursors are logged in full, because
they are what you read a log line for.

| Redacted | Why |
|---|---|
| `values` | the plaintext being tokenized — `vault_tokenize(values={"ssn": ...})` is the secret itself |
| `text`, `comments`, `attestation`, `justification` | human free text, where unannounced PII arrives |
| `statement_text_contains` | an audit search term is a data value: someone hunting an SSN types the SSN |
| `connection_string` | a DSN embeds its password inline, as `user:pw@host` |
| anything ending `_password`, `_secret`, `_credential`, `_credentials`, `_private_key`, `_passphrase` | applied as a suffix rule, so the next credential-bearing argument is covered by construction |

Dictionary keys survive, so a line reads
`values={'ssn': '<redacted>', 'email': '<redacted>'}` — you keep which fields
were sent and lose the data. An argument that was omitted logs as `None`
rather than `<redacted>`, so "the caller left it out" stays distinguishable
from "a secret was sent and hidden".

**Tokens are not redacted.** `tokens`, `token`, `page_token` and
`next_page_token` are logged in full. A token exists to be handled freely —
that is what tokenizing produces — and ALTR's own Shield audit log is keyed by
token. The paging ones are cursors.

## Why redaction is keyed on the argument name

Not on the tool name. A list of tool names is only correct until the next tool
is added; a list of argument names covers a new tool the day it is written.
The suffix rule extends that further, so `*_password` needs no maintenance at
all.

## Where redaction applies

Argument data can reach a log by more than one route, so redaction is applied at
each of them:

- **The invocation line** (`tool_invoked`) — arguments are redacted as above.
- **Tracebacks.** Frame locals hold tool arguments, so both renderers are
  configured with `show_locals=False`.
- **Argument coercion.** Arguments are validated before the tool body runs, and
  a validation error names the value it rejected.
  `ValidationRedactionMiddleware` builds the caller-facing error from the field
  path and message only, and a logging filter scrubs rejected values from
  records emitted by dependencies.

Redacting one route and not the others would achieve nothing, which is why all
three are covered rather than just the obvious one.

## What is never logged

Tool results. `_summarize` emits only a count or `ok`, so a `vault_detokenize`
response full of plaintext logs as `3 items`. `MAPI_KEY` and `MAPI_SECRET` are
`SecretStr` and render as `**********` wherever they appear.
