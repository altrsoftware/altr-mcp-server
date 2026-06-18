# Classification Tools (15 tools)

Discover sensitive data in your databases using automated classification. Manage classifiers (pattern-based detectors), group them into collections, and run classification jobs that scan columns for PII, financial data, and other sensitive patterns. Supports Snowflake, OLTP, and Databricks (GDLP only).

## Tool Summary

| Tool | Description |
|------|-------------|
| `get_classifiers` | List all available data classifiers |
| `create_classifier` | Create a custom data classifier |
| `delete_classifier` | Remove a custom classifier |
| `get_collections` | List classifier collections |
| `create_collection` | Create a classifier collection |
| `delete_collection` | Delete a classifier collection |
| `add_classifiers_to_collection` | Add classifiers to a collection |
| `remove_classifiers_from_collection` | Remove classifiers from a collection |
| `get_jobs` | Check status of classification jobs |
| `create_job` | Run an ALTR-native classification scan (Snowflake, by `database_id`) |
| `create_gdlp_job` | Run a GDLP (Google DLP) scan on a Snowflake connection |
| `create_databricks_job` | Run a GDLP scan on a Databricks connection |
| `create_oltp_job` | Run an on-demand scan on an OLTP sidecar repo via a classifier agent |
| `update_job_status` | Pause, cancel, or resume a job |
| `get_classification_report` | Get results from a completed job |

## Typical Workflow

### Snowflake / OLTP

1. Check existing classifiers with `get_classifiers` and collections with `get_collections`
2. Optionally create custom classifiers and collections
3. Get the target database ID with `get_database_id`
4. Run a scan with `create_job`
5. Wait 15-30+ minutes, then check status with `get_jobs`
6. When status is COMPLETED, view results with `get_classification_report`

### Databricks

1. Get the Databricks database ID with `get_database_id`
2. Run a GDLP scan with `create_databricks_job` (no collection selection needed)
3. Wait, then check status with `get_jobs`
4. When status is COMPLETED, view results with `get_classification_report`

### OLTP (sidecar repos)

1. Find the CLASSIFIER agent with `list_sc_agents` (`agent_type="CLASSIFIER"`), and the target repo and service user with `list_sc_repos` / `list_sc_service_users`
2. Run an on-demand scan with `create_oltp_job` (sidecar repos have no `database_id`, so `create_job` does not apply)
3. Wait, then check status with `get_jobs`
4. When status is COMPLETED, view results with `get_classification_report`

For Snowflake GDLP (Google DLP) scans, use `create_gdlp_job` instead of `create_job` — it skips collection selection and uses ALTR's built-in GDLP classifiers.

## Tool Details

### get_classifiers

List all available data classifiers (pattern-based detectors) in ALTR. Includes both ALTR-managed and custom classifiers.

**Parameters:** None

---

### create_classifier

Create a custom data classifier for detecting specific data patterns. Use when ALTR's built-in classifiers don't cover your data types.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `classifier_name` | str | yes | Unique name for the classifier |
| `description` | str | yes | Human-readable explanation of what it detects |
| `minimum_threshold` | int | yes | Percent (0-100) confidence required to consider a column a match |
| `pattern` | str | yes | Regex pattern used to match values |
| `sample_size` | int | yes | Number of values ALTR should sample per column |

---

### delete_classifier

Remove a custom classifier you created. Cannot delete ALTR-managed classifiers.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `classifier_name` | str | yes | Exact classifier name as returned by `get_classifiers` |

---

### get_collections

List classifier collections (groups of classifiers used for classification jobs). A collection is required when creating a job with `create_job`.

**Parameters:** None

---

### create_collection

Create a classifier collection to use for automated data discovery. Collections group classifiers together for classification jobs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_name` | str | yes | Unique name for the collection |
| `description` | str | no | Human-readable description. Default: `""` |

---

### delete_collection

Delete a classifier collection. Cannot delete collections in use by active or recent jobs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_name` | str | yes | Exact collection name as returned by `get_collections` |

---

### add_classifiers_to_collection

Add classifiers to an existing collection. All classifiers must already exist. ALTR-managed collections cannot have classifiers appended.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_name` | str | yes | Collection to add classifiers to |
| `classifier_names` | str or list[str] | yes | Classifier name(s) to add |

---

### remove_classifiers_from_collection

Remove classifiers from a collection.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_name` | str | yes | Collection to remove classifiers from |
| `classifier_names` | str or list[str] | yes | Classifier name(s) to remove |

---

### get_jobs

Check the status of classification jobs. Jobs run asynchronously and can take 10-30+ minutes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max jobs to return (default 50, max 50) |
| `contiguous_id` | str | no | Pagination token from a prior call |
| `status` | str | no | Filter by status: `RUNNING`, `PAUSED`, `COMPLETED`, `CANCELLED`, `FAILED` |
| `job_type` | str | no | Filter by type: `FULL`, `INCREMENTAL`, `RECLASSIFICATION` |
| `database_id` | int | no | Restrict to a specific database |
| `classification_type` | int | no | ALTR classification type code (1-5) |
| `order` | str | no | Sort order by start time: `asc` or `desc` (default `desc`) |

---

### create_job

Run an automated classification scan to discover sensitive data in a Snowflake or OLTP database. Jobs run asynchronously.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_type` | str | yes | Job type: `FULL`, `INCREMENTAL`, or `RECLASSIFICATION` |
| `database_id` | int | yes | Target database ID (from `get_databases` / `get_database_id`) |
| `collection_name` | str | yes | Classifier collection to use for this run |

---

### create_databricks_job

Run a GDLP classification scan on a Databricks connection. No classifier or collection selection — ALTR's built-in GDLP classifiers are used automatically. Jobs run asynchronously; use `get_jobs` to poll status and `get_classification_report` once complete.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `database_id` | int | yes | ALTR database ID for the Databricks connection (from `get_databases` / `get_database_id`) |

---

### create_gdlp_job

Run a GDLP (Google DLP) classification scan on a Snowflake connection. A separate job type from `create_job` — it does not use a classifier collection; ALTR's built-in GDLP classifiers are used automatically. Jobs run asynchronously; poll with `get_jobs` and fetch results with `get_classification_report`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `database_id` | int | yes | ALTR database ID for the Snowflake connection (from `get_databases` / `get_database_id`) |

---

### create_oltp_job

Run an on-demand classification scan on an OLTP database (Oracle, MSSQL, MySQL, PostgreSQL) via a sidecar classification agent. Use this for OLTP sidecar repos — `create_job` is Snowflake-only because it requires a numeric `database_id`, which sidecar repos do not have. Triggers an immediate one-off run (does not create a scheduled task). Jobs run asynchronously; poll with `get_jobs` and fetch results with `get_classification_report`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `agent_id` | str | yes | CLASSIFIER agent UUID (from `list_sc_agents` with `agent_type="CLASSIFIER"`) |
| `repo_name` | str | yes | Target sidecar repository name (from `list_sc_repos`) |
| `service_user_name` | str | yes | Repo service user the agent authenticates as (from `list_sc_service_users`) |
| `collection_name` | str | yes | Classifier collection to run |
| `classification_type` | int | no | ALTR classification type code. Default `5` |
| `sample_strategy` | str | no | Sampling strategy: `ROWS`, `METADATA`, or `COMBINED`. Default `ROWS` |
| `sample_size` | int | no | Number of values sampled per column. Default `1000` |
| `sample_type` | str | no | Sampling unit. Default `ROWS` |

---

### update_job_status

Control a running classification job (pause, cancel, or resume).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Job identifier to update |
| `status` | str | yes | New status: `PAUSED`, `CANCELLED`, or `RUNNING` |

---

### get_classification_report

Get detailed results from a completed classification job. Returns which columns were detected as containing sensitive data along with confidence scores. Only call after the job status is COMPLETED.

After reviewing results, check if needed Snowflake tags exist using `get_tags`. If tags are missing, create them in Snowflake before connecting with `connect_tag`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Job identifier from `create_job` or `get_jobs` |
