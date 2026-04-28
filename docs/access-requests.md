# Access Request Tools (6 tools)

Submit, review, and manage data access requests. Requests follow an approval workflow: create a request, then approve, deny, or cancel it.

## Tool Summary

| Tool | Description |
|------|-------------|
| `create_access_request` | Submit a new access request |
| `get_access_requests` | List access requests in your organization |
| `get_access_request` | Get details for a specific request |
| `approve_access_request` | Approve a pending request |
| `deny_access_request` | Deny a pending request |
| `cancel_access_request` | Cancel a request you created |

## Tool Details

### create_access_request

Create a new access request for data access approval. Submits a request that must be approved before access is granted.

Rules follow the same format as access management policy rules:
- **actors**: list with `type` (`"role"`), `condition`, and `identifiers`
- **objects**: list with `type` (`"database"`, `"schema"`, `"table"`, `"view"`), `condition`, and `identifiers` or `fully_qualified_identifiers`
- **access**: list with `name` (`"read"` or `"write"`)

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `requester` | str | yes | Name of the person requesting access |
| `justification` | str | yes | Reason for the access request |
| `connection_id` | int | yes | ALTR connection ID for the target database |
| `rules` | list[dict] or str | yes | List of access rule objects, or a JSON string |
| `email` | str | no | Requester's email address |
| `role` | str | no | Requester's Snowflake role |
| `snowflake_metadata` | dict | no | Dict with `account_region`, `account_name`, and `organization_name` |

---

### get_access_requests

List access requests in your ALTR organization.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max requests to return (default 10) |
| `requester` | str | no | Filter by requester name |
| `status` | str | no | Filter by status: `OPEN`, `PENDING`, `PENDING_APPROVED`, `CLOSED_APPROVED`, `PENDING_DENIED`, `CLOSED_DENIED`, `PENDING_CANCELLED`, `CLOSED_CANCELLED`, `CLOSED`, `FAILED` |
| `sort` | str | no | Sort order by creation time: `"asc"` or `"desc"` |
| `exclusive_start_key` | str | no | Pagination token from a prior call |

---

### get_access_request

Get details for a specific access request.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | str | yes | Access request ID (UUID) |

---

### approve_access_request

Approve a pending access request.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | str | yes | Access request ID (UUID) |
| `justification` | str | yes | Reason for approving the request |

---

### deny_access_request

Deny a pending access request.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | str | yes | Access request ID (UUID) |
| `justification` | str | yes | Reason for denying the request |

---

### cancel_access_request

Cancel an access request you created.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | str | yes | Access request ID (UUID) |
| `justification` | str | yes | Reason for cancelling the request |
