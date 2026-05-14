import urllib.parse

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from altr_mcp.settings import get_settings
from altr_mcp.utils import classification
from altr_mcp.utils.logging import log_tool


def register(mcp: FastMCP) -> None:

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_classifiers() -> dict:
        """List all available data classifiers
        (pattern-based detectors) in ALTR.

        Classifiers automatically detect sensitive data
        types like SSNs, emails,
        and phone numbers. Includes both ALTR-managed and custom classifiers.
        """
        settings = get_settings()
        classifiers = await classification.get_classifiers(
            {}, settings.auth, settings.org_id)
        return {"success": True, "data": classifiers, "error": None}

    @mcp.tool()
    @log_tool
    async def create_classifier(
            classifier_name: str,
            description: str,
            minimum_threshold: int,
            pattern: str,
            sample_size: int
            ) -> dict:
        """Create a custom data classifier for detecting
        specific data patterns.

        Use when ALTR's built-in classifiers don't cover
        your data types. Custom classifiers can be added
        to collections and used in classification jobs.

        Args:
            classifier_name: Unique name for the classifier.
            description: Human‑readable explanation of what it detects.
            minimum_threshold: Percent (0-100) confidence
                required to consider a column a match.
            pattern: Regex pattern used to match values.
            sample_size: Number of values ALTR should sample per column.
        """
        settings = get_settings()
        params = {
            "classifier_name": classifier_name,
            "description": description,
            "minimum_threshold": minimum_threshold,
            "pattern": pattern,
            "sample_size": sample_size,
        }
        response = await classification.create_classifier(
            params, settings.auth, settings.org_id)
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
            params, settings.auth, settings.org_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_collections() -> dict:
        """List classifier collections (groups of classifiers
        used for classification jobs).

        A collection is required when creating a classification
        job with `create_job`. Check for existing collections
        (e.g., "ALTR Managed") before creating new ones.
        """
        settings = get_settings()
        collections = await classification.get_collections(
            {}, settings.auth, settings.org_id)
        return {"success": True, "data": collections, "error": None}

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
        existing "ALTR Managed"), then use it in
        `create_job` to scan your database. Review results
        with `get_classification_report` to see which
        columns were detected.

        Args:
            collection_name: Unique name for the collection.
            description: Optional human‑readable description.
        """
        settings = get_settings()
        params = {
            "collection_name": collection_name,
            "description": description,
        }
        response = await classification.create_collection(
            params, settings.auth, settings.org_id)
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
            params, settings.auth, settings.org_id)
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

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_jobs(
            limit: int | None = None,
            contiguous_id: str | None = None,
            status: str | None = None,
            job_type: str | None = None,
            database_id: int | None = None,
            classification_type: int | None = None,
            order: str | None = None
            ) -> dict:
        """Check the status of classification jobs you've run.

        Classification jobs run asynchronously and can take
        10-30+ minutes to complete depending on your database
        size. Use this to check if a job has finished after
        waiting an appropriate amount of time.

        Once a job shows status COMPLETED, you can fetch its
        detailed report with `get_classification_report`. If
        status is still RUNNING, wait longer before checking
        again.

        Typical workflow: After creating a job with
        `create_job`, wait 15-30+ minutes, then use this
        function to check status. When status is COMPLETED,
        use the job_id with `get_classification_report` to
        view results.

        Args:
            limit: Max jobs to return (default 50, max 50).
            contiguous_id: Pagination token from a prior
                `get_jobs` call.
            status: Filter by job status (e.g. RUNNING,
                PAUSED, COMPLETED, CANCELLED, FAILED).
            job_type: Filter by job type (FULL,
                INCREMENTAL, RECLASSIFICATION).
            database_id: Restrict to a specific database
                (numeric ID from `get_databases` /
                `get_database_id`).
            classification_type: Optional ALTR
                classification type code (1-5).
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
        if classification_type is not None:
            params["classification_type"] = classification_type
        if order:
            params["order"] = order
        jobs = await classification.get_jobs(
            params, settings.auth, settings.org_id)
        return {"success": True, "data": jobs, "error": None}

    @mcp.tool()
    @log_tool
    async def create_job(
            job_type: str,
            database_id: int,
            collection_name: str
            ) -> dict:
        """Run an automated classification scan to discover
        sensitive data in your database.

        Scans database columns using classifiers in the
        specified collection to identify columns containing
        PII, financial data, etc.

        Classification jobs run asynchronously and can take
        10-30+ minutes depending on database size. After
        creating a job, use `get_jobs` to poll for
        completion, then `get_classification_report` to
        view results.

        Args:
            job_type: Job type to run (FULL, INCREMENTAL, RECLASSIFICATION).
            database_id: Target database ID (from
                `get_databases` / `get_database_id`).
            collection_name: Classifier collection to use for this run.
        """
        settings = get_settings()
        params = {
            "job_type": job_type,
            "database_id": database_id,
            "collection_name": collection_name,
        }
        response = await classification.create_job(
            params, settings.auth, settings.org_id)
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
            params, settings.auth, settings.org_id, encoded_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_databricks_job(database_id: int) -> dict:
        """Run a GDLP classification scan on a Databricks database.

        Scans the Databricks catalog to identify sensitive data columns using
        ALTR's built-in GDLP classifiers. Runs asynchronously — after
        creating the job, use `get_jobs` to poll for completion, then
        `get_classification_report` to view results.

        Args:
            database_id: ALTR database ID for the Databricks connection
                (from `get_databases` / `get_database_id`).
        """
        settings = get_settings()
        params = {"database_id": database_id}
        response = await classification.create_databricks_job(
            params, settings.auth, settings.org_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_classification_report(job_id: str) -> dict:
        """Get detailed results from a completed classification job.

        Returns which columns were detected as containing
        sensitive data along with confidence scores. Only call
        after the job status is COMPLETED (verify with
        `get_jobs`).

        After reviewing results, check if the needed Snowflake
        tags exist using `get_tags`. If tags are missing, they
        must be created in Snowflake first before connecting
        with `connect_tag`.

        Args:
            job_id: Job identifier returned from `create_job`
                or listed by `get_jobs`.
        """
        settings = get_settings()
        params = {}
        response = await classification.get_job_report(
            params, settings.auth, settings.org_id, job_id)
        return {"success": True, "data": response, "error": None}
