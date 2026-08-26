# Error Handling

## Response Structure

All tools return a consistent structure:

```json
{"success": true, "data": {...}, "error": null}
```

## Error Types

### API Errors (4xx)

When the ALTR API returns a client error (400, 401, 403, 404), the tool still returns `success: true` at the tool level, but the `data` field contains the error:

```json
{
  "success": true,
  "data": {
    "success": false,
    "status_code": 400,
    "message": "Client error '400 Bad Request' for url '...'"
  },
  "error": null
}
```

Common status codes:

| Code | Meaning |
|------|---------|
| 400 | Bad request — invalid parameters or missing required fields |
| 401 | Unauthorized — invalid MAPI_KEY or MAPI_SECRET |
| 403 | Forbidden — API key lacks permission for this operation |
| 404 | Not found — resource doesn't exist or wrong ID |

### Retryable Errors (429, 5xx)

Transient errors (429 Too Many Requests, 500, 502, 503) are automatically retried up to 3 times with exponential backoff and jitter. If all retries fail:

```json
{
  "success": true,
  "data": {
    "success": false,
    "status_code": 503,
    "message": "Retry exhausted after 3 attempts (HTTP 503)"
  },
  "error": null
}
```

A `Retry-After` response header overrides the exponential backoff, clamped to `MAX_RETRY_AFTER` (default `60` seconds) so a server cannot park a call indefinitely. A value that is not a plain number of seconds — the HTTP-date form, or `inf`/`nan` — falls back to exponential backoff, which is itself bounded by the same ceiling.

Retry behavior is configured via `MAX_RETRIES` (default `3`, minimum `1`, counting total attempts rather than retries on top of the first, so `1` means "try once, never retry") or disabled entirely with `DISABLE_RETRY=true`. Each individual attempt is bounded by `REQUEST_TIMEOUT` (default `30` seconds, covering connect, read, write, and connection-pool acquisition).

Connections are pooled and shared across calls, so a `PoolTimeout` can surface on one tool call when many others are saturating the pool. See [the README configuration table](../README.md#configuration) for all four settings.

### Validation Errors

When a tool's parameters fail validation, the call raises an MCP `ToolError` with `isError: true`. The message names the field and what was wrong with it, and deliberately omits the value that was rejected — that value may be plaintext, and pydantic's own rendering embeds it as `input_value=`. See [Logging](logging.md).

Argument *shape* failures are caught before the tool body runs, by `ValidationRedactionMiddleware`. This path returns a bare message rather than the `{success, data, error}` envelope, because it is raised above the decorator that builds that envelope:

```
Validation failed: values: Input should be a valid dictionary
```

A tool's own field validators — masking rules, access-rate thresholds, sidecar bindings — build their own messages and surface through the unexpected-error path below, in the usual envelope:

```json
{
  "success": false,
  "data": null,
  "error": "Failed to add rules: ValueError: rules[0].role: Field required"
}
```

### Unexpected Errors

Any unhandled exception in a tool is caught, logged, and returned as a `ToolError`:

```json
{
  "success": false,
  "data": null,
  "error": "Failed to get tags: ConnectionError: Unable to reach API"
}
```

## Error Behavior Summary

| Scenario | `success` | MCP `isError` | Retried |
|----------|-----------|---------------|---------|
| 2xx response | `true` | `false` | No |
| 400 Bad Request | `true` (data.success=false) | `false` | No |
| 401 Unauthorized | `true` (data.success=false) | `false` | No |
| 403 Forbidden | `true` (data.success=false) | `false` | No |
| 404 Not Found | `true` (data.success=false) | `false` | No |
| 429 Too Many Requests | `true` (data.success=false) | `false` | Yes (3x) |
| 500/502/503 | `true` (data.success=false) | `false` | Yes (3x) |
| Validation error | `false` | `true` | No |
| Connection error | `false` | `true` | No |

## Notes

- API errors (4xx/5xx) do not raise MCP errors — the AI assistant sees them in `data` and can adapt its approach
- Only validation errors and unexpected exceptions raise MCP `ToolError` (with `isError: true`), which signals the client that something went wrong at the tool level
- All errors are logged via structlog with correlation IDs for debugging
