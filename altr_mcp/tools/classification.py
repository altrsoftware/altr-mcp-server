import base64
import urllib.parse

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from altr_mcp.settings import get_settings
from altr_mcp.utils import classification, database as databases, scan_requests
from altr_mcp.utils import sidecar_config
from altr_mcp.utils.logging import log_tool

# POST /scan-objects rejects decoded content over 128 KiB with a 413.
SCAN_OBJECT_MAX_BYTES = 128 * 1024


def _failed(response) -> bool:
    return isinstance(response, dict) and response.get("success") is False


def _failure(response: dict) -> str:
    """The upstream's own reason. On an HTTP error, httpx's message holds the full URL."""
    if "body" in response:
        body = (response.get("body") or "").strip()[:200]
        return f"HTTP {response.get('status_code')}" + (f": {body}" if body else "")
    return str(response.get("message"))


async def _connection(database_id: int, database_type: str) -> dict:
    """The data source record, checked to be of the expected type."""
    auth, offset = get_settings().auth, 0
    while True:
        response = await databases._get_databases({"offset": offset}, auth)
        if _failed(response):
            raise ValueError(f"Could not list data sources: {_failure(response)}")
        page = response.get("data") or {}
        rows = page.get("databases") or []
        for row in rows:
            if row.get("id") == database_id:
                if row.get("databaseType") != database_type:
                    raise ValueError(
                        f"Data source {database_id} is a {row.get('databaseType')} "
                        f"connection, not {database_type}.")
                return row
        offset += len(rows)
        if not rows or offset >= (page.get("count") or 0):
            raise ValueError(f"No data source with ID {database_id}.")


async def _repo_type(repo_name: str) -> str:
    repo = await sidecar_config.get_repo(get_settings().auth, repo_name)
    if _failed(repo) and repo.get("status_code") != 404:
        raise ValueError(f"Could not read repository {repo_name}: {_failure(repo)}")
    repo = repo.get("data", repo) if isinstance(repo, dict) else {}
    if not repo.get("type"):
        raise ValueError(f"No repository named {repo_name}.")
    return repo["type"].lower()


async def _check_collection(collection_name: str) -> None:
    """Refuse a collection the console would not run: unknown or empty."""
    response = await classification.get_collection(collection_name, get_settings().auth)
    if response.get("status_code") == 404:
        raise ValueError(f"No collection named {collection_name}.")
    if _failed(response):
        raise ValueError(f"Could not read collection {collection_name}: {_failure(response)}")
    collection = response.get("collection") or {}
    if collection.get("classifier_count") == 0:
        raise ValueError(
            f"{collection_name} has no classifiers. Add at least one before scanning.")


def _as_list(value):
    return value if isinstance(value, list) else [value]


def register(mcp: FastMCP) -> None:

    # ── Classifiers ─────────────────────────────────────────────────────────

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_classifiers(
            prefix: str | None = None,
            order_by: str | None = None,
            sort_order: str | None = None,
            exclude_collection: str | None = None
            ) -> dict:
        """List all available data classifiers in ALTR.

        Classifiers automatically detect sensitive data
        types like SSNs, emails,
        and phone numbers. Includes both ALTR-managed and custom classifiers.

        Args:
            prefix: Only classifiers whose names start with this, e.g.
                "email" matches email_address and email_domain.
            order_by: "name" or "collection_count" (how many collections use
                each classifier).
            sort_order: "asc" or "desc".
            exclude_collection: Leave out classifiers already in this
                collection, e.g. to find ones to add to it.
        """
        settings = get_settings()
        params = {"prefix": prefix, "order_by": order_by,
                  "sort_order": sort_order,
                  "exclude_collection": exclude_collection}
        classifiers = await classification.get_classifiers(
            {k: v for k, v in params.items() if v}, settings.auth)
        return {"success": True, "data": classifiers, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_classifier(classifier_name: str) -> dict:
        """Get details for a single classifier by name.

        Args:
            classifier_name: Exact classifier name as returned
                by `get_classifiers`.
        """
        settings = get_settings()
        response = await classification.get_classifier(
            classifier_name, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_classifier(
            classifier_name: str,
            compound_ruleset: dict,
            description: str | None = None,
            tags: list[str] | None = None
            ) -> dict:
        """Create a custom data classifier defined by a compound ruleset.

        All detection logic lives in `compound_ruleset`: one or more
        conditions (ROW_DATA regex, METADATA column-name matching,
        AMAZON_COMPREHEND entity detection, DATA_LENGTH, CONTENT_TYPE, GDLP
        info-types and more) combined with AND/OR. A plain regex classifier
        is a ruleset with a single ROW_DATA condition carrying the pattern
        and its minimum_threshold. Always set minimum_threshold on ROW_DATA
        leaves. Sampling is set on the job, not here.

        Compound ruleset structure:
        ```json
        {
          "operator": "AND",
          "conditions": [
            {
              "target": "ROW_DATA",
              "pattern": "\\\\d{3}-\\\\d{2}-\\\\d{4}",
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

        Valid `target` values: ROW_DATA, METADATA, COLUMN_LOCATION, GDLP,
        SNOWFLAKE_NATIVE, CONTENT_TYPE, DATA_LENGTH, COLUMN_SIZE,
        AMAZON_COMPREHEND, ENTROPY.

        AMAZON_COMPREHEND leaf fields: `entity_type` (e.g. "SSN", "CREDIT_DEBIT_NUMBER",
        "EMAIL"), `minimum_score` (0.0–1.0, default 0.5).

        METADATA leaf fields: `comparator` (matches/contains/equals/starts_with/
        ends_with), `pattern`.

        DATA_LENGTH / COLUMN_SIZE leaf fields: `length` or `size`, numeric
        `comparator` (greater_than/less_than/equals/etc.), optional `trim`.

        CONTENT_TYPE leaf fields: `content_format` or `content_formats` (list),
        `dominance_threshold`. Formats: JSON, XML, CSV, PDF, DOCX, XLSX, PNG,
        JPEG, ZIP, GZIP, PARQUET, and more.

        ENTROPY leaf fields (flags values that look like secret keys):
        `minimum_evidence_bits`, `minimum_key_bits`, `alphabet_classes`,
        `decode_base64`, `cumulative`.

        All leaf conditions support `negated: true`.

        Args:
            classifier_name: Unique name for the classifier.
            compound_ruleset: Nested AND/OR condition tree, as above.
            description: Human-readable explanation of what it detects.
            tags: Optional key:value tags describing the classifier, e.g.
                ["type:ssn"]. `list_classifier_tags` shows the tags already in
                use.
        """
        settings = get_settings()
        params = {
            "classifier_name": classifier_name,
            "description": description,
            "compound_ruleset": compound_ruleset,
            "attributes": {"tags": tags} if tags is not None else None,
        }
        response = await classification.create_classifier(
            params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_classifier(
            classifier_name: str,
            description: str | None = None,
            compound_ruleset: dict | None = None,
            tags: list[str] | None = None
            ) -> dict:
        """Update an existing custom classifier. Only provided fields are changed.

        Passing `compound_ruleset` also removes any legacy top-level pattern,
        so the ruleset alone decides matches. To keep a legacy regex, include
        it as a ROW_DATA condition with its own minimum_threshold.

        Args:
            classifier_name: Exact classifier name to update.
            description: Updated description.
            compound_ruleset: Updated compound ruleset. See `create_classifier`
                for structure and valid condition targets.
            tags: Replaces the classifier's key:value tags. Pass [] to clear
                them.
        """
        settings = get_settings()
        data = {}
        if description is not None:
            data["description"] = description
        if tags is not None:
            data["attributes"] = {"tags": tags}
        if compound_ruleset is not None:
            data["compound_ruleset"] = compound_ruleset
            # A null pattern removes a legacy top-level pattern on the API.
            # Keep the classifier threshold: Snowflake reads 0 as match-all.
            data["pattern"] = None
        response = await classification.update_classifier(
            classifier_name, data, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def delete_classifier(classifier_name: str) -> dict:
        """Remove a custom classifier you created.

        Cannot delete ALTR managed classifiers. Only use for
        classifiers you created with `create_classifier`.

        Args:
            classifier_name: Exact classifier name as returned
                by `get_classifiers`.
        """
        settings = get_settings()
        params = {"classifier_name": classifier_name}
        response = await classification.delete_classifier(
            params, settings.auth)
        return {"success": True, "data": response, "error": None}

    # ── Collections ─────────────────────────────────────────────────────────

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_collections(sort_order: str | None = None) -> dict:
        """List classifier collections (groups of classifiers
        used for classification jobs).

        Every classification job runs a collection
        (`create_snowflake_job`, `create_databricks_job`,
        `create_oltp_job`, `create_file_classification_job`). Check for existing collections
        (e.g., "ALTR Managed") before creating new ones.

        Args:
            sort_order: "asc" or "desc" by collection name.
        """
        settings = get_settings()
        params = {"sort_order": sort_order} if sort_order else {}
        collections = await classification.get_collections(
            params, settings.auth)
        return {"success": True, "data": collections, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_collection(collection_name: str) -> dict:
        """Get details for a single collection by name.

        Args:
            collection_name: Exact collection name as returned
                by `get_collections`.
        """
        settings = get_settings()
        response = await classification.get_collection(
            collection_name, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_collection(
            collection_name: str,
            description: str = ""
            ) -> dict:
        """Create a classifier collection to use for automated data discovery.

        Collections group classifiers together for
        classification jobs. After creating a collection,
        you can run a classification job to automatically
        scan your database columns and identify which
        contain sensitive data patterns.

        Typical workflow: Create a collection (or use
        existing "ALTR Managed"), then use it in a
        create-job tool such as `create_snowflake_job` to scan your database. Review results
        with `get_classification_report` to see which
        columns were detected.

        Args:
            collection_name: Unique name for the collection.
            description: Optional human-readable description.
        """
        settings = get_settings()
        params = {
            "collection_name": collection_name,
            "description": description,
        }
        response = await classification.create_collection(
            params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_collection(
            collection_name: str,
            description: str
            ) -> dict:
        """Update a collection's description.

        Args:
            collection_name: Exact collection name to update.
            description: Updated description.
        """
        settings = get_settings()
        response = await classification.update_collection(
            collection_name, {"description": description}, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def delete_collection(collection_name: str) -> dict:
        """Delete a classifier collection.

        Cannot delete collections that are in use by active
        or recent jobs. Only delete collections you created
        that are no longer needed.

        Args:
            collection_name: Exact collection name as returned
                by `get_collections`.
        """
        settings = get_settings()
        params = {"collection_name": collection_name}
        response = await classification.delete_collection(
            params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_collection_classifiers(
            collection_name: str,
            limit: int | None = None,
            contiguous_id: str | None = None,
            prefix: str | None = None,
            sort_order: str | None = None
            ) -> dict:
        """List classifiers that belong to a collection.

        Args:
            collection_name: Collection name to inspect.
            limit: Max items to return.
            contiguous_id: Pagination token.
            prefix: Only classifiers whose names start with this.
            sort_order: "asc" or "desc" by classifier name.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        if prefix:
            params["prefix"] = prefix
        if sort_order:
            params["sort_order"] = sort_order
        response = await classification.get_collection_classifiers(
            collection_name, params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def add_classifiers_to_collection(
            collection_name: str,
            classifier_names: str | list[str]
            ) -> dict:
        """Add classifiers to an existing collection.

        All classifiers must already exist and not already be in the
        collection. ALTR managed collections cannot have classifiers
        appended.

        Args:
            collection_name: Collection to add classifiers to.
            classifier_names: Classifier name(s) to add. Pass a single
                string or a list of strings.
        """
        if isinstance(classifier_names, str):
            classifier_names = [classifier_names]
        settings = get_settings()
        response = await classification.append_classifiers_to_collection(
            collection_name, classifier_names, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def remove_classifiers_from_collection(
            collection_name: str,
            classifier_names: str | list[str]
            ) -> dict:
        """Remove classifiers from a collection.

        Args:
            collection_name: Collection to remove classifiers from.
            classifier_names: Classifier name(s) to remove. Pass a single
                string or a list of strings.
        """
        if isinstance(classifier_names, str):
            classifier_names = [classifier_names]
        settings = get_settings()
        response = await classification.remove_classifiers_from_collection(
            collection_name, classifier_names, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def add_classifier_to_collections(
            classifier_name: str,
            collection_names: str | list[str]
            ) -> dict:
        """Add one classifier to several collections in a single call.

        The reverse of `add_classifiers_to_collection`. All collections must
        exist and not already contain the classifier. ALTR-managed
        collections cannot be added to.

        Args:
            classifier_name: Classifier to add.
            collection_names: Collection name(s) to add it to. Pass a single
                string or a list of strings.
        """
        if isinstance(collection_names, str):
            collection_names = [collection_names]
        settings = get_settings()
        response = await classification.append_collections_to_classifier(
            classifier_name, collection_names, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def remove_classifier_from_collections(
            classifier_name: str,
            collection_names: str | list[str]
            ) -> dict:
        """Remove one classifier from several collections in a single call.

        The classifier must currently be in every collection named.
        Collections whose names start with "ALTR" cannot have classifiers
        removed.

        Args:
            classifier_name: Classifier to remove.
            collection_names: Collection name(s) to remove it from. Pass a
                single string or a list of strings.
        """
        if isinstance(collection_names, str):
            collection_names = [collection_names]
        settings = get_settings()
        response = await classification.remove_collections_from_classifier(
            classifier_name, collection_names, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_classifier_tags(
            key: str | None = None,
            prefix: str | None = None,
            limit: int | None = None,
            contiguous_id: str | None = None
            ) -> dict:
        """List the key:value tags in use across the org's classifiers.

        Covers tags on classifiers and on their ruleset conditions, with the
        number of classifiers using each and where it appears. Use it to reuse
        existing tags in `create_classifier` and `update_classifier`. These
        are classifier tags, not the Snowflake tags `get_tags` lists.

        Args:
            key: Only tags with this exact key (the part before ':').
            prefix: Only tags whose full key:value string starts with this.
            limit: Max tags per page (default 100, max 500).
            contiguous_id: Pagination token from a prior call.
        """
        settings = get_settings()
        params = {"key": key, "prefix": prefix, "limit": limit,
                  "contiguous_id": contiguous_id}
        params = {k: v for k, v in params.items() if v is not None}
        response = await classification.list_classifier_tags(
            params, settings.auth)
        return {"success": True, "data": response, "error": None}

    # ── ALTR-managed classifiers ─────────────────────────────────────────────

    @mcp.tool()
    @log_tool
    async def import_altr_managed_classifiers(
            collection: str | None = None) -> dict:
        """Import ALTR-managed classifiers and create or update their
        collection.

        ALTR maintains curated classifiers for common sensitive data types
        (SSN, credit cards, email, phone numbers, etc.), grouped into managed
        collections. Importing is idempotent and syncs the latest versions.
        Use `get_altr_managed_timestamp` first to see whether an update is
        available.

        Args:
            collection: Managed collection slug: "regex" (the default, the
                "ALTR Managed" collection), "gdlp", "aws-comprehend",
                "snowflake-native" or "stoplight", or "all" to import every
                managed collection.
        """
        settings = get_settings()
        response = await classification.import_altr_managed_classifiers(
            settings.auth, collection)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_altr_managed_timestamp(
            collection: str | None = None) -> dict:
        """Check whether a newer version of ALTR-managed classifiers is available.

        Returns the latest available version timestamp alongside the version
        currently installed in your org. If they differ, call
        `import_altr_managed_classifiers` for that collection to update.

        Args:
            collection: Managed collection slug: "regex" (the default),
                "gdlp", "aws-comprehend", "snowflake-native" or "stoplight",
                or "all" for every managed collection in one call.
        """
        settings = get_settings()
        response = await classification.get_altr_managed_timestamp(
            settings.auth, collection)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_altr_managed_classifiers(
            limit: int | None = None,
            contiguous_id: str | None = None,
            collection: str | None = None
            ) -> dict:
        """List available ALTR-managed (prebuilt) classifiers.

        Shows the canonical set maintained by ALTR, not what's currently
        in your org. Call `import_altr_managed_classifiers` to sync them.

        Args:
            limit: Max items to return.
            contiguous_id: Pagination token.
            collection: Managed collection slug: "regex" (the default),
                "gdlp", "aws-comprehend", "snowflake-native" or "stoplight".
        """
        if collection == "all":
            raise ValueError(
                'list_altr_managed_classifiers takes one collection slug; '
                '"all" works only for import and timestamps.')
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        response = await classification.list_altr_managed_classifiers(
            params, settings.auth, collection)
        return {"success": True, "data": response, "error": None}

    # ── Jobs ─────────────────────────────────────────────────────────────────

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_jobs(
            limit: int | None = None,
            contiguous_id: str | None = None,
            status: str | None = None,
            job_type: str | None = None,
            database_id: int | None = None,
            agent_id: str | None = None,
            classification_type: int | None = None,
            order: str | None = None
            ) -> dict:
        """Check the status of classification jobs you've run.

        Classification jobs run asynchronously and can take
        10-30+ minutes to complete depending on your database
        size. Use this to check if a job has finished after
        waiting an appropriate amount of time.

        Once a job shows status COMPLETED, you can fetch its
        detailed report with `get_classification_report` or
        browse results with `get_job_findings`. If status is
        still RUNNING, wait longer before checking again. A
        review-gated job stops at AWAITING_REVIEW until its
        findings are decided and `confirm_job_report` runs.

        Typical workflow: After creating a job, wait 15-30+
        minutes, then use this function to check status. When
        status is COMPLETED, use `get_job_findings` to navigate
        results or `get_classification_report` for a full dump.

        Args:
            limit: Max jobs to return (default 50, max 50).
            contiguous_id: Pagination token from a prior
                `get_jobs` call.
            status: Filter by job status (e.g. RUNNING,
                PAUSED, COMPLETED, CANCELLED, FAILED).
            job_type: Filter by job type (FULL or INCREMENTAL).
            database_id: Restrict to a specific database
                (numeric ID from `get_databases` /
                `get_database_id`).
            agent_id: Restrict to jobs run by a specific
                CLASSIFIER agent UUID.
            classification_type: Optional classification type code.
                1=ALTR Hosted (Snowflake, Databricks), 5=In-Warehouse
                Snowflake or agent. Legacy codes, which the job tools never
                create: 1 without a collection=Google DLP (filtering on 1
                also returns these; check collection_name), 2=Snowflake
                Native, 3=Snowflake Tag Import, 4=Snowflake Native+Tag
                Import, 6=GDLP BYOK.
            order: Sort order by start time, `asc` or
                `desc` (default `desc`).
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id:
            params["contiguous_id"] = contiguous_id
        if status:
            params["status"] = status
        if job_type:
            params["job_type"] = job_type
        if database_id is not None:
            params["database_id"] = database_id
        if agent_id:
            params["agent_id"] = agent_id
        if classification_type is not None:
            params["classification_type"] = classification_type
        if order:
            params["order"] = order
        jobs = await classification.get_jobs(
            params, settings.auth)
        return {"success": True, "data": jobs, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_active_jobs(
            limit: int | None = None,
            contiguous_id: str | None = None,
            database_id: int | None = None,
            agent_id: str | None = None,
            status: str | None = None,
            job_type: str | None = None,
            classification_type: int | None = None,
            order: str | None = None
            ) -> dict:
        """List all currently active (non-terminal) classification jobs.

        Returns jobs that have not finished: created, running, paused or
        resumed, cancelling, building their report, or waiting for review.
        Useful for checking what's in flight without filtering through all
        historical jobs.

        Args:
            limit: Max jobs to return.
            contiguous_id: Pagination token.
            database_id: Filter by database ID.
            agent_id: Filter by agent UUID.
            status: One active status: CREATED, RESUMED, PAUSED, RUNNING,
                PENDING_CANCEL, UPLOADING_REPORT, PROCESSING_REPORT,
                PROCESSING_FINDINGS or AWAITING_REVIEW.
            job_type: FULL or INCREMENTAL.
            classification_type: Classification type code. 1=ALTR Hosted
                (Snowflake, Databricks), 5=In-Warehouse Snowflake or agent.
                Legacy codes, which the job tools never create: 1 without a
                collection=Google DLP (filtering on 1 also returns these;
                check collection_name), 2=Snowflake Native, 3=Snowflake Tag
                Import, 4=Snowflake Native+Tag Import, 6=GDLP BYOK.
            order: "desc" (newest first, the default) or "asc".
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id:
            params["contiguous_id"] = contiguous_id
        if database_id is not None:
            params["database_id"] = database_id
        if agent_id:
            params["agent_id"] = agent_id
        filters = {"status": status, "job_type": job_type, "order": order}
        params.update({k: v for k, v in filters.items() if v})
        if classification_type is not None:
            params["classification_type"] = classification_type
        response = await classification.get_active_jobs(params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_job(job_id: str) -> dict:
        """Get details for a single classification job by ID.

        Args:
            job_id: Job identifier returned from a create-job tool
                or listed by `get_jobs`.
        """
        settings = get_settings()
        response = await classification.get_job(job_id, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_job_summary(job_id: str) -> dict:
        """Get an inline per-classifier classification summary for a completed job.

        Returns classification counts grouped by classifier — faster than
        `get_classification_report` because it doesn't require a presigned
        S3 round-trip. Use this to get a quick count of detected columns
        before drilling into `get_job_findings`.

        Args:
            job_id: Job identifier of a COMPLETED job.
        """
        settings = get_settings()
        response = await classification.get_job_summary(job_id, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_report_groups(
            limit: int | None = None,
            contiguous_id: str | None = None,
            status: str | list[str] | None = None,
            connection_type: str | list[str] | None = None
            ) -> dict:
        """List classification reports grouped by collection, method and
        datasource, newest activity first.

        Each group carries its latest run; page older runs with
        `list_report_group_runs`. Keep filters the same across pages, and page
        until contiguous_id is absent: a filtered page can be empty while
        more matches remain.

        Args:
            limit: Max groups per page (default 50, max 50).
            contiguous_id: Pagination token from a prior call.
            status: Only groups whose latest run has one of these report
                statuses: "needs_review", "in_progress", "confirmed",
                "failed".
            connection_type: Only these connection types, e.g.
                ["databricks", "mysql"].
        """
        if isinstance(status, str):
            status = [status]
        if isinstance(connection_type, str):
            connection_type = [connection_type]
        settings = get_settings()
        params = {"limit": limit, "contiguous_id": contiguous_id,
                  "status": status, "connection_type": connection_type}
        params = {k: v for k, v in params.items() if v is not None}
        response = await classification.list_report_groups(
            params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_report_group_runs(
            group_id: str,
            limit: int | None = None,
            contiguous_id: str | None = None
            ) -> dict:
        """List a report group's classification runs, newest first.

        Args:
            group_id: group_id from `list_report_groups`.
            limit: Max runs per page (default 50, max 50).
            contiguous_id: Pagination token from a prior call.
        """
        settings = get_settings()
        params = {"limit": limit, "contiguous_id": contiguous_id}
        params = {k: v for k, v in params.items() if v is not None}
        response = await classification.list_report_group_runs(
            group_id, params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_job_exclusions(job_id: str) -> dict:
        """Show which exclusion paths a classification job applied.

        `applied` lists exclusions that covered at least one object;
        `unmatched` lists those that covered nothing. A non-empty `unmatched`
        means the scan sampled more than intended, for example because of a
        mistyped path. When `applied_unavailable` or `match_unavailable` is
        true, the matching list is unknown rather than empty.

        Args:
            job_id: Job identifier.
        """
        settings = get_settings()
        response = await classification.get_job_exclusions(
            job_id, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_snowflake_job(
            database_id: int,
            collection_name: str,
            processing_location: str = "altr_hosted",
            schema: str | None = None,
            table: str | None = None,
            exclude: str | list[str] | None = None,
            sample_type: str = "ROWS",
            sample_size: int | None = None,
            requires_review: bool = True
            ) -> dict:
        """Run a classification scan on a Snowflake database, as the console's
        Classify Data wizard does.

        The collection's classifiers decide what is detected. The processing
        location decides where the scan runs:
        - "altr_hosted" (the default): ALTR reads samples and evaluates the
          classifiers in its cloud, including Google DLP conditions.
        - "in_warehouse": the scan runs in Snowflake on your compute. Google
          DLP, Content Type and Amazon Comprehend conditions are skipped.

        Scans run asynchronously and can take 10-30+ minutes. Poll `get_job`
        or `get_jobs`; a review-gated job stops at AWAITING_REVIEW.

        Args:
            database_id: Snowflake connection ID (from `get_databases`).
            collection_name: Collection to run. It must contain classifiers.
            processing_location: "altr_hosted" or "in_warehouse".
            schema: Scan only this schema of the database.
            table: Scan only this table (requires schema).
            exclude: Objects to skip, relative to the scope: a schema name, or
                "schema.table". Without schema, exclusions apply to the whole
                database. Check `get_job_exclusions` afterwards: a name that
                matches nothing is not an error, and that data is scanned.
            sample_type: "ROWS" (a row count, the default) or "PERCENT".
            sample_size: Rows to sample per column (default 1000), or a
                percentage from 1 to 100 (default 5) with PERCENT.
            requires_review: Hold the report for human review until every
                finding is decided and `confirm_job_report` runs. Defaults to
                true, as in the console.
        """
        location = processing_location.strip().lower().replace("-", "_")
        if location not in ("altr_hosted", "in_warehouse"):
            raise ValueError('processing_location must be "altr_hosted" or "in_warehouse".')
        body = {
            "database_id": database_id,
            "job_type": "FULL",
            "classification_type": "gdlp" if location == "altr_hosted" else "altr_native",
            "requires_review": requires_review,
            "collection_name": collection_name,
            "condition_types": scan_requests.SNOWFLAKE_CONDITION_TYPES,
            **scan_requests.sampling(sample_type, sample_size),
        }
        settings = get_settings()
        database = await _connection(database_id, "snowflake_external_functions")
        if schema or table or exclude:
            parts = scan_requests.object_scope(database["databaseName"], schema, table)
            body.update(scan_requests.scope_and_exclusions(parts, exclude))
        await _check_collection(collection_name)
        response = await classification.create_snowflake_job(body, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_databricks_job(
            database_id: int,
            collection_name: str,
            catalog: str | None = None,
            schema: str | None = None,
            table: str | None = None,
            exclude: str | list[str] | None = None,
            sample_type: str = "ROWS",
            sample_size: int | None = None,
            requires_review: bool = True
            ) -> dict:
        """Run a classification scan on a Databricks workspace, as the
        console does. Databricks scans are always ALTR Hosted.

        Scans run asynchronously; poll `get_job` or `get_jobs`. A
        review-gated job stops at AWAITING_REVIEW.

        Args:
            database_id: Databricks connection ID (from `get_databases`).
            collection_name: Collection to run. It must contain classifiers.
            catalog: Scan only this Unity Catalog catalog.
            schema: Scan only this schema (requires catalog).
            table: Scan only this table (requires schema).
            exclude: Objects to skip, relative to the scope: a schema, or
                "schema.table" under a catalog. Check `get_job_exclusions`
                afterwards: a name that matches nothing is not an error.
            sample_type: "ROWS" (a row count, the default) or "PERCENT".
            sample_size: Rows to sample per column (default 1000), or a
                percentage from 1 to 100 (default 5) with PERCENT.
            requires_review: Hold the report for human review until every
                finding is decided and `confirm_job_report` runs. Defaults to
                true, as in the console.
        """
        body = {
            "database_id": database_id,
            "requires_review": requires_review,
            "collection_name": collection_name,
            "condition_types": scan_requests.CONDITION_TYPES,
            **scan_requests.sampling(sample_type, sample_size),
        }
        body.update(scan_requests.scope_and_exclusions(
            scan_requests.object_scope(catalog, schema, table), exclude))
        settings = get_settings()
        await _connection(database_id, "databricks")
        await _check_collection(collection_name)
        response = await classification.create_databricks_job(body, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_oltp_job(
            repo_name: str,
            agent_id: str,
            service_user_name: str,
            collection_name: str,
            database: str | None = None,
            schema: str | None = None,
            table: str | None = None,
            exclude: str | list[str] | None = None,
            sid: str | None = None,
            service_name: str | None = None,
            sample_type: str = "ROWS",
            sample_size: int | None = None,
            requires_review: bool = True
            ) -> dict:
        """Run a classification scan on a database repository (Oracle, MSSQL,
        PostgreSQL, MySQL, MongoDB, Cassandra) through a classifier agent, as
        the console does. The scan runs on the agent, in your network.
        Google DLP and Amazon Comprehend conditions use the agent's own Google
        Cloud and AWS credentials; a collection with either kind fails the
        scan if the agent isn't configured for it.

        For S3 and filesystem repositories use
        `create_file_classification_job`. Scans run asynchronously; poll
        `get_job` or `get_jobs`. A review-gated job stops at AWAITING_REVIEW.

        Args:
            repo_name: Repository name (from `list_sc_repos`).
            agent_id: CLASSIFIER agent ID (from `list_sc_agents`).
            service_user_name: Repository service user the agent connects as
                (from `list_sc_service_users`).
            collection_name: Collection to run. It must contain classifiers.
            database: Scan only this database. On Oracle this is the
                connection's service name.
            schema: Scan only this schema (requires database). MySQL, MongoDB
                and Cassandra have no schema level.
            table: Scan only this table or collection (requires database,
                and schema on Oracle, MSSQL and PostgreSQL).
            exclude: Objects to skip, relative to the scope: "schema" or
                "schema.table" under a database (a table name on MySQL,
                MongoDB and Cassandra). Check `get_job_exclusions` afterwards:
                a name that matches nothing is not an error.
            sid: Oracle only, for an unscoped scan: the SID to connect with.
            service_name: Oracle only: the service name to connect with. A
                scoped Oracle scan always connects by service name, which is
                also its database.
            sample_type: "ROWS" (a row count, the default) or "PERCENT".
            sample_size: Rows to sample per column (default 1000), or a
                percentage from 1 to 100 (default 5) with PERCENT.
            requires_review: Hold the report for human review until every
                finding is decided and `confirm_job_report` runs. Defaults to
                true, as in the console.
        """
        sampling = scan_requests.sampling(sample_type, sample_size)
        database = scan_requests.name(database, "database")
        sid = scan_requests.name(sid, "sid")
        service_name = scan_requests.name(service_name, "service_name")
        if sid and service_name:
            raise ValueError("Pass sid or service_name, not both.")
        repo_type = await _repo_type(repo_name)
        if repo_type in scan_requests.FILE_REPO_TYPES:
            raise ValueError(
                f"{repo_name} is a file repository; use create_file_classification_job.")
        if repo_type not in scan_requests.RELATIONAL_REPO_TYPES:
            raise ValueError(f"Repositories of type {repo_type} can't be classified.")
        scoped = bool(database or schema or table or exclude)
        if repo_type == "oracle":
            if scoped:
                if sid:
                    raise ValueError("A scoped Oracle scan connects by service name, not SID.")
                database = database or service_name
                if service_name and database and service_name != database:
                    raise ValueError(
                        "On Oracle the scope's database is the service name; they must match.")
                service_name = database
        elif sid or service_name:
            raise ValueError("sid and service_name are for Oracle repositories only.")
        two_level = repo_type in scan_requests.TWO_LEVEL_REPO_TYPES
        parts = scan_requests.object_scope(database, schema, table, two_level)
        body = {
            "agent_id": agent_id,
            "classification_type": scan_requests.ALTR_NATIVE,
            "collection_name": collection_name,
            "condition_types": scan_requests.CONDITION_TYPES,
            "repo_name": repo_name,
            **sampling,
            "service_user_name": service_user_name,
            "requires_review": requires_review,
        }
        if service_name:
            body["service_name"] = service_name
        elif sid:
            body["sid"] = sid
        body.update(scan_requests.scope_and_exclusions(parts, exclude, two_level))
        settings = get_settings()
        await _check_collection(collection_name)
        response = await classification.create_oltp_job(body, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_file_classification_job(
            repo_name: str,
            agent_id: str,
            service_user_name: str,
            collection_name: str,
            paths: str | list[str] | None = None,
            exclude_paths: str | list[str] | None = None,
            content_classification: bool = True,
            full_file_scan: bool = False,
            include_glob: str | None = None,
            exclude_glob: str | None = None,
            max_files: int | None = None,
            max_file_bytes: int | None = None,
            scan_mode: str | None = None,
            glue_crawler: str | None = None,
            glue_start_crawler: bool = False,
            sniff_bytes: bool = True,
            metadata_map: str = "hashed",
            metadata_map_by_format: dict | None = None,
            requires_review: bool = True
            ) -> dict:
        """Run a classification scan on an S3 or filesystem repository through
        a classifier agent, as the console does. File contents stay in the
        agent's network, except that Google DLP and Amazon Comprehend
        conditions send them to those services under the agent's own Google
        Cloud and AWS credentials; a collection with either kind fails the
        scan if the agent isn't configured for it.

        Scans run asynchronously; poll `get_job` or `get_jobs`. A
        review-gated job stops at AWAITING_REVIEW.

        Args:
            repo_name: S3 or filesystem repository (from `list_sc_repos`).
            agent_id: CLASSIFIER agent ID (from `list_sc_agents`).
            service_user_name: Repository service user (from
                `list_sc_service_users`).
            collection_name: Collection to run. It must contain classifiers.
            paths: Scan only these prefixes or directories, relative to the
                repository root (at most 50). Omit to scan everything.
            exclude_paths: Prefixes or directories to skip, relative to the
                repository root (at most 100).
            content_classification: Classify file contents. False maps files
                and fields only. Defaults to true.
            full_file_scan: Read every value of every file instead of a
                sample. Defaults to false.
            include_glob: Only files whose paths match this glob.
            exclude_glob: Skip files whose paths match this glob.
            max_files: Cap on files listed (agent default 100000).
            max_file_bytes: Bytes read per file, at most 67108864 (64 MiB;
                agent default 10 MiB).
            scan_mode: S3 only: "CRAWL" (list the bucket, the default) or
                "GLUE" (read the repository's Glue database).
            glue_crawler: S3 with GLUE only: the Glue crawler to start.
            glue_start_crawler: S3 with GLUE only: run the crawler when the
                catalog is empty.
            sniff_bytes: S3 only: detect content types from file bytes rather
                than extensions. Defaults to true.
            metadata_map: How field names (CSV headers, JSON keys) are kept in
                results: "hashed" (the default), "plaintext" or "none".
            metadata_map_by_format: Per-format overrides for csv, json, xml,
                html or yaml, e.g. {"csv": "plaintext"}.
            requires_review: Hold the report for human review until every
                finding is decided and `confirm_job_report` runs. Defaults to
                true, as in the console.
        """
        location = scan_requests.path_scope_and_exclusions(paths, exclude_paths)
        retained = scan_requests.metadata_map(metadata_map, metadata_map_by_format)
        repo_type = await _repo_type(repo_name)
        if repo_type not in scan_requests.FILE_REPO_TYPES:
            raise ValueError(f"{repo_name} is not a file repository; use create_oltp_job.")
        options = scan_requests.file_options(
            repo_type == "s3", content_classification=content_classification,
            full_file_scan=full_file_scan, include_glob=include_glob,
            exclude_glob=exclude_glob, max_files=max_files,
            max_file_bytes=max_file_bytes, scan_mode=scan_mode,
            glue_crawler=glue_crawler, glue_start_crawler=glue_start_crawler,
            sniff_bytes=sniff_bytes)
        body = {
            "agent_id": agent_id,
            "classification_type": scan_requests.ALTR_NATIVE,
            "collection_name": collection_name,
            "condition_types": scan_requests.CONDITION_TYPES,
            "repo_name": repo_name,
            # The console sends its sampling defaults for file sources too.
            **scan_requests.sampling("ROWS", None),
            "service_user_name": service_user_name,
            "requires_review": requires_review,
            **location,
            "file_options": options,
        }
        if retained is not None:
            body["metadata_map"] = retained
        settings = get_settings()
        await _check_collection(collection_name)
        response = await classification.create_oltp_job(body, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_job_status(job_id: str, status: str) -> dict:
        """Control a running classification job (pause, cancel, or resume).

        Use to manage long-running classification jobs. Status options: PAUSED,
        CANCELLED, or RUNNING.

        Args:
            job_id: Job identifier to update.
            status: New status (PAUSED, CANCELLED, or RUNNING).
        """
        settings = get_settings()
        encoded_id = urllib.parse.quote(job_id, safe='')
        params = {"status": status}
        response = await classification.update_job_status(
            params, settings.auth, encoded_id)
        return {"success": True, "data": response, "error": None}

    # ── Job findings tree ────────────────────────────────────────────────────

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_job_findings(
            job_id: str,
            limit: int | None = None,
            page_token: str | None = None,
            classifier_name: str | list[str] | None = None,
            confirmed_status: str | list[str] | None = None,
            include_column_status_counts: bool | None = None,
            confidence: str | list[str] | None = None
            ) -> dict:
        """List databases found in a completed classification job.

        Entry point for navigating classification results hierarchically
        without downloading the full report. Returns the databases that
        contain detected columns. Drill down with `get_job_findings_schemas`,
        then tables, columns, and classifiers.

        Prefer this over `get_classification_report` when you want to
        interactively explore or filter results by status or classifier.

        Args:
            job_id: Identifier of a COMPLETED job, or of a review-gated job at
                AWAITING_REVIEW.
            limit: Max databases to return.
            page_token: Pagination token from a prior call.
            classifier_name: Filter to databases containing detections by
                these classifier(s). Single string or list.
            confirmed_status: Filter by review status:
                approved, rejected, or pending. Single string or list.
            include_column_status_counts: If true, include approved/
                rejected/pending counts per database.
            confidence: Keep only findings of these confidence tiers: HIGH,
                MEDIUM, LOW. Counts are limited the same way.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if page_token:
            params["page_token"] = page_token
        if classifier_name:
            params["classifier_name"] = _as_list(classifier_name)
        if confirmed_status:
            params["confirmed_status"] = _as_list(confirmed_status)
        if include_column_status_counts is not None:
            params["include_column_status_counts"] = include_column_status_counts
        if confidence:
            params["confidence"] = _as_list(confidence)
        response = await classification.get_job_findings(
            job_id, params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_job_findings_schemas(
            job_id: str,
            database: str,
            limit: int | None = None,
            page_token: str | None = None,
            classifier_name: str | list[str] | None = None,
            confirmed_status: str | list[str] | None = None,
            confidence: str | list[str] | None = None
            ) -> dict:
        """List schemas in a database from a classification job's findings.

        Second level of the findings tree. Call after `get_job_findings`
        to drill into a specific database.

        Args:
            job_id: Identifier of a COMPLETED job, or of a review-gated job at
                AWAITING_REVIEW.
            database: Database name from `get_job_findings`.
            limit: Max schemas to return.
            page_token: Pagination token.
            classifier_name: Filter by classifier name(s).
            confirmed_status: Filter by review status: approved, rejected
                or pending. Single string or list.
            confidence: Keep only findings of these confidence tiers: HIGH,
                MEDIUM, LOW. Counts are limited the same way.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if page_token:
            params["page_token"] = page_token
        if classifier_name:
            params["classifier_name"] = _as_list(classifier_name)
        if confirmed_status:
            params["confirmed_status"] = _as_list(confirmed_status)
        if confidence:
            params["confidence"] = _as_list(confidence)
        response = await classification.get_job_findings_schemas(
            job_id, database, params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_job_findings_tables(
            job_id: str,
            database: str,
            schema: str,
            limit: int | None = None,
            page_token: str | None = None,
            classifier_name: str | list[str] | None = None,
            confirmed_status: str | list[str] | None = None,
            confidence: str | list[str] | None = None
            ) -> dict:
        """List tables in a schema from a classification job's findings.

        Third level of the findings tree.

        Args:
            job_id: Identifier of a COMPLETED job, or of a review-gated job at
                AWAITING_REVIEW.
            database: Database name.
            schema: Schema name from `get_job_findings_schemas`.
            limit: Max tables to return.
            page_token: Pagination token.
            classifier_name: Filter by classifier name(s).
            confirmed_status: Filter by review status: approved, rejected
                or pending. Single string or list.
            confidence: Keep only findings of these confidence tiers: HIGH,
                MEDIUM, LOW. Counts are limited the same way.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if page_token:
            params["page_token"] = page_token
        if classifier_name:
            params["classifier_name"] = _as_list(classifier_name)
        if confirmed_status:
            params["confirmed_status"] = _as_list(confirmed_status)
        if confidence:
            params["confidence"] = _as_list(confidence)
        response = await classification.get_job_findings_tables(
            job_id, database, schema, params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_job_findings_columns(
            job_id: str,
            database: str,
            schema: str,
            table: str,
            limit: int | None = None,
            page_token: str | None = None,
            classifier_name: str | list[str] | None = None,
            confirmed_status: str | list[str] | None = None,
            confidence: str | list[str] | None = None
            ) -> dict:
        """List columns in a table from a classification job's findings.

        Fourth level of the findings tree.

        Args:
            job_id: Identifier of a COMPLETED job, or of a review-gated job at
                AWAITING_REVIEW.
            database: Database name.
            schema: Schema name.
            table: Table name from `get_job_findings_tables`.
            limit: Max columns to return.
            page_token: Pagination token.
            classifier_name: Filter by classifier name(s).
            confirmed_status: Filter by review status: approved, rejected
                or pending. Single string or list.
            confidence: Keep only findings of these confidence tiers: HIGH,
                MEDIUM, LOW. Counts are limited the same way.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if page_token:
            params["page_token"] = page_token
        if classifier_name:
            params["classifier_name"] = _as_list(classifier_name)
        if confirmed_status:
            params["confirmed_status"] = _as_list(confirmed_status)
        if confidence:
            params["confidence"] = _as_list(confidence)
        response = await classification.get_job_findings_columns(
            job_id, database, schema, table, params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_job_findings_classifiers(
            job_id: str,
            database: str,
            schema: str,
            table: str,
            column: str,
            limit: int | None = None,
            page_token: str | None = None,
            confirmed_status: str | list[str] | None = None,
            classifier_name: str | list[str] | None = None,
            confidence: str | list[str] | None = None
            ) -> dict:
        """List classifiers that fired on a specific column in a completed job.

        Fifth (leaf) level of the findings tree. Shows per-classifier detection
        results for a column with confidence scores. Use `get_job_findings_lineage`
        to see the full compound-ruleset evaluation trace for a specific classifier.

        Args:
            job_id: Identifier of a COMPLETED job, or of a review-gated job at
                AWAITING_REVIEW.
            database: Database name.
            schema: Schema name.
            table: Table name.
            column: Column name from `get_job_findings_columns`.
            limit: Max classifiers to return.
            page_token: Pagination token.
            confirmed_status: Filter by review status: approved, rejected
                or pending. Single string or list.
            classifier_name: Only these classifier(s).
            confidence: Keep only findings of these confidence tiers: HIGH,
                MEDIUM, LOW. Counts are limited the same way.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if page_token:
            params["page_token"] = page_token
        if confirmed_status:
            params["confirmed_status"] = _as_list(confirmed_status)
        if classifier_name:
            params["classifier_name"] = _as_list(classifier_name)
        if confidence:
            params["confidence"] = _as_list(confidence)
        response = await classification.get_job_findings_classifiers(
            job_id, database, schema, table, column, params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_job_findings_lineage(
            job_id: str,
            database: str,
            schema: str,
            table: str,
            column: str,
            classifier_name: str
            ) -> dict:
        """Get the compound-ruleset evaluation trace (lineage) for a classifier
        on a specific column in a completed job.

        Returns the full decision tree showing which conditions evaluated,
        which matched, and why the classifier did or did not fire. Useful for
        debugging custom classifiers or understanding AMAZON_COMPREHEND /
        METADATA condition results.

        Args:
            job_id: Identifier of a COMPLETED job, or of a review-gated job at
                AWAITING_REVIEW.
            database: Database name.
            schema: Schema name.
            table: Table name.
            column: Column name.
            classifier_name: Classifier name to inspect.
        """
        settings = get_settings()
        response = await classification.get_job_findings_lineage(
            job_id, database, schema, table, column,
            classifier_name, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_job_findings_leaves(
            job_id: str,
            limit: int | None = None,
            page_token: str | None = None,
            confidence: str | list[str] | None = None
            ) -> dict:
        """List every finding in a job in one stream, ordered by full path.

        One row per (database, schema, table, column, classifier), with
        total_findings, match_rate_avg, is_new and the resolved review
        status. Use this to see a whole job at once instead of walking the
        tree with `get_job_findings` and its drill-down tools. Rows are under
        `items`. File sources also return crawl records, with an empty
        classifier_name and no confirmed_status; they are not findings and
        need no decision, and a confidence filter leaves them out.

        Args:
            job_id: Job identifier.
            limit: Max rows per page (default 100, max 1000).
            page_token: next_page_token from a prior call.
            confidence: Keep only these confidence tiers: HIGH, MEDIUM, LOW.
                Single string or list.
        """
        settings = get_settings()
        params: dict = {}
        if limit is not None:
            params["limit"] = limit
        if page_token:
            params["page_token"] = page_token
        if confidence:
            params["confidence"] = _as_list(confidence)
        response = await classification.get_job_findings_leaves(
            job_id, params, settings.auth)
        return {"success": True, "data": response, "error": None}

    # ── Job decisions ─────────────────────────────────────────────────────────

    @mcp.tool()
    @log_tool
    async def record_job_decision(
            job_id: str,
            confirmed_status: str,
            database: str | None = None,
            schema: str | None = None,
            table: str | None = None,
            column: str | None = None,
            classifier_name: str | None = None
            ) -> dict:
        """Approve or reject classification findings in a job.

        Decisions can be scoped from the entire job down to a specific
        classifier on a specific column. Broader scopes (e.g., entire table)
        apply to all columns and classifiers within that scope.

        After recording decisions, check overall progress with
        `get_job_review_status`. For a job created with requires_review=true,
        finish with `confirm_job_report` to release the report. To decide
        many findings at once, use `record_bulk_job_decision`.

        Args:
            job_id: Identifier of a COMPLETED job, or of a review-gated job at
                AWAITING_REVIEW.
            confirmed_status: Decision to record: "approved" or "rejected".
            database: Scope to this database (omit for job-wide).
            schema: Scope to this schema (requires database).
            table: Scope to this table (requires schema).
            column: Scope to this column (requires table).
            classifier_name: Scope to this classifier on the column
                (requires column).
        """
        settings = get_settings()
        data: dict = {"confirmed_status": confirmed_status}
        if database is not None:
            data["database"] = database
        if schema is not None:
            data["schema"] = schema
        if table is not None:
            data["table"] = table
        if column is not None:
            data["column"] = column
        if classifier_name is not None:
            data["classifier_name"] = classifier_name
        response = await classification.create_job_decision(
            job_id, data, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_job_decisions(
            job_id: str,
            database: str | None = None,
            schema: str | None = None,
            table: str | None = None,
            column: str | None = None,
            limit: int | None = None,
            page_token: str | None = None
            ) -> dict:
        """List human review decisions recorded for a classification job.

        Args:
            job_id: Job identifier.
            database: Filter to this database.
            schema: Filter to this schema.
            table: Filter to this table.
            column: Filter to this column.
            limit: Max decisions to return.
            page_token: Pagination token.
        """
        settings = get_settings()
        params: dict = {}
        if database is not None:
            params["database"] = database
        if schema is not None:
            params["schema"] = schema
        if table is not None:
            params["table"] = table
        if column is not None:
            params["column"] = column
        if limit is not None:
            params["limit"] = limit
        if page_token:
            params["page_token"] = page_token
        response = await classification.get_job_decisions(
            job_id, params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def revoke_job_decisions(
            job_id: str,
            database: str | None = None,
            schema: str | None = None,
            table: str | None = None,
            column: str | None = None,
            classifier_name: str | None = None
            ) -> dict:
        """Revoke (remove) previously recorded review decisions for a job.

        Scope works the same as `record_job_decision` — revoke at any
        granularity from the whole job down to a single classifier on a column.
        After revoking, those findings return to "pending" status.

        Args:
            job_id: Job identifier.
            database: Scope to this database.
            schema: Scope to this schema.
            table: Scope to this table.
            column: Scope to this column.
            classifier_name: Scope to this classifier.
        """
        settings = get_settings()
        params: dict = {}
        if database is not None:
            params["database"] = database
        if schema is not None:
            params["schema"] = schema
        if table is not None:
            params["table"] = table
        if column is not None:
            params["column"] = column
        if classifier_name is not None:
            params["classifier_name"] = classifier_name
        response = await classification.delete_job_decisions(
            job_id, params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def record_bulk_job_decision(
            job_id: str,
            confirmed_status: str,
            classifier_names: list[str],
            confidence: list[str] | None = None,
            database: str | None = None,
            schema: str | None = None,
            table: str | None = None,
            dry_run: bool = False
            ) -> dict:
        """Approve or reject every undecided finding that matches a filter.

        Covers findings of the given classifiers, optionally narrowed by
        confidence tier and by a database, schema and table path. Findings
        that already have a decision are left alone, and each covered
        finding can still be overridden with `record_job_decision`. Run with
        dry_run=True first to see how many findings it would cover.

        Returns matched_findings and matched_objects, plus a bulk_decision_id
        when something was recorded (not on a dry run or when nothing
        matched). Undo the whole decision with `revoke_bulk_job_decision`.

        Args:
            job_id: Job identifier.
            confirmed_status: Decision to record: "approved" or "rejected".
            classifier_names: Classifiers whose findings to decide.
            confidence: Keep only these confidence tiers: HIGH, MEDIUM, LOW.
            database: Limit to this database.
            schema: Limit to this schema (requires database).
            table: Limit to this table (requires schema).
            dry_run: If true, return the counts without recording anything.
        """
        if not classifier_names:
            # The engine reads an empty list as every classifier.
            raise ValueError("classifier_names must name at least one classifier.")
        settings = get_settings()
        predicate: dict = {"classifier_names": classifier_names}
        if confidence:
            predicate["confidence"] = confidence
        if database is not None:
            predicate["database"] = database
        if schema is not None:
            predicate["schema"] = schema
        if table is not None:
            predicate["table"] = table
        data = {
            "confirmed_status": confirmed_status,
            "predicate": predicate,
            "dry_run": dry_run,
        }
        response = await classification.create_bulk_job_decision(
            job_id, data, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def revoke_bulk_job_decision(
            job_id: str, bulk_decision_id: str) -> dict:
        """Undo a bulk decision recorded with `record_bulk_job_decision`.

        Revokes every decision it still covers. A finding decided
        individually afterwards keeps that individual decision.

        Args:
            job_id: Job identifier.
            bulk_decision_id: bulk_decision_id returned by
                `record_bulk_job_decision`.
        """
        settings = get_settings()
        response = await classification.delete_bulk_job_decision(
            job_id, bulk_decision_id, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_job_review_status(job_id: str) -> dict:
        """Get the review progress for a classification job.

        Returns total/approved/rejected/pending counts across all findings.
        Use after recording decisions with `record_job_decision` to check
        how much review work remains.

        Args:
            job_id: Identifier of a COMPLETED job, or of a review-gated job at
                AWAITING_REVIEW.
        """
        settings = get_settings()
        response = await classification.get_job_review_status(
            job_id, settings.auth)
        return {"success": True, "data": response, "error": None}

    # ── Report ───────────────────────────────────────────────────────────────

    @mcp.tool()
    @log_tool
    async def confirm_job_report(job_id: str) -> dict:
        """Confirm the review of a review-gated job and release its report.

        For a job created with requires_review=true. Every finding must have
        a decision; check with `get_job_review_status` first. Generation
        then runs in the background and decisions are locked: poll `get_job`
        until the status is COMPLETED, then read the report with
        `get_classification_report`.

        Args:
            job_id: Job identifier.
        """
        settings = get_settings()
        response = await classification.confirm_job_report(
            job_id, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def cancel_job_report(job_id: str) -> dict:
        """Cancel a review-gated job before its report is confirmed.

        For a job created with requires_review=true that is still being
        reviewed. The job moves to CANCELLED and its review data is
        discarded. A job whose report has already been confirmed cannot be
        cancelled this way.

        Args:
            job_id: Job identifier.
        """
        settings = get_settings()
        response = await classification.cancel_job_report(
            job_id, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_classification_report(job_id: str) -> dict:
        """Get detailed results from a completed classification job.

        Returns which columns were detected as containing
        sensitive data along with confidence scores. Only call
        after the job status is COMPLETED (verify with
        `get_jobs`).

        For interactive navigation, prefer `get_job_findings` which
        lets you drill down without downloading the full report.

        After reviewing results, check if the needed Snowflake
        tags exist using `get_tags`. If tags are missing, they
        must be created in Snowflake first before connecting
        with `connect_tag`.

        Args:
            job_id: Job identifier returned from a create-job tool
                or listed by `get_jobs`.
        """
        settings = get_settings()
        params = {}
        response = await classification.get_job_report(
            params, settings.auth, job_id)
        return {"success": True, "data": response, "error": None}

    # ── Scan objects ─────────────────────────────────────────────────────────

    @mcp.tool()
    @log_tool
    async def scan_object(
            content: str | None = None,
            content_base64: str | None = None,
            collection_name: str | None = None,
            classifier_name: str | None = None,
            classifier: dict | None = None,
            file_name: str | None = None,
            include_all_tokens: bool | None = None,
            include_lineage: bool | None = None,
            metadata_map: dict | None = None
            ) -> dict:
        """Classify a file's contents and return the scan summary.

        Runs synchronously on up to 128 KiB of content: CSV, JSON, XML,
        YAML, plain text and the other types `get_scan_object_supported_types`
        lists. The content is processed in memory and not stored; the summary
        and token map are kept, so read the map with `get_scan_object_map`
        and the request_id returned here.

        Choose what to scan with:
        - collection_name: every classifier in the collection.
        - collection_name and classifier_name: one classifier from the
          collection. Add `classifier` to test an edited definition
          (pattern, compound_ruleset, minimum_threshold, attributes) in place
          of the saved one, without saving it.
        - classifier alone: an unsaved classifier (classifier_name, pattern
          and/or compound_ruleset, minimum_threshold, attributes), with no
          collection needed.

        Args:
            content: File contents as text. Pass this or content_base64.
            content_base64: File contents, base64-encoded. Use for binary
                files.
            collection_name: Collection to scan with.
            classifier_name: One classifier from collection_name.
            classifier: An unsaved classifier definition, as described above.
            file_name: Optional original file name, echoed in the results.
            include_all_tokens: If true, the token map includes tokens that
                matched no classifier. Defaults to false.
            include_lineage: If true, the token map shows how each
                classifier's conditions decided each match.
            metadata_map: How structural names (CSV headers, JSON keys) are
                kept in the map: {"default": "hashed"|"plaintext"|"none",
                "by_format": {"csv": ...}}.
        """
        if (content is None) == (content_base64 is None):
            raise ValueError("Pass exactly one of content and content_base64.")
        if classifier_name is not None and collection_name is None:
            raise ValueError("classifier_name needs the collection_name it is in.")
        if collection_name is None and classifier is None:
            raise ValueError(
                "Pass collection_name, collection_name with classifier_name, "
                "or an unsaved classifier.")
        if (collection_name is not None and classifier is not None
                and classifier_name is None):
            raise ValueError(
                "A classifier definition with a collection needs "
                "classifier_name: it replaces that classifier for this scan.")
        if content is not None:
            raw = content.encode("utf-8")
        else:
            # Line breaks from wrapped base64 are dropped, as the API does.
            unwrapped = content_base64.replace("\r", "").replace("\n", "")
            try:
                raw = base64.b64decode(unwrapped, validate=True)
            except ValueError as e:
                raise ValueError(f"content_base64 is not valid base64: {e}") from e
        if len(raw) > SCAN_OBJECT_MAX_BYTES:
            raise ValueError(
                f"Content is {len(raw)} bytes; the scan limit is "
                f"{SCAN_OBJECT_MAX_BYTES} bytes (128 KiB).")
        body: dict = {"content": base64.b64encode(raw).decode("ascii")}
        options = {"file_name": file_name,
                   "include_all_tokens": include_all_tokens,
                   "include_lineage": include_lineage,
                   "metadata_map": metadata_map}
        body.update({k: v for k, v in options.items() if v is not None})
        if classifier is not None:
            body["draft" if collection_name is not None else "classifier"] = classifier
        settings = get_settings()
        response = await classification.scan_object(
            body, settings.auth, collection_name, classifier_name)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_scan_objects(
            limit: int | None = None,
            contiguous_id: str | None = None,
            status: str | None = None,
            collection_name: str | None = None,
            classifier_name: str | None = None,
            order: str | None = None
            ) -> dict:
        """List past `scan_object` scans, newest first.

        Args:
            limit: Max scans per page (default 50, max 50).
            contiguous_id: Pagination token from a prior call.
            status: "COMPLETED", "FAILED" or "UNSUPPORTED_CONTENT_TYPE".
            collection_name: Only scans of this collection.
            classifier_name: Only single-classifier or unsaved-classifier
                scans of this classifier.
            order: "desc" (default) or "asc" by creation time.
        """
        settings = get_settings()
        params = {"limit": limit, "contiguous_id": contiguous_id,
                  "status": status, "collection_name": collection_name,
                  "classifier_name": classifier_name, "order": order}
        params = {k: v for k, v in params.items() if v is not None}
        response = await classification.list_scan_objects(
            params, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_scan_object(request_id: str) -> dict:
        """Get the stored summary of a scan: status, token counts, timing.

        Args:
            request_id: request_id from `scan_object` or `list_scan_objects`.
        """
        settings = get_settings()
        response = await classification.get_scan_object(
            request_id, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_scan_object_map(request_id: str) -> dict:
        """Get a scan's token map: where each classified token sits in the
        file and which classifiers matched it.

        Starts with a per-classifier summary. Each token carries its
        location (line, column, CSV row and header, or JSON/XML path) and its
        effective tags, not its value. Fails with 422 for a failed scan.

        Args:
            request_id: request_id from `scan_object` or `list_scan_objects`.
        """
        settings = get_settings()
        response = await classification.get_scan_object_map(
            request_id, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_scan_object_supported_types() -> dict:
        """List the content types `scan_object` detects and how it handles
        each, plus its size limit and metadata_map options.
        """
        settings = get_settings()
        response = await classification.get_scan_object_supported_types(
            settings.auth)
        return {"success": True, "data": response, "error": None}
