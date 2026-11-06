# Access Request Tools (4 tools)

Review data access requests and approve or deny them, as the console does. Requests are filed from outside the console; approving one creates a Snowflake access management policy that grants what was asked.

## Tool Summary

| Tool | Description |
|------|-------------|
| `get_access_requests` | List access requests, OPEN ones by default |
| `get_access_request` | Get one access request |
| `approve_access_request` | Approve an OPEN request |
| `deny_access_request` | Deny an OPEN request |

## Tool Details

### get_access_requests

List access requests, newest first, as the console's access request list does. Only OPEN requests unless `status` says otherwise; the API filters on one status per call.

Returns at most 100 requests. When more match, the response carries `last_evaluated_key`, but the API can't take it back yet, so narrow the list with `status` or `requester` instead.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max requests to return, 1 to 100. Default: 100 |
| `status` | str | no | `OPEN` (default), `CLOSED_APPROVED`, `CLOSED_DENIED`, `CLOSED_CANCELLED` or `FAILED`. The API also accepts `NONE`, `PENDING_CREATION` and the `PENDING_*` states |
| `requester` | str | no | Only requests from this requester (exact name) |
| `sort` | str | no | `desc` (newest first, default) or `asc` |

---

### get_access_request

Get one access request: who asked, for what, why, and its status.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | str | yes | Access request ID (UUID) |

---

### approve_access_request

Approve an OPEN access request. ALTR creates a Snowflake access management policy granting what was requested, linked to the request, and applies it asynchronously. A request that isn't OPEN is refused before anything is sent.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | str | yes | Access request ID (UUID) |
| `justification` | str | no | Reason recorded with the decision (up to 1000 characters) |

---

### deny_access_request

Deny an OPEN access request. A request that isn't OPEN is refused before anything is sent.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | str | yes | Access request ID (UUID) |
| `justification` | str | no | Reason recorded with the decision (up to 1000 characters) |
