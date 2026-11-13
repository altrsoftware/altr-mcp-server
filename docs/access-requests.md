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

List one page of access requests, newest first, as the console's access request list does. Only OPEN requests unless `status` says otherwise; the API filters on one status per call.

To get the next page, pass the response's `last_evaluated_key` unchanged as `exclusive_start_key`, with the same `status` and `requester`. Keep going until `last_evaluated_key` is absent: the last page can be empty and still carry one. Paging needs unified-policy 4.31.1 or later; earlier versions reject every key.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max requests to return, 1 to 100. Default: 100 |
| `status` | str | no | `OPEN` (default), `CLOSED_APPROVED`, `CLOSED_DENIED`, `CLOSED_CANCELLED` or `FAILED`. The API also accepts `NONE`, `PENDING_CREATION` and the `PENDING_*` states |
| `requester` | str | no | Only requests from this requester (exact name) |
| `sort` | str | no | `desc` (newest first, default) or `asc` |
| `exclusive_start_key` | dict or str | no | `last_evaluated_key` from the previous page, as returned (an object, or the same object as a JSON string) |

---

### get_access_request

Get one access request: who asked, for what, why, and its status.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | str | yes | Access request ID (UUID) |

---

### approve_access_request

Approve an OPEN access request. ALTR creates a Snowflake access management policy granting what was requested, linked to the request, and applies it asynchronously. The API refuses a request that isn't OPEN.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | str | yes | Access request ID (UUID) |
| `justification` | str | no | Reason recorded with the decision (up to 1000 characters) |

---

### deny_access_request

Deny an OPEN access request. The API refuses a request that isn't OPEN.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | str | yes | Access request ID (UUID) |
| `justification` | str | no | Reason recorded with the decision (up to 1000 characters) |
