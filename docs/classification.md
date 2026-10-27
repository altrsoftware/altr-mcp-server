# Classification Tools (52 tools)

Discover sensitive data in your databases using automated classification. Manage classifiers, group them into collections, and run classification jobs that scan columns for PII, financial data, and other sensitive patterns. Supports Snowflake, OLTP, and Databricks (GDLP only). Single files can also be classified directly with `scan_object`.

## Tool Summary

| Tool | Description |
|------|-------------|
| `get_classifiers` | List all available data classifiers |
| `get_classifier` | Get details for a single classifier |
| `create_classifier` | Create a custom classifier defined by a compound ruleset |
| `update_classifier` | Update an existing custom classifier |
| `delete_classifier` | Remove a custom classifier |
| `get_collections` | List classifier collections |
| `get_collection` | Get details for a single collection |
| `create_collection` | Create a classifier collection |
| `update_collection` | Update a collection's description |
| `delete_collection` | Delete a classifier collection |
| `get_collection_classifiers` | List classifiers in a collection |
| `add_classifiers_to_collection` | Add classifiers to a collection |
| `remove_classifiers_from_collection` | Remove classifiers from a collection |
| `add_classifier_to_collections` | Add one classifier to several collections |
| `remove_classifier_from_collections` | Remove one classifier from several collections |
| `list_classifier_tags` | List the key:value tags in use across classifiers |
| `import_altr_managed_classifiers` | Sync an ALTR-managed collection, or all of them, into your org |
| `get_altr_managed_timestamp` | Check if a newer version of an ALTR-managed collection is available |
| `list_altr_managed_classifiers` | List the classifiers in an ALTR-managed collection |
| `get_jobs` | Check status of classification jobs |
| `get_active_jobs` | List all currently running or paused jobs |
| `get_job` | Get details for a single job |
| `get_job_summary` | Get per-classifier detection counts for a completed job |
| `list_report_groups` | List reports grouped by collection, method and datasource |
| `list_report_group_runs` | List a report group's runs |
| `get_job_exclusions` | Show which exclusion paths a job applied and which matched nothing |
| `create_snowflake_job` | Run a classification scan on a Snowflake connection (ALTR Hosted or In-Warehouse) |
| `create_databricks_job` | Run a classification scan on a Databricks connection |
| `create_oltp_job` | Run a classification scan on a database repository through an agent |
| `create_file_classification_job` | Run a classification scan on an S3 or filesystem repository through an agent |
| `update_job_status` | Pause, cancel, or resume a job |
| `get_job_findings` | List databases with detected columns (findings tree entry point) |
| `get_job_findings_schemas` | List schemas with detections in a database |
| `get_job_findings_tables` | List tables with detections in a schema |
| `get_job_findings_columns` | List detected columns in a table |
| `get_job_findings_classifiers` | List classifiers that fired on a column |
| `get_job_findings_lineage` | Get compound-ruleset evaluation trace for a classifier on a column |
| `get_job_findings_leaves` | List every finding in a job in one paginated stream |
| `record_job_decision` | Approve or reject classification findings |
| `get_job_decisions` | List review decisions recorded for a job |
| `revoke_job_decisions` | Remove previously recorded decisions |
| `record_bulk_job_decision` | Approve or reject every undecided finding matching a filter |
| `revoke_bulk_job_decision` | Undo a bulk decision |
| `get_job_review_status` | Get approved/rejected/pending counts for a job |
| `confirm_job_report` | Confirm a review-gated job's decisions and release its report |
| `cancel_job_report` | Cancel a review-gated job before its report is confirmed |
| `get_classification_report` | Download full results from a completed job |
| `scan_object` | Classify a file's contents (up to 128 KiB) and return the summary |
| `list_scan_objects` | List past file scans |
| `get_scan_object` | Get a file scan's summary |
| `get_scan_object_map` | Get a file scan's token map |
| `get_scan_object_supported_types` | List the content types file scans detect |

## Typical Workflow

Every scan runs a collection of classifiers, as in the console's Classify Data wizard. The collection must contain at least one classifier. Where the scan runs depends on the source:

| Source | Tool | Processing location |
|---|---|---|
| Snowflake | `create_snowflake_job` | `altr_hosted` (default): ALTR evaluates the classifiers in its cloud. `in_warehouse`: the scan runs in Snowflake on your compute and skips Google DLP, Content Type and Amazon Comprehend conditions |
| Databricks | `create_databricks_job` | ALTR Hosted |
| Database repositories | `create_oltp_job` | Agent, in your network |
| S3 and filesystem repositories | `create_file_classification_job` | Agent, in your network |

There is no separate Google DLP job: Google DLP runs when the collection has Google DLP conditions and the scan is ALTR Hosted. Every scan evaluates all condition types its location supports, samples 1000 rows per column unless told otherwise, and is review-gated (`requires_review` true), as in the console.

1. Check classifiers with `get_classifiers` and collections with `get_collections`, or import ALTR-managed collections with `import_altr_managed_classifiers`
2. Find the source: `get_databases` for Snowflake and Databricks, or `list_sc_repos`, `list_sc_agents` (`agent_type="CLASSIFIER"`) and `list_sc_service_users` for repositories
3. Start the scan with the tool for the source, optionally narrowed with a scope and exclusions
4. Wait 15-30+ minutes, checking with `get_job` or `get_jobs`. If you used exclusions, check `get_job_exclusions`
5. Review the findings (below), then read results with `get_job_findings` or `get_classification_report`

### Review-gated jobs

Scans are review-gated unless `requires_review=false`. A review-gated job holds its report:

1. When the job reaches AWAITING_REVIEW, browse findings with `get_job_findings` or `get_job_findings_leaves`
2. Decide findings with `record_job_decision`, or many at once with `record_bulk_job_decision` (run it with `dry_run=true` first to see the counts)
3. Check that nothing is pending with `get_job_review_status`
4. Release the report with `confirm_job_report`; decisions are then locked. Poll `get_job` until COMPLETED, then use `get_classification_report`

To abandon a review instead, call `cancel_job_report`.

## Condition Types

A classifier's conditions target these values. ALTR Hosted Snowflake scans evaluate all of them; Databricks and repository scans evaluate all but `SNOWFLAKE_NATIVE`. In-Warehouse Snowflake scans skip `GDLP`, `CONTENT_TYPE` and `AMAZON_COMPREHEND` conditions.

| Value | Description |
|-------|-------------|
| `ROW_DATA` | Regex matching against sampled column values |
| `METADATA` | Evaluate column name/description against classifier rules |
| `COLUMN_LOCATION` | Scope evaluation by database/schema/table location |
| `CONTENT_TYPE` | Detect structured/binary content formats (JSON, PDF, ZIP, etc.) |
| `DATA_LENGTH` | Evaluate UTF-8 byte length of column values |
| `COLUMN_SIZE` | Evaluate the declared column size |
| `AMAZON_COMPREHEND` | AWS Comprehend PII entity detection |
| `GDLP` | Google DLP info-type detection |
| `SNOWFLAKE_NATIVE` | Snowflake's own classification tags (`SEMANTIC_CATEGORY` / `PRIVACY_CATEGORY`) on Snowflake jobs |
| `ENTROPY` | Flag columns whose sampled values look like secret keys (needs row sampling) |

## Classification Types

Jobs started from the console or these tools are ALTR Native. Older jobs carry other codes, which `get_jobs` and `get_active_jobs` can filter on:

| Code | Description |
|------|-------------|
| `1` | Google DLP; ALTR Hosted Snowflake and Databricks scans also report this code |
| `2` | Snowflake Native |
| `3` | Snowflake Object Tag Import |
| `4` | Snowflake Native + Tag Import |
| `5` | ALTR Native |
| `6` | GDLP BYOK (bring-your-own-key) |

## Tool Details

### get_classifiers

List all available data classifiers in ALTR. Includes both ALTR-managed and custom classifiers.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prefix` | str | no | Only classifiers whose names start with this, e.g. `email` matches `email_address` |
| `order_by` | str | no | `name` or `collection_count` (how many collections use each classifier) |
| `sort_order` | str | no | `asc` or `desc` |
| `exclude_collection` | str | no | Leave out classifiers already in this collection |

---

### get_classifier

Get details for a single classifier by name.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `classifier_name` | str | yes | Exact classifier name as returned by `get_classifiers` |

---

### create_classifier

Create a custom data classifier defined by a compound ruleset: one or more conditions (ROW_DATA regex, METADATA, AMAZON_COMPREHEND, DATA_LENGTH, CONTENT_TYPE and more) combined with AND/OR. A plain regex classifier is a ruleset with a single ROW_DATA condition carrying the pattern and its `minimum_threshold`. Sampling is set on the job, not the classifier.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `classifier_name` | str | yes | Unique name for the classifier |
| `compound_ruleset` | dict | yes | Nested AND/OR condition tree |
| `description` | str | no | Human-readable explanation of what it detects |
| `tags` | list[str] | no | key:value tags describing the classifier, e.g. `["type:ssn"]`. `list_classifier_tags` shows the tags already in use |

**Compound ruleset structure:**
```json
{
  "operator": "AND",
  "conditions": [
    {
      "target": "ROW_DATA",
      "pattern": "\\d{3}-\\d{2}-\\d{4}",
      "comparator": "matches",
      "minimum_threshold": 70
    },
    {
      "target": "METADATA",
      "pattern": "ssn",
      "comparator": "contains"
    }
  ]
}
```

**AMAZON_COMPREHEND leaf fields:** `entity_type` (e.g. `"SSN"`, `"CREDIT_DEBIT_NUMBER"`, `"EMAIL"`), `minimum_score` (0.0–1.0, default `0.5`).

**METADATA leaf fields:** `comparator` (`matches`/`contains`/`equals`/`starts_with`/`ends_with`), `pattern`.

**DATA_LENGTH / COLUMN_SIZE leaf fields:** `length` or `size`, numeric `comparator` (`greater_than`/`less_than`/`equals`/etc.), optional `trim`.

**ENTROPY leaf fields** (flags values that look like secret keys): `minimum_evidence_bits`, `minimum_key_bits`, `alphabet_classes`, `decode_base64`, `cumulative`.

Always set `minimum_threshold` on ROW_DATA leaves. All conditions support `negated: true`.

---

### update_classifier

Update an existing custom classifier. Only provided fields are changed. Passing `compound_ruleset` also removes any legacy top-level pattern, so the ruleset alone decides matches. To keep a legacy regex, include it as a ROW_DATA condition with its own `minimum_threshold`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `classifier_name` | str | yes | Exact classifier name to update |
| `description` | str | no | Updated description |
| `compound_ruleset` | dict | no | Updated compound ruleset |
| `tags` | list[str] | no | Replaces the classifier's key:value tags. `[]` clears them |

---

### delete_classifier

Remove a custom classifier you created. Cannot delete ALTR-managed classifiers.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `classifier_name` | str | yes | Exact classifier name as returned by `get_classifiers` |

---

### get_collections

List classifier collections (groups of classifiers used for classification jobs). Every scan runs a collection.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sort_order` | str | no | `asc` or `desc` by collection name |

---

### get_collection

Get details for a single collection by name.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_name` | str | yes | Exact collection name as returned by `get_collections` |

---

### create_collection

Create a classifier collection to use for automated data discovery.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_name` | str | yes | Unique name for the collection |
| `description` | str | no | Human-readable description. Default: `""` |

---

### update_collection

Update a collection's description.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_name` | str | yes | Exact collection name to update |
| `description` | str | yes | Updated description |

---

### delete_collection

Delete a classifier collection. Cannot delete collections in use by active or recent jobs.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_name` | str | yes | Exact collection name as returned by `get_collections` |

---

### get_collection_classifiers

List classifiers that belong to a collection.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection_name` | str | yes | Collection name to inspect |
| `limit` | int | no | Max items to return |
| `contiguous_id` | str | no | Pagination token |
| `prefix` | str | no | Only classifiers whose names start with this |
| `sort_order` | str | no | `asc` or `desc` by classifier name |

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

### add_classifier_to_collections

Add one classifier to several collections in a single call, the reverse of `add_classifiers_to_collection`. All collections must exist and not already contain it. ALTR-managed collections cannot be added to.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `classifier_name` | str | yes | Classifier to add |
| `collection_names` | str or list[str] | yes | Collection name(s) to add it to |

---

### remove_classifier_from_collections

Remove one classifier from several collections in a single call. It must currently be in each one. Collections whose names start with "ALTR" cannot have classifiers removed.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `classifier_name` | str | yes | Classifier to remove |
| `collection_names` | str or list[str] | yes | Collection name(s) to remove it from |

---

### list_classifier_tags

List the key:value tags in use across your classifiers, both on classifiers and on their ruleset conditions, with how many classifiers use each and where. These are classifier tags, not the Snowflake tags `get_tags` lists.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `key` | str | no | Only tags with this exact key (the part before `:`) |
| `prefix` | str | no | Only tags whose full `key:value` starts with this |
| `limit` | int | no | Max tags per page (default 100, max 500) |
| `contiguous_id` | str | no | Pagination token |

---

### import_altr_managed_classifiers

Import an ALTR-managed collection and create or update it in your org. ALTR maintains curated classifiers for common sensitive data types (SSN, credit cards, email, phone numbers, etc.) in several managed collections. Importing is idempotent. Use `get_altr_managed_timestamp` first to check whether an update is available.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection` | str | no | Managed collection slug: `regex` (default, the "ALTR Managed" collection), `gdlp`, `aws-comprehend`, `snowflake-native`, `stoplight`, or `all` for every managed collection |

---

### get_altr_managed_timestamp

Check whether a newer version of an ALTR-managed collection is available. Returns the latest available version timestamp alongside the version installed in your org.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `collection` | str | no | Managed collection slug: `regex` (default, the "ALTR Managed" collection), `gdlp`, `aws-comprehend`, `snowflake-native`, `stoplight`, or `all` for every managed collection in one call |

---

### list_altr_managed_classifiers

List available ALTR-managed (prebuilt) classifiers. Shows the canonical set maintained by ALTR; call `import_altr_managed_classifiers` to sync them into your org.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max items to return |
| `contiguous_id` | str | no | Pagination token |
| `collection` | str | no | Managed collection slug: `regex` (default, the "ALTR Managed" collection), `gdlp`, `aws-comprehend`, `snowflake-native`, `stoplight` |

---

### get_jobs

Check the status of classification jobs. Jobs run asynchronously and can take 10-30+ minutes.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max jobs to return (default 50, max 50) |
| `contiguous_id` | str | no | Pagination token from a prior call |
| `status` | str | no | Filter by status: `RUNNING`, `PAUSED`, `COMPLETED`, `CANCELLED`, `FAILED` |
| `job_type` | str | no | Filter by type: `FULL` or `INCREMENTAL` |
| `database_id` | int | no | Restrict to a specific database |
| `agent_id` | str | no | Restrict to jobs run by a specific CLASSIFIER agent UUID |
| `classification_type` | int | no | Filter by type code (1–6; see [Classification Types](#classification-types)) |
| `order` | str | no | Sort order by start time: `asc` or `desc` (default `desc`) |

---

### get_active_jobs

List all currently active (non-terminal) classification jobs: created, running, paused or resumed, cancelling, building their report, or waiting for review. Faster than `get_jobs` when you just want to see what's in flight.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max jobs to return |
| `contiguous_id` | str | no | Pagination token |
| `database_id` | int | no | Filter by database ID |
| `agent_id` | str | no | Filter by agent UUID |
| `status` | str | no | One active status: `CREATED`, `RESUMED`, `PAUSED`, `RUNNING`, `PENDING_CANCEL`, `UPLOADING_REPORT`, `PROCESSING_REPORT`, `PROCESSING_FINDINGS`, `AWAITING_REVIEW` |
| `job_type` | str | no | `FULL` or `INCREMENTAL` |
| `classification_type` | int | no | Classification type code: 1 Google DLP, 2 Snowflake Native, 3 Snowflake Tag Import, 4 Snowflake Native + Tag Import, 5 ALTR Native, 6 GDLP BYOK |
| `order` | str | no | `desc` (newest first, default) or `asc` |

---

### get_job

Get details for a single classification job by ID.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Job identifier from a create-job tool or `get_jobs` |

---

### get_job_summary

Get an inline per-classifier detection count summary for a completed job. Faster than `get_classification_report` because it skips the presigned S3 round-trip.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | COMPLETED job identifier |

---

### list_report_groups

List classification reports grouped by collection, classification method and datasource, ordered by each group's latest run. Each group carries its latest run; page older runs with `list_report_group_runs`. Keep filters the same across pages and page until `contiguous_id` is absent: a filtered page can be empty while more matches remain.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max groups per page (default 50, max 50) |
| `contiguous_id` | str | no | Pagination token |
| `status` | str or list[str] | no | Latest-run report status: `needs_review`, `in_progress`, `confirmed`, `failed` |
| `connection_type` | str or list[str] | no | Connection types, e.g. `"databricks"` or `["databricks", "mysql"]` |

---

### list_report_group_runs

List a report group's classification runs, newest first.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `group_id` | str | yes | `group_id` from `list_report_groups` |
| `limit` | int | no | Max runs per page (default 50, max 50) |
| `contiguous_id` | str | no | Pagination token |

---

### get_job_exclusions

Show which exclusion paths a job applied. `applied` lists exclusions that covered at least one object, and `unmatched` lists those that covered nothing. A non-empty `unmatched` means the scan sampled more than intended, for example because of a mistyped path. When `applied_unavailable` or `match_unavailable` is true, that list is unknown rather than empty.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Job identifier |

---

### create_snowflake_job

Run a classification scan on a Snowflake connection, as the console's Classify Data wizard does. Sends `job_type` `FULL`, every condition type, and `classification_type` `gdlp` for ALTR Hosted or `altr_native` for In-Warehouse. A scope or exclusions use the connection's database name, looked up from the connection.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `database_id` | int | yes | Snowflake connection ID (from `get_databases`) |
| `collection_name` | str | yes | Collection to run; it must contain classifiers |
| `processing_location` | str | no | `altr_hosted` (default) or `in_warehouse` |
| `schema` | str | no | Scan only this schema |
| `table` | str | no | Scan only this table (requires `schema`) |
| `exclude` | str or list[str] | no | Objects to skip, relative to the scope: a schema, or `schema.table`. Without `schema`, they apply to the whole database. A name that matches nothing is not an error; check `get_job_exclusions` afterwards. At most 100 |
| `sample_type` | str | no | `ROWS` (a row count, default) or `PERCENT` |
| `sample_size` | int | no | Rows to sample per column (default `1000`), or a percentage from 1 to 100 (default `5`) with `PERCENT` |
| `requires_review` | bool | no | Hold the report for human review until `confirm_job_report` runs. Default `true`, as in the console (see [Review-gated jobs](#review-gated-jobs)) |

---


### create_databricks_job

Run a classification scan on a Databricks connection, as the console does. Databricks scans are ALTR Hosted. Sends every condition type except `SNOWFLAKE_NATIVE`, and no `classification_type` or `job_type`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `database_id` | int | yes | Databricks connection ID (from `get_databases`) |
| `collection_name` | str | yes | Collection to run; it must contain classifiers |
| `catalog` | str | no | Scan only this Unity Catalog catalog |
| `schema` | str | no | Scan only this schema (requires `catalog`) |
| `table` | str | no | Scan only this table (requires `schema`) |
| `exclude` | str or list[str] | no | Objects to skip, relative to the scope: a schema, or `schema.table` under a catalog. At most 100 |
| `sample_type` | str | no | `ROWS` (a row count, default) or `PERCENT` |
| `sample_size` | int | no | Rows to sample per column (default `1000`), or a percentage from 1 to 100 (default `5`) with `PERCENT` |
| `requires_review` | bool | no | Hold the report for human review until `confirm_job_report` runs. Default `true`, as in the console (see [Review-gated jobs](#review-gated-jobs)) |

---

### create_oltp_job

Run a classification scan on a database repository through a classifier agent, as the console does. Supports Oracle, MSSQL, PostgreSQL, MySQL, MongoDB and Cassandra repositories; for S3 and filesystem repositories use `create_file_classification_job`. Sends `classification_type` `5` (ALTR Native) and every condition type except `SNOWFLAKE_NATIVE`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | Repository name (from `list_sc_repos`) |
| `agent_id` | str | yes | CLASSIFIER agent ID (from `list_sc_agents`) |
| `service_user_name` | str | yes | Repository service user the agent connects as (from `list_sc_service_users`) |
| `collection_name` | str | yes | Collection to run; it must contain classifiers |
| `database` | str | no | Scan only this database. On Oracle this is the connection's service name |
| `schema` | str | no | Scan only this schema (requires `database`). MySQL, MongoDB and Cassandra have no schema level |
| `table` | str | no | Scan only this table or collection. Requires `database`, and `schema` on Oracle, MSSQL and PostgreSQL |
| `exclude` | str or list[str] | no | Objects to skip, relative to the scope: `schema` or `schema.table` under a database, or a table name on MySQL, MongoDB and Cassandra. At most 100 |
| `sid` | str | no | Oracle only, for an unscoped scan: the SID to connect with |
| `service_name` | str | no | Oracle only: the service name to connect with. A scoped Oracle scan always connects by service name, which is also its database |
| `sample_type` | str | no | `ROWS` (a row count, default) or `PERCENT` |
| `sample_size` | int | no | Rows to sample per column (default `1000`), or a percentage from 1 to 100 (default `5`) with `PERCENT` |
| `requires_review` | bool | no | Hold the report for human review until `confirm_job_report` runs. Default `true`, as in the console (see [Review-gated jobs](#review-gated-jobs)) |

On MySQL, MongoDB and Cassandra a table scope repeats the database in `schema`, as the console sends it.

---

### create_file_classification_job

Run a classification scan on an S3 or filesystem repository through a classifier agent, as the console does. File contents never leave the agent's network. Always sends `file_options`; sends `metadata_map` only when it differs from the default.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `repo_name` | str | yes | S3 or filesystem repository (from `list_sc_repos`) |
| `agent_id` | str | yes | CLASSIFIER agent ID (from `list_sc_agents`) |
| `service_user_name` | str | yes | Repository service user (from `list_sc_service_users`) |
| `collection_name` | str | yes | Collection to run; it must contain classifiers |
| `paths` | str or list[str] | no | Scan only these prefixes or directories, relative to the repository root. At most 50 |
| `exclude_paths` | str or list[str] | no | Prefixes or directories to skip, relative to the repository root. At most 100 |
| `content_classification` | bool | no | Classify file contents (default `true`); `false` maps files and fields only |
| `full_file_scan` | bool | no | Read every value of every file instead of a sample (default `false`) |
| `include_glob` | str | no | Only files whose paths match this glob |
| `exclude_glob` | str | no | Skip files whose paths match this glob |
| `max_files` | int | no | Cap on files listed (agent default 100000) |
| `max_file_bytes` | int | no | Bytes read per file, up to 67108864 (64 MiB; agent default 10 MiB) |
| `scan_mode` | str | no | S3 only: `CRAWL` (default) or `GLUE` |
| `glue_crawler` | str | no | S3 with `GLUE`: the Glue crawler to start |
| `glue_start_crawler` | bool | no | S3 with `GLUE`: run the crawler when the catalog is empty |
| `sniff_bytes` | bool | no | S3 only: detect content types from file bytes (default `true`) |
| `metadata_map` | str | no | How field names are kept in results: `hashed` (default), `plaintext` or `none` |
| `metadata_map_by_format` | dict | no | Per-format overrides for `csv`, `json`, `xml`, `html` or `yaml` |
| `requires_review` | bool | no | Hold the report for human review until `confirm_job_report` runs. Default `true`, as in the console (see [Review-gated jobs](#review-gated-jobs)) |

---

### update_job_status

Control a running classification job (pause, cancel, or resume).

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Job identifier to update |
| `status` | str | yes | New status: `PAUSED`, `CANCELLED`, or `RUNNING` |

---

### get_job_findings

Entry point for navigating classification results hierarchically. Returns databases that contain detected columns. Drill down with `get_job_findings_schemas` → tables → columns → classifiers. Prefer this over `get_classification_report` when you want to interactively filter or explore results.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Identifier of a COMPLETED job, or of a review-gated job at AWAITING_REVIEW |
| `limit` | int | no | Max databases to return |
| `page_token` | str | no | Pagination token |
| `classifier_name` | str or list[str] | no | Filter to databases with detections by these classifier(s) |
| `confirmed_status` | str or list[str] | no | Filter by review status: `approved`, `rejected`, or `pending` |
| `include_column_status_counts` | bool | no | Include approved/rejected/pending counts per database |
| `confidence` | str or list[str] | no | Only findings of these confidence tiers: `HIGH`, `MEDIUM`, `LOW`. Counts are limited the same way |

---

### get_job_findings_schemas

List schemas with detected columns in a database. Second level of the findings tree.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Identifier of a COMPLETED job, or of a review-gated job at AWAITING_REVIEW |
| `database` | str | yes | Database name from `get_job_findings` |
| `limit` | int | no | Max schemas to return |
| `page_token` | str | no | Pagination token |
| `classifier_name` | str or list[str] | no | Filter by classifier name(s) |
| `confirmed_status` | str or list[str] | no | Filter by review status: `approved`, `rejected`, `pending` |
| `confidence` | str or list[str] | no | Only findings of these confidence tiers: `HIGH`, `MEDIUM`, `LOW`. Counts are limited the same way |

---

### get_job_findings_tables

List tables with detected columns in a schema. Third level of the findings tree.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Identifier of a COMPLETED job, or of a review-gated job at AWAITING_REVIEW |
| `database` | str | yes | Database name |
| `schema` | str | yes | Schema name from `get_job_findings_schemas` |
| `limit` | int | no | Max tables to return |
| `page_token` | str | no | Pagination token |
| `classifier_name` | str or list[str] | no | Filter by classifier name(s) |
| `confirmed_status` | str or list[str] | no | Filter by review status: `approved`, `rejected`, `pending` |
| `confidence` | str or list[str] | no | Only findings of these confidence tiers: `HIGH`, `MEDIUM`, `LOW`. Counts are limited the same way |

---

### get_job_findings_columns

List detected columns in a table. Fourth level of the findings tree.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Identifier of a COMPLETED job, or of a review-gated job at AWAITING_REVIEW |
| `database` | str | yes | Database name |
| `schema` | str | yes | Schema name |
| `table` | str | yes | Table name from `get_job_findings_tables` |
| `limit` | int | no | Max columns to return |
| `page_token` | str | no | Pagination token |
| `classifier_name` | str or list[str] | no | Filter by classifier name(s) |
| `confirmed_status` | str or list[str] | no | Filter by review status: `approved`, `rejected`, `pending` |
| `confidence` | str or list[str] | no | Only findings of these confidence tiers: `HIGH`, `MEDIUM`, `LOW`. Counts are limited the same way |

---

### get_job_findings_classifiers

List classifiers that fired on a specific column. Use `get_job_findings_lineage` to see why a specific classifier did or did not fire.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Identifier of a COMPLETED job, or of a review-gated job at AWAITING_REVIEW |
| `database` | str | yes | Database name |
| `schema` | str | yes | Schema name |
| `table` | str | yes | Table name |
| `column` | str | yes | Column name from `get_job_findings_columns` |
| `limit` | int | no | Max classifiers to return |
| `page_token` | str | no | Pagination token |
| `confirmed_status` | str or list[str] | no | Filter by review status: `approved`, `rejected`, `pending` |
| `classifier_name` | str or list[str] | no | Only these classifier(s) |
| `confidence` | str or list[str] | no | Only findings of these confidence tiers: `HIGH`, `MEDIUM`, `LOW`. Counts are limited the same way |

---

### get_job_findings_lineage

Get the full compound-ruleset evaluation trace for a classifier on a specific column. Shows which conditions evaluated, which matched, and why the classifier did or did not fire. Useful for debugging custom classifiers or inspecting AMAZON_COMPREHEND / METADATA condition results.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Identifier of a COMPLETED job, or of a review-gated job at AWAITING_REVIEW |
| `database` | str | yes | Database name |
| `schema` | str | yes | Schema name |
| `table` | str | yes | Table name |
| `column` | str | yes | Column name |
| `classifier_name` | str | yes | Classifier name to inspect |

---

### get_job_findings_leaves

List every finding in a job in one paginated stream, one row per (database, schema, table, column, classifier), ordered by full path. Each row carries the finding count, average match rate, whether it is new, and its resolved review status. Use this to see a whole job at once instead of walking the tree. File sources also return crawl records, with an empty `classifier_name` and no `confirmed_status`; they are not findings and need no decision.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Job identifier |
| `limit` | int | no | Max rows per page (default 100, max 1000) |
| `page_token` | str | no | `next_page_token` from a prior call |
| `confidence` | str or list[str] | no | Keep only these confidence tiers: `HIGH`, `MEDIUM`, `LOW` |

---

### record_job_decision

Approve or reject classification findings in a job. Decisions can be scoped from the entire job down to a specific classifier on a specific column. Broader scopes apply to all columns and classifiers within.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Identifier of a COMPLETED job, or of a review-gated job at AWAITING_REVIEW |
| `confirmed_status` | str | yes | Decision: `approved` or `rejected` |
| `database` | str | no | Scope to this database |
| `schema` | str | no | Scope to this schema (requires `database`) |
| `table` | str | no | Scope to this table (requires `schema`) |
| `column` | str | no | Scope to this column (requires `table`) |
| `classifier_name` | str | no | Scope to this classifier (requires `column`) |

---

### get_job_decisions

List human review decisions recorded for a classification job.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Job identifier |
| `database` | str | no | Filter to this database |
| `schema` | str | no | Filter to this schema |
| `table` | str | no | Filter to this table |
| `column` | str | no | Filter to this column |
| `limit` | int | no | Max decisions to return |
| `page_token` | str | no | Pagination token |

---

### revoke_job_decisions

Remove previously recorded review decisions. Revoked findings return to `pending` status. Scope works the same as `record_job_decision`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Job identifier |
| `database` | str | no | Scope to this database |
| `schema` | str | no | Scope to this schema |
| `table` | str | no | Scope to this table |
| `column` | str | no | Scope to this column |
| `classifier_name` | str | no | Scope to this classifier |

---

### record_bulk_job_decision

Approve or reject every undecided finding that matches a filter: the given classifiers, optionally narrowed by confidence tier and by a database, schema and table path. Findings that already have a decision are left alone, and each covered finding can still be overridden with `record_job_decision`. Returns the matched counts, plus a `bulk_decision_id` when something was recorded (not on a dry run or when nothing matched). `classifier_names` must name at least one classifier.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Job identifier |
| `confirmed_status` | str | yes | Decision: `approved` or `rejected` |
| `classifier_names` | list[str] | yes | Classifiers whose findings to decide |
| `confidence` | list[str] | no | Keep only these confidence tiers: `HIGH`, `MEDIUM`, `LOW` |
| `database` | str | no | Limit to this database |
| `schema` | str | no | Limit to this schema (requires `database`) |
| `table` | str | no | Limit to this table (requires `schema`) |
| `dry_run` | bool | no | Return the counts without recording anything (default false) |

---

### revoke_bulk_job_decision

Undo a bulk decision. Revokes every decision it still covers; a finding decided individually afterwards keeps that individual decision.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Job identifier |
| `bulk_decision_id` | str | yes | `bulk_decision_id` returned by `record_bulk_job_decision` |

---

### get_job_review_status

Get the review progress for a job — total/approved/rejected/pending counts across all findings.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Identifier of a COMPLETED job, or of a review-gated job at AWAITING_REVIEW |

---

### confirm_job_report

Confirm the review of a review-gated job (created with `requires_review=true`) and release its report. Every finding must have a decision; check with `get_job_review_status` first. Report generation then runs in the background and decisions are locked. Poll `get_job` until COMPLETED, then read the report with `get_classification_report`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Job identifier |

---

### cancel_job_report

Cancel a review-gated job that is still being reviewed. The job moves to CANCELLED and its review data is discarded. A job whose report has already been confirmed cannot be cancelled this way.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Job identifier |

---

### get_classification_report

Download full results from a completed classification job as JSON. Returns which columns were detected as containing sensitive data along with confidence scores. For interactive exploration, prefer `get_job_findings`.

After reviewing results, check if needed Snowflake tags exist using `get_tags`. If tags are missing, create them in Snowflake before connecting with `connect_tag`.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | str | yes | Job identifier from a create-job tool or `get_jobs` |

---

### scan_object

Classify a file's contents synchronously, up to 128 KiB, and return the scan summary. The content is processed in memory and not stored; the summary and token map are kept, so read the map with `get_scan_object_map` and the returned `request_id`. Pass exactly one of `content` and `content_base64`, and choose what to scan with:

- `collection_name`: every classifier in the collection.
- `collection_name` and `classifier_name`: one classifier from the collection. Add `classifier` to test an edited definition (`pattern`, `compound_ruleset`, `minimum_threshold`, `attributes`) in place of the saved one without saving it.
- `classifier` alone: an unsaved classifier (`classifier_name`, `pattern` and/or `compound_ruleset`, `minimum_threshold`, `attributes`), with no collection needed.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `content` | str | one of | File contents as text |
| `content_base64` | str | one of | File contents, base64-encoded, for binary files |
| `collection_name` | str | no | Collection to scan with |
| `classifier_name` | str | no | One classifier from `collection_name` |
| `classifier` | dict | no | An unsaved classifier definition, as above |
| `file_name` | str | no | Original file name, echoed in the results |
| `include_all_tokens` | bool | no | Include tokens no classifier matched in the map (default false) |
| `include_lineage` | bool | no | Show how each classifier's conditions decided each match |
| `metadata_map` | dict | no | How structural names are kept: `{"default": "hashed"\|"plaintext"\|"none", "by_format": {"csv": ...}}` |

`content` and `content_base64` are redacted from the log, like other arguments that carry data.

---

### list_scan_objects

List past `scan_object` scans, newest first.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | no | Max scans per page (default 50, max 50) |
| `contiguous_id` | str | no | Pagination token |
| `status` | str | no | `COMPLETED`, `FAILED` or `UNSUPPORTED_CONTENT_TYPE` |
| `collection_name` | str | no | Only scans of this collection |
| `classifier_name` | str | no | Only single-classifier or unsaved-classifier scans of this classifier |
| `order` | str | no | `desc` (default) or `asc` by creation time |

---

### get_scan_object

Get the stored summary of a file scan: status, token counts and timing.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | str | yes | `request_id` from `scan_object` or `list_scan_objects` |

---

### get_scan_object_map

Get a file scan's token map: a per-classifier summary, then each classified token's location (line, column, CSV row and header, or JSON/XML path) and effective tags. Token values are not included. Fails with 422 for a failed scan.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `request_id` | str | yes | `request_id` from `scan_object` or `list_scan_objects` |

---

### get_scan_object_supported_types

List the content types `scan_object` detects and how it tokenizes each, plus its size limit and `metadata_map` options.

**Parameters:** None
