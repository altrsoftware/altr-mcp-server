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

The `Retry-After` header is honored when present. Retry behavior can be configured via `MAX_RETRIES` (default 3) or disabled entirely with `DISABLE_RETRY=true`.

### Validation Errors

When tool parameters fail Pydantic validation (e.g. invalid masking rule format), the tool raises an MCP `ToolError` with `isError: true`:

```json
{
  "success": false,
  "data": null,
  "error": "Validation failed: 1 validation error for MaskingRule\nrole\n  Field required"
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
