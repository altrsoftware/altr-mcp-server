# Telemetry Tools (9 tools)

Monitor ALTR agent and sidecar instances and their task telemetry. View running instances, inspect task status, and clean up stale telemetry data.

## Tool Summary

| Tool | Description |
|------|-------------|
| `get_agent_instances` | List running instances for an agent |
| `get_agent_instance` | Get details for a specific agent instance |
| `disconnect_agent_instance` | Disconnect an agent instance from ALTR's view |
| `get_agent_task_telemetry` | Get task telemetry for an agent |
| `get_sidecar_instances` | List running instances for a sidecar |
| `get_sidecar_instance` | Get details for a specific sidecar instance |
| `disconnect_sidecar_instance` | Disconnect a sidecar instance from ALTR's view |
| `get_task_telemetry` | Get telemetry for a specific task |
| `delete_task_telemetry` | Delete telemetry for a specific task |

## Tool Details

### get_agent_instances

List running instances for a specific ALTR agent.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | Agent UUID |
| `limit` | int | no | Max items to return |
| `contiguous_id` | str | no | Pagination token from a prior call |

---

### get_agent_instance

Get details for a specific agent instance.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | Agent UUID |
| `instance_id` | str | yes | Instance UUID |

---

### disconnect_agent_instance

Disconnect an agent instance from ALTR's view.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | Agent UUID |
| `instance_id` | str | yes | Instance UUID to disconnect |

---

### get_agent_task_telemetry

Get task telemetry for a specific agent. Returns task status, messages, and metadata for tasks assigned to this agent.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | Agent UUID |
| `limit` | int | no | Max items to return |
| `contiguous_id` | str | no | Pagination token from a prior call |

---

### get_sidecar_instances

List running instances for a specific sidecar.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sidecar_id` | str | yes | Sidecar UUID |
| `limit` | int | no | Max items to return |
| `contiguous_id` | str | no | Pagination token from a prior call |

---

### get_sidecar_instance

Get details for a specific sidecar instance.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sidecar_id` | str | yes | Sidecar UUID |
| `instance_id` | str | yes | Instance UUID |

---

### disconnect_sidecar_instance

Disconnect a sidecar instance from ALTR's view.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sidecar_id` | str | yes | Sidecar UUID |
| `instance_id` | str | yes | Instance UUID to disconnect |

---

### get_task_telemetry

Get telemetry for a specific task by its ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | str | yes | Task UUID |

---

### delete_task_telemetry

Delete telemetry for a specific task.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `task_id` | str | yes | Task UUID |
