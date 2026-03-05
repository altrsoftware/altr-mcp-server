import httpx
from mcp.server.fastmcp import FastMCP

import os
from dotenv import load_dotenv
import urllib.parse
from altr_mcp.utils import policy
from altr_mcp.utils import tag
from altr_mcp.utils import snowflake
from altr_mcp.utils import classification
from altr_mcp.utils import database

# MCP setup
mcp = FastMCP("altr")

load_dotenv(override=True)


class Creds:
    def __init__(self):
        key = os.getenv('MAPI_KEY')
        secret = os.getenv('MAPI_SECRET')
        self.auth = httpx.BasicAuth(username=key, password=secret)

    def get_auth(self):
        return self.auth


creds = Creds()
Auth = creds.get_auth()


"""
REQUIREMENTS DOCUMENT UPLOAD WORKFLOW

When a user uploads a requirements document to create policy in ALTR, follow this
EXACT sequence. DO NOT SKIP ANY STEPS. Steps 5-7 are MANDATORY and must be completed
before proceeding to step 8.

1. Check databases - Use get_databases() to discover connected Snowflake databases
2. Check tags - Use get_tags() to see existing tags connected to ALTR
3. Check Policies - Use get_policies() to see existing masking policies
4. Check roles - Use get_roles() to see available ALTR roles (user groups)
5. Create a classification job - Use get_collections() first if needed, then
   create_job() to scan the database for sensitive data
   MANDATORY: You MUST complete steps 5-7 before creating any tags (step 8)
6. STOP THE PROMPT AND TELL THE USER TO WAIT - After creating the job, you MUST
   stop and inform the user to wait for the classification job to complete. Do NOT
   proceed until the job is finished. This is a CRITICAL step - do not skip it.
7. Get classification report - Use get_classification_report() with the job_id
   after the job completes. Verify the job status is COMPLETED using get_jobs() first.
8. Create snowflake tag - Use create_snowflake_tags() to create tags in Snowflake
   DO NOT proceed to this step until steps 5-7 are complete
9. Connect tag to ALTR - Use connect_tag() to make ALTR aware of the Snowflake tag
10. Create policies - Use create_policy() to create masking policies for each tag
11. Create rules - Use add_rules() to define masking behavior for each role/tag
    value combination

CRITICAL WORKFLOW RULES:
- Steps 5-7 (classification job, wait, get report) are MANDATORY and cannot be skipped
- You MUST stop after step 5 and wait for the classification job to complete
- Do NOT create tags (step 8) until you have the classification report (step 7)
- Classification jobs can take 10-30+ minutes to complete - plan accordingly
"""


@mcp.tool()
async def get_policies() -> str:
    """List all masking policies configured in your ALTR organization.

    This is STEP 3 of the requirements document upload workflow. Shows which tags
    have policies created, along with policy IDs needed for adding rules or viewing
    existing rules. Use this to verify your setup and discover existing policies
    before creating new ones.

    Requirements document workflow sequence:
    1. Check databases
    2. Check tags
    3. Check Policies (this function)
    4. Check roles
    5. Create a classification job (check collections first if needed)
    6. Stop and tell user to wait
    7. Get classification report
    8. Create snowflake tag
    9. Connect tag to ALTR
    10. Create policies
    11. Create rules

    Typical workflow: Check existing policies before creating new ones to avoid
    conflicts. After creating policies, verify they appear here. Use the policy_id
    from the results when calling `add_rules` or `get_rules`.
    """
    policies = await policy.make_altr_policy_request({}, Auth)
    formatted_polices = policy.format_policies(policies)
    return "\n---\n".join(formatted_polices)


@mcp.tool()
async def get_rules(policy_id: str) -> str:
    """View all masking rules configured for a specific policy.

    Shows which roles have what masking levels for which tag values. Use this to
    verify your security setup matches your requirements document.

    Typical workflow: After adding rules to a policy, use this to verify they're
    configured correctly. Review all policies to ensure complete coverage per
    your security requirements.

    Args:
        policy_id: URL‑encoded policy identifier as returned by `get_policies`.
    """
    rules = await policy.make_altr_rules_request({}, policy_id, Auth)
    formatted_rules = policy.format_rules(rules)
    return "\n---\n".join(formatted_rules)


@mcp.tool()
async def create_policy(tag: str) -> str:
    """Create a masking policy for a specific tag.

    This is STEP 10 of the requirements document upload workflow. Creates an empty
    masking policy that will control how data tagged with the specified tag is masked.
    Until you add rules with `add_rules`, all users will see NULL for tagged columns.

    Requirements document workflow sequence:
    1. Check databases
    2. Check tags
    3. Check Policies
    4. Check roles
    5. Create a classification job (check collections first if needed)
    6. Stop and tell user to wait
    7. Get classification report
    8. Create snowflake tag
    9. Connect tag to ALTR
    10. Create policies (this function)
    11. Create rules

    PREREQUISITE: Ensure steps 5-9 are complete before calling this function.

    IMPORTANT: The tag must already be connected to ALTR (visible in `get_tags`).
    Each tag can only have one policy. Check `get_policies` first to avoid conflicts.

    Typical workflow: After connecting tags to ALTR, create one policy per tag.
    Then use `add_rules` to define masking behavior for each role and tag value
    combination based on your security requirements.

    Args:
        tag: Tag name (UPPERCASE) as returned by `get_tags`.
    """
    return await policy.create_altr_policy({}, Auth, tag)


@mcp.tool()
async def add_rules(
        policy_id: str, masking_policy: int, role: str, tag_value: str) -> str:
    """Define how a specific role sees data with a specific tag value.

    This is STEP 11 of the requirements document upload workflow. After creating a
    policy, add rules to specify the masking behavior. Each rule defines: which role,
    which tag value, and what masking level they should see.

    Requirements document workflow sequence:
    1. Check databases
    2. Check tags
    3. Check Policies
    4. Check roles
    5. Create a classification job (check collections first if needed)
    6. Stop and tell user to wait
    7. Get classification report
    8. Create snowflake tag
    9. Connect tag to ALTR
    10. Create policies
    11. Create rules (this function)

    PREREQUISITE: Ensure steps 5-10 are complete before calling this function.

    Masking levels:
    - 10000: No mask (show raw value) - use sparingly for trusted roles
    - 10001: Full mask (hide entire value) - default for sensitive data
    - 10002: Email mask (mask local part only, e.g., j***@bank.com)
    - 10003: Show last four (mask all but last 4 chars, e.g., ****-****-1234)
    - 10004: Constant mask (replace with fixed token)

    Typical workflow: Based on your security document, add rules for each role/tag
    value combination. For example, DATA_ANALYST role with tag value "PII_US_SSN"
    might get full mask (10001), while FINANCE_MANAGER with "US_HR_COMPENSATION"
    might get no mask (10000) for their direct reports.

    Note: When creating many rules in rapid succession, you may occasionally see
    transient 4xx/5xx responses from this tool. This is usually due to the
    underlying DynamoDB tables not accepting updates quite that quickly, not a
    problem with your rule definitions. Best practice is to call `get_rules`
    after a batch to confirm which rules exist, then retry only missing ones
    with a small delay between requests.

    Args:
        policy_id: URL‑encoded policy ID from `get_policies`.
        masking_policy: Masking level (10000-10004) as described above.
        role: Target user group / role name from `get_roles`.
        tag_value: Exact tag value this rule applies to (case‑sensitive).
    """
    response = await policy.create_altr_rule(
            {}, Auth, policy_id, masking_policy, role, tag_value)
    if response and response.get("success"):
        return f"Successfully created rule for policy {policy_id}"
    else:
        error_msg = response.get("message", "Unknown error") if response else "No response from API"
        return f"Failed to create rule: {error_msg}"


@mcp.tool()
async def delete_policy(policy_id: str) -> str:
    """Delete a masking policy and all its rules.

    Use with caution - this removes all masking rules associated with the policy.
    Consider reviewing rules with `get_rules` first to understand what will be deleted.

    Args:
        policy_id: String that is the URL‑encoded policy ID, typically discovered via `get_policies`.
    """

    return await policy.delete_altr_policy({}, Auth, policy_id)


@mcp.tool()
async def delete_rule(policy_id: str, rule_id: str) -> str:
    """Remove a specific masking rule from a policy.

    Allows fine-grained removal of individual rules without deleting the entire policy.
    Use `get_rules` first to identify the rule_id you want to remove.

    Args:
        policy_id: String that is a URL‑encoded policy ID containing the rule.
        rule_id: String that is a URL‑encoded rule identifier to delete.
    """

    response = await policy.delete_altr_rule({}, Auth, policy_id, rule_id)
    if response and response.get("success"):
        return f"Successfully deleted rule {rule_id}"
    else:
        error_msg = response.get("message", "Unknown error") if response else "No response from API"
        return f"Failed to delete rule: {error_msg}"


@mcp.tool()
async def get_tags():
    """List all tags that are connected to ALTR (available for use in policies).

    This is STEP 2 of the requirements document upload workflow. Only tags that have
    been connected to ALTR via `connect_tag` will appear here. Tags created in
    Snowflake but not yet connected will not be listed.

    Requirements document workflow sequence:
    1. Check databases
    2. Check tags (this function)
    3. Check Policies
    4. Check roles
    5. Create a classification job (check collections first if needed)
    6. Stop and tell user to wait
    7. Get classification report
    8. Create snowflake tag
    9. Connect tag to ALTR
    10. Create policies
    11. Create rules

    Typical workflow: After using `connect_tag` to connect your Snowflake tags to
    ALTR, verify they appear here. These are the tags you can use when creating
    masking policies with `create_policy`.
    """
    response = await tag.make_altr_tag_request({}, Auth)
    formatted_tags = tag.format_tags(response)
    return "\n---\n".join(formatted_tags)


@mcp.tool()
async def delete_tag(tag_group_id: str):
    """
    This Delets a Tag from ALTR.
    This can only be done after all policies applied on the tag are removed.
    If any policies are applied tag removal will fail.
    """
    return await tag.delete_altr_tag(tag_group_id, {}, Auth)


@mcp.tool()
async def get_tag_values(tag_name: str):
    """List all allowed values configured for a specific tag.

    Shows which tag values exist for a tag (e.g., for tag "PII_US_SSN" you might
    see values like "RESTRICTED_HIGHLY_SENSITIVE_PII_US"). These values are what
    you'll reference when creating masking rules.

    Typical workflow: Before creating policies and rules, verify your tag values
    are correct. These values will be used in `add_rules` to specify which masking
    behavior applies to which tag value.

    Args:
        tag_name: Tag name (from `get_tags`) whose values you want to inspect.
    """
    response = await tag.make_altr_tag_values_request(
            {"filter": tag_name}, Auth)
    return response


@mcp.tool()
async def get_roles() -> str:
    """List all ALTR roles (user groups) available in your organization.

    This is STEP 4 of the requirements document upload workflow. Roles represent
    different user types (e.g., DATA_ANALYST, FINANCE_MANAGER, BRANCH_MANAGER).
    You'll use these role names when creating masking rules to define who sees what
    level of data masking.

    Requirements document workflow sequence:
    1. Check databases
    2. Check tags
    3. Check Policies
    4. Check roles (this function)
    5. Create a classification job (check collections first if needed)
    6. Stop and tell user to wait
    7. Get classification report
    8. Create snowflake tag
    9. Connect tag to ALTR
    10. Create policies
    11. Create rules

    Typical workflow: Review available roles before creating masking rules. Based
    on your security document, identify which roles need which masking levels for
    each tag value. Use these role names in `add_rules`.
    """
    user_group_names = await policy.get_user_group_names({}, Auth)
    return "\n".join(user_group_names)


@mcp.tool()
async def get_databases() -> str:
    """Discover which Snowflake databases are connected to ALTR.

    This is STEP 1 of the requirements document upload workflow. Use this as your
    starting point to identify the database you'll be securing. Returns connection
    metadata including database names and IDs needed for subsequent operations like
    creating classification jobs or connecting tags.

    Requirements document workflow sequence:
    1. Check databases (this function)
    2. Check tags
    3. Check Policies
    4. Check roles
    5. Create a classification job (check collections first if needed)
    6. Stop and tell user to wait
    7. Get classification report
    8. Create snowflake tag
    9. Connect tag to ALTR
    10. Create policies
    11. Create rules

    Typical workflow: Call this first to get your database name, then use
    `get_database_id` to get the numeric ID required for classification jobs.
    """
    databases = await database._get_databases({}, Auth)
    import json
    return json.dumps(databases, indent=2)


@mcp.tool()
async def get_database_id(database_name: str) -> str:
    """Get the ALTR database ID for a database name.

    Required before creating classification jobs. The database ID is a numeric
    identifier that ALTR uses internally to reference your Snowflake database.

    Typical workflow: After identifying your database with `get_databases`,
    call this to get the ID needed for `create_job`.

    Args:
        database_name: Friendly database name as shown in the ALTR UI.
    """
    response = await database._get_database_id(database_name, Auth)
    if response and response.get("data"):
        db_id = response.get("data", {}).get("id")
        if db_id:
            return f"Database ID for '{database_name}': {db_id}"
        else:
            return f"Database ID not found in response: {response}"
    else:
        return f"Error retrieving database ID: {response}"


@mcp.tool()
async def connect_tag(database_name: str, schema_name: str, tag_name: str):
    """Connect a Snowflake tag to ALTR so it can be used in masking policies.

    This is STEP 9 of the requirements document upload workflow. After creating tags
    in Snowflake with `create_snowflake_tags`, you must connect them to ALTR before
    they can be used for data masking. This makes ALTR aware of the tag and its values.

    Requirements document workflow sequence:
    1. Check databases
    2. Check tags
    3. Check Policies
    4. Check roles
    5. Create a classification job (check collections first if needed)
    6. Stop and tell user to wait
    7. Get classification report
    8. Create snowflake tag
    9. Connect tag to ALTR (this function)
    10. Create policies
    11. Create rules

    PREREQUISITE: Ensure steps 5-8 are complete before calling this function.

    Typical workflow: For each tag you created in Snowflake, call this to connect
    it to ALTR. Verify it appears in `get_tags` after connecting. Once connected,
    you can create masking policies for it with `create_policy`.

    Args:
        database_name: Name of the target database connection in ALTR.
        schema_name: Exact schema name inside the target database.
        tag_name: Tag to associate with this database/schema.
    Returns:
        The raw API response with success or error details.
    """
    response = await tag.connect_tag_request(
            database_name,
            schema_name,
            tag_name,
            Auth
            )

    return response


@mcp.tool()
async def get_classifiers() -> str:
    """List all available data classifiers (pattern-based detectors) in ALTR.

    Classifiers automatically detect sensitive data types like SSNs, emails,
    phone numbers, etc. Use this to see what ALTR can automatically identify
    in your database columns before you manually tag them.

    Typical workflow: Review available classifiers before running a classification
    job to understand what will be automatically detected. You can then use
    classification results to inform your manual tagging strategy.
    """
    org_id = os.getenv('ORG_ID')
    classifiers = await classification.get_classifiers({}, Auth, org_id)
    formatted_classifiers = classification.format_classifiers(classifiers)
    return "\n---\n".join(formatted_classifiers)


@mcp.tool()
async def create_classifier(
        classifier_name: str,
        description: str,
        minimum_threshold: int,
        pattern: str,
        sample_size: int
        ) -> str:
    """Create a custom data classifier for detecting specific data patterns.

    Advanced use case: If ALTR's built-in classifiers don't detect your specific
    data types, create custom classifiers with regex patterns. These can then be
    added to collections and used in classification jobs.

    Typical workflow: Only needed if you have custom data formats not covered by
    ALTR's managed classifiers. Most users can rely on existing classifiers.

    Args:
        classifier_name: Unique name for the classifier.
        description: Human‑readable explanation of what it detects.
        minimum_threshold: Percent (0–100) confidence required to consider a column a match.
        pattern: Regex pattern used to match values.
        sample_size: Number of values ALTR should sample per column.
    """
    org_id = os.getenv('ORG_ID')
    params = {
        "classifier_name": classifier_name,
        "description": description,
        "minimum_threshold": minimum_threshold,
        "pattern": pattern,
        "sample_size": sample_size,
    }
    response = await classification.create_classifier(params, Auth, org_id)
    if response and "classifier" in response:
        return f"Successfully created classifier '{classifier_name}'"
    else:
        return "Failed to create classifier: Unknown error"


@mcp.tool()
async def delete_classifier(classifier_name: str) -> str:
    """Remove a custom classifier you created.

    Cannot delete ALTR managed classifiers. Only use for classifiers you created
    with `create_classifier`.

    Args:
        classifier_name: Exact classifier name as returned by `get_classifiers`.
    """
    org_id = os.getenv('ORG_ID')
    params = {"classifier_name": classifier_name}
    response = await classification.delete_classifier(params, Auth, org_id)
    if response and response.get("success") is False:
        error_msg = response.get("message", "Unknown error")
        return f"Failed to delete classifier: {error_msg}"
    else:
        return f"Successfully deleted classifier '{classifier_name}'"


@mcp.tool()
async def get_collections() -> str:
    """List classifier collections (groups of classifiers used for classification jobs).

    Part of STEP 5 of the requirements document upload workflow. Collections bundle
    multiple classifiers together. You need a collection to run a classification job
    that scans your database for sensitive data. Check collections before creating
    a classification job.

    Requirements document workflow sequence:
    1. Check databases
    2. Check tags
    3. Check Policies
    4. Check roles
    5. Create a classification job (check collections first if needed - this function)
    6. Stop and tell user to wait
    7. Get classification report
    8. Create snowflake tag
    9. Connect tag to ALTR
    10. Create policies
    11. Create rules

    Typical workflow: Check if a suitable collection exists (e.g., "ALTR Managed"),
    or create a new one with `create_collection` before running `create_job`.
    """
    org_id = os.getenv('ORG_ID')
    collections = await classification.get_collections({}, Auth, org_id)
    formatted_collections = classification.format_collections(collections)
    return "\n---\n".join(formatted_collections)


@mcp.tool()
async def create_collection(
        collection_name: str,
        description: str = ""
        ) -> str:
    """Create a classifier collection to use for automated data discovery.

    Collections group classifiers together for classification jobs. After creating
    a collection, you can run a classification job to automatically scan your
    database columns and identify which contain sensitive data patterns.

    Typical workflow: Create a collection (or use existing "ALTR Managed"), then
    use it in `create_job` to scan your database. Review results with
    `get_classification_report` to see which columns were detected.

    Args:
        collection_name: Unique name for the collection.
        description: Optional human‑readable description.
    """
    org_id = os.getenv('ORG_ID')
    params = {
        "collection_name": collection_name,
        "description": description,
    }
    response = await classification.create_collection(params, Auth, org_id)
    if response and "collection" in response:
        return f"Successfully created collection '{collection_name}'"
    else:
        return "Failed to create collection: Unknown error"


@mcp.tool()
async def delete_collection(collection_name: str) -> str:
    """Delete a classifier collection.

    Cannot delete collections that are in use by active or recent jobs. Only
    delete collections you created that are no longer needed.

    Args:
        collection_name: Exact collection name as returned by `get_collections`.
    """
    org_id = os.getenv('ORG_ID')
    params = {"collection_name": collection_name}
    response = await classification.delete_collection(params, Auth, org_id)
    if response and response.get("success") is False:
        error_msg = response.get("message", "Unknown error")
        return f"Failed to delete collection: {error_msg}"
    else:
        return f"Successfully deleted collection '{collection_name}'"


@mcp.tool()
async def get_jobs(
        limit: int = None,
        contiguous_id: str = None,
        status: str = None,
        job_type: str = None,
        database_id: int = None,
        classification_type: int = None,
        order: str = None
        ) -> str:
    """Check the status of classification jobs you've run.

    Classification jobs run asynchronously and can take 10-30+ minutes to complete
    depending on your database size. Use this to check if a job has finished after
    waiting an appropriate amount of time.

    Once a job shows status COMPLETED, you can fetch its detailed report with
    `get_classification_report`. If status is still RUNNING, wait longer before
    checking again.

    Typical workflow: After creating a job with `create_job`, wait 15-30+ minutes,
    then use this function to check status. When status is COMPLETED, use the
    job_id with `get_classification_report` to view results.

    Args:
        limit: Max jobs to return (default 50, max 50).
        contiguous_id: Pagination token from a prior `get_jobs` call.
        status: Filter by job status (e.g. RUNNING, PAUSED, COMPLETED, CANCELLED, FAILED).
        job_type: Filter by job type (FULL, INCREMENTAL, RECLASSIFICATION).
        database_id: Restrict to a specific database (numeric ID from `get_databases` / `get_database_id`).
        classification_type: Optional ALTR classification type code (1–5).
        order: Sort order by start time, `asc` or `desc` (default `desc`).
    """
    org_id = os.getenv('ORG_ID')
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
    jobs = await classification.get_jobs(params, Auth, org_id)
    formatted_jobs = classification.format_jobs(jobs)
    return "\n---\n".join(formatted_jobs)


@mcp.tool()
async def create_job(
        job_type: str,
        database_id: int,
        collection_name: str
        ) -> str:
    """Run an automated classification scan to discover sensitive data in your database.

    This is STEP 5 of the requirements document upload workflow. This scans your
    database columns using the classifiers in the specified collection to automatically
    identify columns containing PII, financial data, etc.

    Requirements document workflow sequence:
    1. Check databases
    2. Check tags
    3. Check Policies
    4. Check roles
    5. Create a classification job (this function - check collections first if needed)
    6. STOP THE PROMPT AND TELL THE USER TO WAIT - This is a critical step. After
       creating the job, you must stop and inform the user that they need to wait
       for the classification job to complete before proceeding.
    7. Get classification report
    8. Create snowflake tag
    9. Connect tag to ALTR
    10. Create policies
    11. Create rules

    MANDATORY WORKFLOW: Steps 5-7 (this function, wait, get report) are REQUIRED
    and cannot be skipped. You MUST complete the classification process before
    creating any tags in step 8. Do NOT skip to creating tags without first running
    and completing the classification job.

    IMPORTANT: Classification jobs run asynchronously and can take a significant amount
    of time (often 10-30+ minutes depending on database size). The job will continue
    running in the background after this function returns.

    CRITICAL WORKFLOW STEP: After calling this function and receiving a job_id, you
    MUST stop the current workflow and explicitly tell the user to wait. Do NOT proceed
    to step 7 (get_classification_report) until the user indicates the job has completed
    or you verify the job status is COMPLETED using `get_jobs`. Do NOT proceed to step 8
    (create_snowflake_tags) until step 7 is complete.

    Once the job completes:
    1. Use `get_jobs` to verify status is COMPLETED
    2. Then proceed to step 7: use `get_classification_report` with the job_id to view results
    3. Only after getting the classification report should you proceed to step 8 (create tags)

    Typical workflow: After creating/selecting a collection, run a FULL classification
    job. After creating the job, STOP and tell the user to wait. Once the job completes,
    use the classification report to see which columns were detected and inform your
    tagging strategy.

    Args:
        job_type: Job type to run (FULL, INCREMENTAL, RECLASSIFICATION).
        database_id: Target database ID (from `get_databases` / `get_database_id`).
        collection_name: Classifier collection to use for this run.
    """
    org_id = os.getenv('ORG_ID')
    params = {
        "job_type": job_type,
        "database_id": database_id,
        "collection_name": collection_name,
    }
    response = await classification.create_job(params, Auth, org_id)
    if response and "job_id" in response:
        job_id = response.get("job_id", "unknown")
        status = response.get("status", "unknown")
        return f"Successfully created job '{job_id}' with status '{status}'"
    else:
        return "Failed to create job: Unknown error"


@mcp.tool()
async def update_job_status(job_id: str, status: str) -> str:
    """Control a running classification job (pause, cancel, or resume).

    Use to manage long-running classification jobs. Status options: PAUSED,
    CANCELLED, or RUNNING.

    Args:
        job_id: Job identifier to update.
        status: New status (PAUSED, CANCELLED, or RUNNING).
    """
    org_id = os.getenv('ORG_ID')
    encoded_id = urllib.parse.quote(job_id, safe='')
    params = {"status": status}
    response = await classification.update_job_status(
            params, Auth, org_id, encoded_id)
    if response and response.get("status") == status:
        return f"Successfully updated job '{job_id}' status to '{status}'"
    elif response:
        return f"Job status updated. Current status: {response.get('status', 'unknown')}"
    else:
        return "Failed to update job status: Unknown error"


@mcp.tool()
async def get_classification_report(job_id: str) -> dict:
    """Get detailed results from a completed classification job.

    This is STEP 7 of the requirements document upload workflow. Returns which columns
    were detected as containing sensitive data (SSNs, emails, phone numbers, etc.)
    along with confidence scores. Use this to understand what data needs protection
    before you create tags and policies.

    Requirements document workflow sequence:
    1. Check databases
    2. Check tags
    3. Check Policies
    4. Check roles
    5. Create a classification job (check collections first if needed)
    6. Stop and tell user to wait
    7. Get classification report (this function)
    8. Create snowflake tag
    9. Connect tag to ALTR
    10. Create policies
    11. Create rules

    MANDATORY: This step MUST be completed before proceeding to step 8 (create tags).
    Do NOT skip this step or proceed to create_snowflake_tags() until you have
    retrieved and reviewed the classification report.

    IMPORTANT: Only call this function after the classification job from step 5 has
    completed. Verify job status is COMPLETED using `get_jobs` before proceeding.

    Typical workflow: After a classification job completes, use this to see which
    columns contain sensitive data. This helps you decide which tag values to create
    and which columns to tag in your security setup.

    Args:
        job_id: Job identifier returned from `create_job` or listed by `get_jobs`.
    """
    org_id = os.getenv('ORG_ID')
    params = {}
    return await classification.get_job_report(params, Auth, org_id, job_id)


@mcp.tool()
async def create_snowflake_tags(
        allowed_values_list: dict,
        database_name: str,
        schema_name: str,
        tag_name: str
        ) -> str:
    """Create a Snowflake tag with allowed values and apply it to columns.

    This is STEP 8 of the requirements document upload workflow. Creates a tag in
    Snowflake (e.g., "PII_US_SSN") with specific allowed values (e.g.,
    "RESTRICTED_HIGHLY_SENSITIVE_PII_US") and applies those tag values to the
    appropriate columns in your table.

    Requirements document workflow sequence:
    1. Check databases
    2. Check tags
    3. Check Policies
    4. Check roles
    5. Create a classification job (check collections first if needed)
    6. Stop and tell user to wait
    7. Get classification report
    8. Create snowflake tag (this function)
    9. Connect tag to ALTR
    10. Create policies
    11. Create rules

    CRITICAL: Do NOT call this function until steps 5-7 are complete. You MUST:
    - Create a classification job (step 5)
    - Wait for the job to complete (step 6)
    - Get the classification report (step 7)

    Only after you have the classification report should you proceed to create tags.
    Skipping the classification steps will result in an incomplete setup.

    The allowed_values_list maps each tag value to which columns should receive it.
    Dictionary structure: Each key is a tag value (allowed value), and each value
    is a dict with 'table' (string) and 'columns' (list of strings).

    Example for Acme Bank PII_EMPLOYEES table:
    {
        "PII_US_CONTACT_EMAIL": {
            "table": "PII_EMPLOYEES",
            "columns": ["EMAIL"]
        },
        "PII_US_CONTACT_PHONE": {
            "table": "PII_EMPLOYEES",
            "columns": ["PHONE"]
        },
        "RESTRICTED_HIGHLY_SENSITIVE_PII_US": {
            "table": "PII_EMPLOYEES",
            "columns": ["SSN"]
        },
        "PII_US_ADDRESS_STREET": {
            "table": "PII_EMPLOYEES",
            "columns": ["STREET"]
        },
        "PII_US_ADDRESS_ZIP": {
            "table": "PII_EMPLOYEES",
            "columns": ["ZIPCODE"]
        },
        "US_HR_COMPENSATION": {
            "table": "PII_EMPLOYEES",
            "columns": ["SALARY"]
        }
    }

    IMPORTANT: After creating tags in Snowflake, you must connect them to ALTR
    using `connect_tag` before they can be used in masking policies.

    This function requires:
    - SNOWFLAKE_ACCOUNT environment variable to be set
    - SNOWFLAKE_PAT (Personal Access Token) environment variable to be set
    - SNOWFLAKE_ROLE environment variable (defaults to 'ACCOUNTADMIN' if not set)
    - SNOWFLAKE_WAREHOUSE environment variable (defaults to 'DAILY_XS_WH' if not set)

    Typical workflow: Based on your security document, create tags for each sensitivity
    category (e.g., PII_US_SSN, PII_US_CONTACT_EMAIL). Then use `connect_tag` to
    make ALTR aware of them.

    Args:
        allowed_values_list: A dictionary mapping tag values to table/column configurations.
                           Each key is a tag value string, and each value is a dict with:
                           - 'table': string - The table name
                           - 'columns': list - List of column names to tag

        database_name: The name of the Snowflake database where the tag should be created.
                 This database must exist and be accessible with the provided credentials.

        schema_name: The name of the schema within the database where the tag should be created.
               This schema must exist within the specified database.

        tag_name: The name of the tag to create or replace in Snowflake. This will be the
                 tag identifier used in Snowflake's tagging system. The tag will be created
                 with the allowed values specified in the allowed_values_list keys.
    """

    result = await snowflake.create_snowflake_tags(
        allowed_values_list,
        database_name,
        schema_name,
        tag_name
    )

    if result and not result.startswith("Request failed"):
        return f"Successfully created tag. Fully qualified name: {result}"
    else:
        return result if result else "Failed to create tag in Snowflake. Check the logs for details."


def main():
    # Initialize and run the server
    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()
