"""Integration tests for classification tools (altr_mcp/tools/classification.py).

Tests the classification tools using pytest-httpx to mock HTTP responses.
Verifies the {success, data, error} response shape for happy paths.
"""
import base64
import json

import httpx
import pytest
from fastmcp import FastMCP
from pytest_httpx import HTTPXMock

from altr_mcp.tools.classification import register
from tests.integration.conftest import get_tool


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


# ── get_classifiers ─────────────────────────────────────────────────────


async def test_get_classifiers_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_classifiers returns {success, data, error} with classifier list."""
    httpx_mock.add_response(json={
        "classifiers": [
            {
                "classifier_name": "SSN_DETECTOR",
                "description": "Detects SSN patterns",
                "pattern": r"\d{3}-\d{2}-\d{4}",
                "minimum_threshold": 80,
                "sample_size": 100,
                "sample_type": "ROWS",
                "collection_names": ["ALTR Managed"],
                "collection_count": 1,
            }
        ],
        "contiguous_id": None,
    })
    fn = await get_tool(mcp, "get_classifiers")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── create_classifier ───────────────────────────────────────────────────


async def test_create_classifier_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_classifier returns {success, data, error} on successful creation."""
    httpx_mock.add_response(status_code=201, json={
        "classifier": {
            "classifier_name": "MY_CLASSIFIER",
            "description": "Test classifier",
            "compound_ruleset": {"operator": "AND", "conditions": [
                {"target": "ROW_DATA", "pattern": r"\d{3}-\d{2}-\d{4}",
                 "comparator": "matches", "minimum_threshold": 80}]},
            "collection_names": [],
            "collection_count": 0,
        },
    })
    ruleset = {"operator": "AND", "conditions": [{
        "target": "ROW_DATA", "pattern": r"\d{3}-\d{2}-\d{4}",
        "comparator": "matches", "minimum_threshold": 80}]}
    fn = await get_tool(mcp, "create_classifier")
    result = await fn(
        classifier_name="MY_CLASSIFIER",
        description="Test classifier",
        compound_ruleset=ruleset,
    )
    assert result["success"] is True
    assert result["error"] is None
    assert json.loads(httpx_mock.get_requests()[0].content) == {
        "classifier_name": "MY_CLASSIFIER",
        "description": "Test classifier",
        "compound_ruleset": ruleset,
    }


@pytest.mark.parametrize("tool", ["create_classifier", "update_classifier"])
async def test_classifier_tools_offer_only_rulesets(mcp, tool):
    """Pattern-only classifiers are not offered; logic lives in the ruleset."""
    properties = (await mcp.get_tool(tool)).parameters["properties"]
    assert not {"pattern", "minimum_threshold", "sample_size"} & set(properties)
    assert "compound_ruleset" in properties


async def test_create_classifier_requires_a_ruleset(mcp):
    required = (await mcp.get_tool("create_classifier")).parameters["required"]
    assert set(required) == {"classifier_name", "compound_ruleset"}


# ── delete_classifier ───────────────────────────────────────────────────


async def test_delete_classifier_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """delete_classifier returns {success, data, error} on successful deletion."""
    httpx_mock.add_response(status_code=204, content=b"")
    fn = await get_tool(mcp, "delete_classifier")
    result = await fn(classifier_name="MY_CLASSIFIER")
    assert result["success"] is True
    assert result["error"] is None


# ── get_collections ─────────────────────────────────────────────────────


async def test_get_collections_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_collections returns {success, data, error} with collection list."""
    httpx_mock.add_response(json={
        "collections": [
            {
                "collection_name": "ALTR Managed",
                "description": "Default collection",
                "classifier_count": 5,
                "org_id": "org-123",
                "deleted_at": None,
            }
        ],
        "contiguous_id": None,
    })
    fn = await get_tool(mcp, "get_collections")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── create_collection ───────────────────────────────────────────────────


async def test_create_collection_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_collection returns {success, data, error} on successful creation."""
    httpx_mock.add_response(status_code=201, json={
        "collection": {
            "collection_name": "MY_COLLECTION",
            "description": "Test collection",
            "classifier_count": 0,
            "org_id": "org-123",
            "deleted_at": None,
        },
    })
    fn = await get_tool(mcp, "create_collection")
    result = await fn(collection_name="MY_COLLECTION", description="Test collection")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── delete_collection ───────────────────────────────────────────────────


async def test_delete_collection_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """delete_collection returns {success, data, error} on successful deletion."""
    httpx_mock.add_response(status_code=204, content=b"")
    fn = await get_tool(mcp, "delete_collection")
    result = await fn(collection_name="MY_COLLECTION")
    assert result["success"] is True
    assert result["error"] is None


# ── get_jobs ────────────────────────────────────────────────────────────


async def test_get_jobs_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """get_jobs returns {success, data, error} with job list."""
    httpx_mock.add_response(json={
        "jobs": [
            {
                "job_id": "j1",
                "database_id": 1,
                "agent_id": "agent-001",
                "collection_name": "ALTR Managed",
                "job_type": "FULL",
                "status": "COMPLETED",
                "classification_type": 1,
                "sample_strategy": "ROWS",
                "started_at": "2025-01-15T10:00:00Z",
                "completed_at": "2025-01-15T10:05:00Z",
                "updated_at": "2025-01-15T10:05:00Z",
                "cols_processed": 50,
                "retry_count": 0,
                "org_id": "org-123",
            }
        ],
        "contiguous_id": None,
    })
    fn = await get_tool(mcp, "get_jobs")
    result = await fn()
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_get_jobs_with_filters(httpx_mock: HTTPXMock, test_env, mcp):
    """get_jobs passes filter params and returns data."""
    httpx_mock.add_response(json={
        "jobs": [
            {
                "job_id": "j2",
                "database_id": 1,
                "collection_name": "ALTR Managed",
                "job_type": "FULL",
                "status": "RUNNING",
                "classification_type": 1,
                "started_at": "2025-02-01T09:00:00Z",
                "updated_at": "2025-02-01T09:00:00Z",
                "cols_processed": 0,
                "retry_count": 0,
                "org_id": "org-123",
            }
        ],
        "contiguous_id": None,
    })
    fn = await get_tool(mcp, "get_jobs")
    result = await fn(status="RUNNING", limit=5)
    assert result["success"] is True
    assert result["error"] is None


# ── create_job ──────────────────────────────────────────────────────────


async def test_create_job_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """create_job returns {success, data, error} on job creation."""
    httpx_mock.add_response(status_code=201, json={
        "job_id": "j1",
        "database_id": 1,
        "collection_name": "ALTR Managed",
        "job_type": "FULL",
        "status": "CREATED",
        "classification_type": 0,
        "sample_strategy": "ROWS",
        "started_at": None,
        "completed_at": None,
        "updated_at": "2025-01-15T10:00:00Z",
        "cols_processed": 0,
        "retry_count": 0,
        "org_id": "org-123",
    })
    fn = await get_tool(mcp, "create_job")
    result = await fn(job_type="FULL", database_id=1, collection_name="ALTR Managed")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result
    request = httpx_mock.get_request()
    assert "/jobs/snowflake" in str(request.url)
    body = json.loads(request.content)
    assert body == {
        "job_type": "FULL",
        "database_id": 1,
        "collection_name": "ALTR Managed",
        "classification_type": "altr_native",
    }


# ── update_job_status ───────────────────────────────────────────────────


async def test_update_job_status_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """update_job_status returns {success, data, error} on successful update."""
    httpx_mock.add_response(json={
        "job_id": "j1",
        "database_id": 1,
        "collection_name": "ALTR Managed",
        "job_type": "FULL",
        "status": "PAUSED",
        "classification_type": 0,
        "updated_at": "2025-01-15T10:02:00Z",
        "cols_processed": 25,
        "retry_count": 0,
        "org_id": "org-123",
    })
    fn = await get_tool(mcp, "update_job_status")
    result = await fn(job_id="j1", status="PAUSED")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


# ── get_classification_report ───────────────────────────────────────────


async def test_get_classification_report_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_classification_report returns {success, data, error} with report data.

    get_job_report makes 2 HTTP calls:
    1. POST to /v1/jobs/{job_id}/report -> returns {"url": "...", "expiration": "..."}
    2. GET <presigned-url> -> returns actual report JSON
    """
    report_url = "https://s3.amazonaws.com/reports/j1"
    # First response: create report -> returns presigned URL + expiration
    httpx_mock.add_response(status_code=201, json={
        "url": report_url,
        "expiration": "2025-01-15T11:00:00Z",
    })
    # Second response: fetch report from presigned URL
    httpx_mock.add_response(json={
        "job_id": "j1",
        "columns": [{"column_name": "EMAIL", "classifier": "EMAIL_DETECTOR"}],
    })
    fn = await get_tool(mcp, "get_classification_report")
    result = await fn(job_id="j1")
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


async def test_report_download_uses_the_shared_client_and_timeout(
        httpx_mock: HTTPXMock, test_env, mcp, monkeypatch):
    """The presigned GET honors REQUEST_TIMEOUT and shares the client.

    get_job_report fetches the report outside api.request, so it had its own
    one-off httpx.AsyncClient on httpx's 5s default -- short for a report
    download -- and the happy-path test above asserts only the response
    shape, so reverting it was undetectable.
    """
    monkeypatch.setenv("REQUEST_TIMEOUT", "12")
    report_url = "https://s3.amazonaws.com/reports/j1"
    httpx_mock.add_response(status_code=201, json={
        "url": report_url,
        "expiration": "2025-01-15T11:00:00Z",
    })
    httpx_mock.add_response(url=report_url, json={"job_id": "j1"})

    built = 0
    real_init = httpx.AsyncClient.__init__

    def counting_init(self, *args, **kwargs):
        nonlocal built
        built += 1
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", counting_init)

    fn = await get_tool(mcp, "get_classification_report")
    result = await fn(job_id="j1")
    assert result["success"] is True

    # Both the POST and the presigned GET go through one client.
    assert built == 1, f"expected one shared client, {built} were built"
    download = next(
        r for r in httpx_mock.get_requests() if str(r.url) == report_url)
    assert download.extensions["timeout"] == httpx.Timeout(12.0).as_dict()


async def test_report_download_reports_an_expired_url(
        httpx_mock: HTTPXMock, test_env, mcp):
    """An expired presigned URL names the failure instead of crashing.

    S3 answers an expired URL with 403 and an XML body, so the unguarded
    resp.json() raised JSONDecodeError and the operator saw a JSON parse
    error rather than the actual cause.
    """
    report_url = "https://s3.amazonaws.com/reports/j1"
    httpx_mock.add_response(status_code=201, json={
        "url": report_url,
        "expiration": "2025-01-15T11:00:00Z",
    })
    httpx_mock.add_response(
        url=report_url,
        status_code=403,
        text="<Error><Code>AccessDenied</Code></Error>",
    )

    fn = await get_tool(mcp, "get_classification_report")
    result = await fn(job_id="j1")
    inner = result["data"]
    assert inner["success"] is False
    assert inner["status_code"] == 403
    assert "403" in inner["message"]


# ── error path ──────────────────────────────────────────────────────────


async def test_classification_domain_error_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """classification domain returns success:True wrapping an error data payload on 404."""
    httpx_mock.add_response(status_code=404)
    fn = await get_tool(mcp, "delete_classifier")
    # 404 is non-retryable -> api.request returns {success: False} dict
    # Tool wraps it: {success: True, data: {success: False, ...}, error: None}
    result = await fn(classifier_name="NONEXISTENT")
    assert isinstance(result, dict)
    # Tool layer success is True; inner data indicates failure
    assert result["success"] is True
    assert result["error"] is None
    inner = result["data"]
    assert inner.get("success") is False


# ── create_databricks_job ────────────────────────────────────────────────


async def test_create_databricks_job_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_databricks_job returns {success, data, error} on creation."""
    httpx_mock.add_response(status_code=201, json={
        "job_id": "dbx-job-uuid-1234",
        "database_id": 42,
        "status": "CREATED",
        "classification_type": 6,
        "platform": "databricks",
    })
    fn = await get_tool(mcp, "create_databricks_job")
    result = await fn(database_id=42)
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result
    request = httpx_mock.get_request()
    assert "/jobs/databricks" in str(request.url)
    body = json.loads(request.content)
    assert body == {"database_id": 42}


async def test_create_databricks_job_with_collection(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_databricks_job forwards collection_name when given."""
    httpx_mock.add_response(status_code=201, json={
        "job_id": "dbx-job-uuid-5678",
        "database_id": 57,
        "status": "CREATED",
        "classification_type": 6,
        "platform": "databricks",
    })
    fn = await get_tool(mcp, "create_databricks_job")
    result = await fn(database_id=57, collection_name="financial_pci")
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert "/jobs/databricks" in str(request.url)
    body = json.loads(request.content)
    assert body == {"database_id": 57, "collection_name": "financial_pci"}


# ── create_gdlp_job ──────────────────────────────────────────────────────


async def test_create_gdlp_job_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_gdlp_job (Snowflake GDLP) posts to /v1/jobs/snowflake with a
    gdlp classification_type and wraps the response."""
    httpx_mock.add_response(status_code=201, json={
        "job_id": "gdlp-job-uuid-1234",
        "database_id": 42,
        "status": "CREATED",
        "classification_type": 1,
    })
    fn = await get_tool(mcp, "create_gdlp_job")
    result = await fn(database_id=42)
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result
    request = httpx_mock.get_request()
    assert "/jobs/snowflake" in str(request.url)
    body = json.loads(request.content)
    assert body == {"database_id": 42, "classification_type": "gdlp"}


async def test_create_gdlp_job_with_collection_and_sampling(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_gdlp_job forwards collection_name and sampling fields when given."""
    httpx_mock.add_response(status_code=201, json={
        "job_id": "gdlp-job-uuid-5678",
        "database_id": 42,
        "status": "CREATED",
        "classification_type": 1,
    })
    fn = await get_tool(mcp, "create_gdlp_job")
    result = await fn(
        database_id=42,
        collection_name="financial_pci",
        sample_size=250,
        sample_type="ROWS",
    )
    assert result["success"] is True
    request = httpx_mock.get_request()
    assert "/jobs/snowflake" in str(request.url)
    body = json.loads(request.content)
    assert body == {
        "database_id": 42,
        "classification_type": "gdlp",
        "collection_name": "financial_pci",
        "sample_size": 250,
        "sample_type": "ROWS",
    }


# ── create_oltp_job ──────────────────────────────────────────────────────


async def test_create_oltp_job_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_oltp_job returns {success, data, error} on creation."""
    httpx_mock.add_response(status_code=201, json={
        "job_id": "oltp-job-uuid-1234",
        "repository": {"name": "postgres_db", "type": "Postgres"},
        "collection_name": "oltp-demo",
        "status": "CREATED",
        "classification_type": 5,
    })
    fn = await get_tool(mcp, "create_oltp_job")
    result = await fn(
        agent_id="agent-uuid-1234",
        repo_name="postgres_db",
        service_user_name="postgres_service",
        collection_name="oltp-demo",
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result
    request = httpx_mock.get_request()
    assert "/jobs/oltp" in str(request.url)
    body = json.loads(request.content)
    # The four required params plus the four defaulted sampling fields.
    assert body == {
        "agent_id": "agent-uuid-1234",
        "repo_name": "postgres_db",
        "service_user_name": "postgres_service",
        "collection_name": "oltp-demo",
        "classification_type": 5,
        "sample_strategy": "ROWS",
        "sample_size": 1000,
        "sample_type": "ROWS",
    }


# ── add/remove classifiers to collection ─────────────────────────────────


async def test_add_classifiers_to_collection_scalar(
        httpx_mock: HTTPXMock, test_env, mcp):
    """A single classifier_names string is wrapped in a one-element list."""
    httpx_mock.add_response(json={"success": True})
    fn = await get_tool(mcp, "add_classifiers_to_collection")
    result = await fn(
        collection_name="my-collection",
        classifier_names="EMAIL",
    )
    assert result["success"] is True
    body = json.loads(httpx_mock.get_request().content)
    assert body == {"classifier_names": ["EMAIL"]}


async def test_add_classifiers_to_collection_list(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"success": True})
    fn = await get_tool(mcp, "add_classifiers_to_collection")
    result = await fn(
        collection_name="my-collection",
        classifier_names=["EMAIL", "SSN"],
    )
    assert result["success"] is True
    body = json.loads(httpx_mock.get_request().content)
    assert body == {"classifier_names": ["EMAIL", "SSN"]}


async def test_remove_classifiers_from_collection_scalar(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"success": True})
    fn = await get_tool(mcp, "remove_classifiers_from_collection")
    result = await fn(
        collection_name="my-collection",
        classifier_names="EMAIL",
    )
    assert result["success"] is True


# ── get_jobs with full filter set ────────────────────────────────────────


async def test_get_jobs_all_filters(httpx_mock: HTTPXMock, test_env, mcp):
    """get_jobs forwards every filter param in the query string."""
    httpx_mock.add_response(json={"jobs": []})
    fn = await get_tool(mcp, "get_jobs")
    result = await fn(
        limit=25,
        contiguous_id="cur",
        status="COMPLETED",
        job_type="FULL",
        database_id=42,
        classification_type=2,
        order="asc",
    )
    assert result["success"] is True
    url = str(httpx_mock.get_request().url)
    for fragment in (
        "limit=25",
        "contiguous_id=cur",
        "status=COMPLETED",
        "job_type=FULL",
        "database_id=42",
        "classification_type=2",
        "order=asc",
    ):
        assert fragment in url


# ── invalid JSON / 5xx retry ─────────────────────────────────────────────────


async def test_classification_invalid_json_response(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(
        content=b"<html>Bad Gateway</html>",
        headers={"Content-Type": "text/html"},
    )
    fn = await get_tool(mcp, "delete_classifier")
    result = await fn(classifier_name="test-classifier")
    assert result["success"] is True
    assert "raw" in result["data"]


async def test_classification_5xx_retry_exhaustion(
        httpx_mock: HTTPXMock, retry_env, mcp):
    httpx_mock.add_response(status_code=500)
    httpx_mock.add_response(status_code=500)
    fn = await get_tool(mcp, "delete_classifier")
    result = await fn(classifier_name="test-classifier")
    assert result["success"] is True
    assert result["data"]["success"] is False
    assert "Retry exhausted" in result["data"]["message"]


# ══════════════════════════════════════════════════════════════════════════
# Coverage for the remaining classification tools.
#
# Each tool builds a params/data dict from its optional arguments and
# forwards it to altr_mcp.utils.classification. Tests below pass every
# optional argument so the `if x is not None` branches are exercised, not
# just the call itself; a second test covers the bare path where omitting
# the arguments takes a different branch.


# ══════════════════════════════════════════════════════════════════════════


# ── classifiers ─────────────────────────────────────────────────────────


async def test_get_classifier_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """get_classifier fetches a single classifier by name."""
    httpx_mock.add_response(json={"classifier_name": "SSN_DETECTOR"})
    fn = await get_tool(mcp, "get_classifier")
    result = await fn(classifier_name="SSN_DETECTOR")
    assert result == {
        "success": True,
        "data": {"classifier_name": "SSN_DETECTOR"},
        "error": None,
    }


async def test_get_classifier_url_encodes_the_name(
        httpx_mock: HTTPXMock, test_env, mcp):
    """A name with a slash is encoded rather than forming a new path segment."""
    httpx_mock.add_response(json={"classifier_name": "a/b"})
    fn = await get_tool(mcp, "get_classifier")
    await fn(classifier_name="a/b")
    assert "a%2Fb" in str(httpx_mock.get_requests()[0].url)


async def test_update_classifier_sends_every_provided_field(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Each optional field provided reaches the request body."""
    httpx_mock.add_response(json={"classifier_name": "C"})
    fn = await get_tool(mcp, "update_classifier")
    result = await fn(
        classifier_name="C",
        description="updated",
        compound_ruleset={"operator": "AND", "conditions": [
            {"target": "METADATA", "comparator": "contains", "pattern": "ssn"}]},
    )
    assert result["success"] is True
    request = httpx_mock.get_requests()[0]
    assert request.method == "PATCH"
    assert json.loads(request.content) == {
        "description": "updated",
        "compound_ruleset": {"operator": "AND", "conditions": [
            {"target": "METADATA", "comparator": "contains", "pattern": "ssn"}]},
        # The threshold is not cleared, because a 0 threshold matches all.
        "pattern": None,
    }


async def test_update_classifier_omits_unset_fields(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Only the name is required; unset fields are left out of the body."""
    httpx_mock.add_response(json={"classifier_name": "C"})
    fn = await get_tool(mcp, "update_classifier")
    result = await fn(classifier_name="C", description="only this")
    assert result["success"] is True
    assert json.loads(httpx_mock.get_requests()[0].content) == {
        "description": "only this"}


# ── collections ─────────────────────────────────────────────────────────


async def test_get_collection_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """get_collection fetches a single collection by name."""
    httpx_mock.add_response(json={"collection_name": "ALTR Managed"})
    fn = await get_tool(mcp, "get_collection")
    result = await fn(collection_name="ALTR Managed")
    assert result["success"] is True
    assert result["data"]["collection_name"] == "ALTR Managed"


async def test_update_collection_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """update_collection sends the new description."""
    httpx_mock.add_response(json={"collection_name": "C"})
    fn = await get_tool(mcp, "update_collection")
    result = await fn(collection_name="C", description="new description")
    assert result["success"] is True
    request = httpx_mock.get_requests()[0]
    assert request.method == "PATCH"
    assert json.loads(request.content)["description"] == "new description"


async def test_get_collection_classifiers_with_pagination_args(
        httpx_mock: HTTPXMock, test_env, mcp):
    """limit and contiguous_id are forwarded as query params."""
    httpx_mock.add_response(json={"classifiers": [], "contiguous_id": None})
    fn = await get_tool(mcp, "get_collection_classifiers")
    result = await fn(collection_name="C", limit=25, contiguous_id="abc")
    assert result["success"] is True
    url = str(httpx_mock.get_requests()[0].url)
    assert "limit=25" in url
    assert "contiguous_id=abc" in url


async def test_get_collection_classifiers_without_pagination_args(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Omitting both leaves the query string empty."""
    httpx_mock.add_response(json={"classifiers": []})
    fn = await get_tool(mcp, "get_collection_classifiers")
    result = await fn(collection_name="C")
    assert result["success"] is True
    assert not str(httpx_mock.get_requests()[0].url.params)


# ── ALTR-managed collection ─────────────────────────────────────────────


async def test_import_altr_managed_classifiers(
        httpx_mock: HTTPXMock, test_env, mcp):
    """import_altr_managed_classifiers POSTs and returns the result."""
    httpx_mock.add_response(json={"imported": 42})
    fn = await get_tool(mcp, "import_altr_managed_classifiers")
    result = await fn()
    assert result["success"] is True
    assert result["data"] == {"imported": 42}
    assert httpx_mock.get_requests()[0].method == "POST"


async def test_get_altr_managed_timestamp(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_altr_managed_timestamp returns the last-import timestamp."""
    httpx_mock.add_response(json={"timestamp": "2026-08-03T00:00:00Z"})
    fn = await get_tool(mcp, "get_altr_managed_timestamp")
    result = await fn()
    assert result["success"] is True
    assert result["data"]["timestamp"] == "2026-08-03T00:00:00Z"


async def test_list_altr_managed_classifiers_with_pagination_args(
        httpx_mock: HTTPXMock, test_env, mcp):
    """limit and contiguous_id are forwarded."""
    httpx_mock.add_response(json={"classifiers": []})
    fn = await get_tool(mcp, "list_altr_managed_classifiers")
    result = await fn(limit=10, contiguous_id="tok")
    assert result["success"] is True
    url = str(httpx_mock.get_requests()[0].url)
    assert "limit=10" in url and "contiguous_id=tok" in url


async def test_list_altr_managed_classifiers_without_args(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Both arguments are optional."""
    httpx_mock.add_response(json={"classifiers": []})
    fn = await get_tool(mcp, "list_altr_managed_classifiers")
    result = await fn()
    assert result["success"] is True
    assert not str(httpx_mock.get_requests()[0].url.params)


# ── jobs ────────────────────────────────────────────────────────────────


async def test_get_active_jobs_with_every_filter(
        httpx_mock: HTTPXMock, test_env, mcp):
    """All four optional filters reach the query string."""
    httpx_mock.add_response(json={"jobs": []})
    fn = await get_tool(mcp, "get_active_jobs")
    result = await fn(
        limit=5, contiguous_id="tok", database_id=2167, agent_id="agent-1")
    assert result["success"] is True
    url = str(httpx_mock.get_requests()[0].url)
    for expected in ("limit=5", "contiguous_id=tok",
                     "database_id=2167", "agent_id=agent-1"):
        assert expected in url


async def test_get_active_jobs_without_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Every filter is optional."""
    httpx_mock.add_response(json={"jobs": []})
    fn = await get_tool(mcp, "get_active_jobs")
    result = await fn()
    assert result["success"] is True
    assert not str(httpx_mock.get_requests()[0].url.params)


async def test_get_job_happy_path(httpx_mock: HTTPXMock, test_env, mcp):
    """get_job fetches one job by id."""
    httpx_mock.add_response(json={"job_id": "j-1", "status": "COMPLETED"})
    fn = await get_tool(mcp, "get_job")
    result = await fn(job_id="j-1")
    assert result["success"] is True
    assert result["data"]["status"] == "COMPLETED"


async def test_get_job_summary_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """get_job_summary hits the /summary sub-resource."""
    httpx_mock.add_response(json={"total_columns": 10})
    fn = await get_tool(mcp, "get_job_summary")
    result = await fn(job_id="j-1")
    assert result["success"] is True
    assert "summary" in str(httpx_mock.get_requests()[0].url)


# ── findings ────────────────────────────────────────────────────────────


async def test_get_job_findings_with_every_filter(
        httpx_mock: HTTPXMock, test_env, mcp):
    """All optional filters are forwarded, including a bool and a list."""
    httpx_mock.add_response(json={"databases": []})
    fn = await get_tool(mcp, "get_job_findings")
    result = await fn(
        job_id="j-1",
        limit=50,
        page_token="pt",
        classifier_name=["SSN", "EMAIL"],
        confirmed_status="pending",
        include_column_status_counts=True,
    )
    assert result["success"] is True
    url = str(httpx_mock.get_requests()[0].url)
    assert "classifier_name=SSN" in url and "classifier_name=EMAIL" in url
    assert "confirmed_status=pending" in url


async def test_get_job_findings_wraps_a_single_classifier_in_a_list(
        httpx_mock: HTTPXMock, test_env, mcp):
    """A bare string classifier_name is normalised to a one-item list."""
    httpx_mock.add_response(json={"databases": []})
    fn = await get_tool(mcp, "get_job_findings")
    result = await fn(job_id="j-1", classifier_name="SSN")
    assert result["success"] is True
    assert httpx_mock.get_requests()[0].url.params.get_list(
        "classifier_name") == ["SSN"]


async def test_get_job_findings_include_counts_false_is_still_sent(
        httpx_mock: HTTPXMock, test_env, mcp):
    """include_column_status_counts=False is a value, not an omission."""
    httpx_mock.add_response(json={"databases": []})
    fn = await get_tool(mcp, "get_job_findings")
    await fn(job_id="j-1", include_column_status_counts=False)
    url = str(httpx_mock.get_requests()[0].url)
    assert "include_column_status_counts=false" in url.lower()


async def test_get_job_findings_without_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    """job_id alone is enough."""
    httpx_mock.add_response(json={"databases": []})
    fn = await get_tool(mcp, "get_job_findings")
    result = await fn(job_id="j-1")
    assert result["success"] is True
    assert not str(httpx_mock.get_requests()[0].url.params)


async def test_get_job_findings_schemas(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Drill-down to schemas, with filters."""
    httpx_mock.add_response(json={"schemas": []})
    fn = await get_tool(mcp, "get_job_findings_schemas")
    result = await fn(
        job_id="j-1", database="DB", limit=10, page_token="pt",
        classifier_name="SSN", confirmed_status="approved")
    assert result["success"] is True
    assert "/databases/DB/schemas" in str(httpx_mock.get_requests()[0].url)


async def test_get_job_findings_schemas_minimal(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Only job_id and database are required."""
    httpx_mock.add_response(json={"schemas": []})
    fn = await get_tool(mcp, "get_job_findings_schemas")
    result = await fn(job_id="j-1", database="DB")
    assert result["success"] is True
    url = httpx_mock.get_requests()[0].url
    assert url.path.endswith("/databases/DB/schemas")
    assert not str(url.params)


async def test_get_job_findings_tables(httpx_mock: HTTPXMock, test_env, mcp):
    """Drill-down to tables, with filters."""
    httpx_mock.add_response(json={"tables": []})
    fn = await get_tool(mcp, "get_job_findings_tables")
    result = await fn(
        job_id="j-1", database="DB", schema="SCH", limit=10,
        page_token="pt", classifier_name=["SSN"],
        confirmed_status="rejected")
    assert result["success"] is True
    assert "/schemas/SCH/tables" in str(httpx_mock.get_requests()[0].url)


async def test_get_job_findings_tables_minimal(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Filters are optional at the tables level too."""
    httpx_mock.add_response(json={"tables": []})
    fn = await get_tool(mcp, "get_job_findings_tables")
    result = await fn(job_id="j-1", database="DB", schema="SCH")
    assert result["success"] is True
    url = httpx_mock.get_requests()[0].url
    assert url.path.endswith("/schemas/SCH/tables")
    assert not str(url.params)


async def test_get_job_findings_columns(httpx_mock: HTTPXMock, test_env, mcp):
    """Drill-down to columns, with filters."""
    httpx_mock.add_response(json={"columns": []})
    fn = await get_tool(mcp, "get_job_findings_columns")
    result = await fn(
        job_id="j-1", database="DB", schema="SCH", table="TBL",
        limit=10, page_token="pt", classifier_name="SSN",
        confirmed_status="pending")
    assert result["success"] is True
    assert "/tables/TBL/columns" in str(httpx_mock.get_requests()[0].url)


async def test_get_job_findings_columns_minimal(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Filters are optional at the columns level too."""
    httpx_mock.add_response(json={"columns": []})
    fn = await get_tool(mcp, "get_job_findings_columns")
    result = await fn(
        job_id="j-1", database="DB", schema="SCH", table="TBL")
    assert result["success"] is True
    url = httpx_mock.get_requests()[0].url
    assert url.path.endswith("/tables/TBL/columns")
    assert not str(url.params)


async def test_get_job_findings_classifiers(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Drill-down to the classifiers detected on one column."""
    httpx_mock.add_response(json={"classifiers": []})
    fn = await get_tool(mcp, "get_job_findings_classifiers")
    result = await fn(
        job_id="j-1", database="DB", schema="SCH", table="TBL",
        column="COL", limit=10, page_token="pt",
        confirmed_status="approved")
    assert result["success"] is True
    assert "/columns/COL/classifiers" in str(httpx_mock.get_requests()[0].url)


async def test_get_job_findings_classifiers_minimal(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Pagination and status filters are optional."""
    httpx_mock.add_response(json={"classifiers": []})
    fn = await get_tool(mcp, "get_job_findings_classifiers")
    result = await fn(
        job_id="j-1", database="DB", schema="SCH", table="TBL",
        column="COL")
    assert result["success"] is True
    url = httpx_mock.get_requests()[0].url
    assert url.path.endswith("/columns/COL/classifiers")
    assert not str(url.params)


async def test_get_job_findings_lineage(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Lineage takes the full path plus a classifier; all are required."""
    httpx_mock.add_response(json={"conditions": []})
    fn = await get_tool(mcp, "get_job_findings_lineage")
    result = await fn(
        job_id="j-1", database="DB", schema="SCH", table="TBL",
        column="COL", classifier_name="SSN")
    assert result["success"] is True
    assert httpx_mock.get_requests()[0].url.path.endswith(
        "/columns/COL/classifiers/SSN/lineage")


# ── job decisions ───────────────────────────────────────────────────────


async def test_record_job_decision_at_full_scope(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Every scope field provided lands in the POST body."""
    httpx_mock.add_response(json={"recorded": 1})
    fn = await get_tool(mcp, "record_job_decision")
    result = await fn(
        job_id="j-1", confirmed_status="approved", database="DB",
        schema="SCH", table="TBL", column="COL", classifier_name="SSN")
    assert result["success"] is True
    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    body = json.loads(request.content)
    assert body == {
        "confirmed_status": "approved",
        "database": "DB",
        "schema": "SCH",
        "table": "TBL",
        "column": "COL",
        "classifier_name": "SSN",
    }


async def test_record_job_decision_job_wide(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Omitting every scope field records a job-wide decision."""
    httpx_mock.add_response(json={"recorded": 99})
    fn = await get_tool(mcp, "record_job_decision")
    result = await fn(job_id="j-1", confirmed_status="rejected")
    assert result["success"] is True
    assert json.loads(httpx_mock.get_requests()[0].content) == {
        "confirmed_status": "rejected"}


async def test_get_job_decisions_with_every_filter(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Scope and pagination filters are forwarded as query params."""
    httpx_mock.add_response(json={"decisions": []})
    fn = await get_tool(mcp, "get_job_decisions")
    result = await fn(
        job_id="j-1", database="DB", schema="SCH", table="TBL",
        column="COL", limit=20, page_token="pt")
    assert result["success"] is True
    url = str(httpx_mock.get_requests()[0].url)
    for expected in ("database=DB", "schema=SCH", "table=TBL",
                     "column=COL", "limit=20", "page_token=pt"):
        assert expected in url


async def test_get_job_decisions_without_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    """job_id alone returns every decision on the job."""
    httpx_mock.add_response(json={"decisions": []})
    fn = await get_tool(mcp, "get_job_decisions")
    result = await fn(job_id="j-1")
    assert result["success"] is True
    assert not str(httpx_mock.get_requests()[0].url.params)


async def test_revoke_job_decisions_at_full_scope(
        httpx_mock: HTTPXMock, test_env, mcp):
    """revoke_job_decisions DELETEs with every scope field as a param."""
    httpx_mock.add_response(json={"revoked": 1})
    fn = await get_tool(mcp, "revoke_job_decisions")
    result = await fn(
        job_id="j-1", database="DB", schema="SCH", table="TBL",
        column="COL", classifier_name="SSN")
    assert result["success"] is True
    request = httpx_mock.get_requests()[0]
    assert request.method == "DELETE"
    url = str(request.url)
    for expected in ("database=DB", "schema=SCH", "table=TBL",
                     "column=COL", "classifier_name=SSN"):
        assert expected in url


async def test_revoke_job_decisions_job_wide(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Omitting every scope field revokes across the whole job."""
    httpx_mock.add_response(json={"revoked": 99})
    fn = await get_tool(mcp, "revoke_job_decisions")
    result = await fn(job_id="j-1")
    assert result["success"] is True
    assert not str(httpx_mock.get_requests()[0].url.params)


async def test_get_job_review_status(httpx_mock: HTTPXMock, test_env, mcp):
    """get_job_review_status hits the /review-status sub-resource."""
    httpx_mock.add_response(json={
        "total": 10, "approved": 4, "rejected": 1, "pending": 5})
    fn = await get_tool(mcp, "get_job_review_status")
    result = await fn(job_id="j-1")
    assert result["success"] is True
    assert result["data"]["pending"] == 5
    assert "review-status" in str(httpx_mock.get_requests()[0].url)


async def test_report_creation_failure_passes_the_cause_through(
        httpx_mock: HTTPXMock, test_env, mcp):
    """A failed report *creation* keeps its own error shape.

    get_job_report reads ["url"] off the creation response. When creation
    failed -- bad job id, 4xx, retries exhausted -- api.request has already
    returned {success: False, ...} with no "url", so indexing it raised
    KeyError: 'url' and discarded the real cause.
    """
    httpx_mock.add_response(status_code=404, json={"message": "not found"})

    fn = await get_tool(mcp, "get_classification_report")
    result = await fn(job_id="nope")
    inner = result["data"]
    assert inner["success"] is False
    assert inner["status_code"] == 404
    # Only the creation call was made; no download was attempted.
    assert len(httpx_mock.get_requests()) == 1


OLTP_ARGS = {"agent_id": "a", "repo_name": "r", "service_user_name": "s",
             "collection_name": "C"}


async def test_create_oltp_job_sends_no_sampling_for_a_metadata_scan(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=201, json={"job_id": "j1"})
    fn = await get_tool(mcp, "create_oltp_job")
    await fn(**OLTP_ARGS, sample_strategy="METADATA", sample_size=500)
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert body["sample_strategy"] == "METADATA"
    assert "sample_size" not in body and "sample_type" not in body


async def test_create_oltp_job_sends_percent_sampling(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=201, json={"job_id": "j1"})
    fn = await get_tool(mcp, "create_oltp_job")
    await fn(**OLTP_ARGS, sample_strategy="COMBINED",
             sample_type="PERCENT", sample_size=10)
    body = json.loads(httpx_mock.get_requests()[0].content)
    assert (body["sample_strategy"], body["sample_size"],
            body["sample_type"]) == ("COMBINED", 10, "PERCENT")


async def test_create_oltp_job_needs_a_size_for_percent_sampling(
        httpx_mock: HTTPXMock, test_env, mcp):
    fn = await get_tool(mcp, "create_oltp_job")
    with pytest.raises(Exception, match="required when sample_type is PERCENT"):
        await fn(**OLTP_ARGS, sample_type="PERCENT")


# ── review-gated jobs ───────────────────────────────────────────────────


@pytest.mark.parametrize("tool,args,path", [
    ("create_job", {"job_type": "FULL", "database_id": 1,
                    "collection_name": "C"}, "/jobs/snowflake"),
    ("create_gdlp_job", {"database_id": 1}, "/jobs/snowflake"),
    ("create_databricks_job", {"database_id": 1}, "/jobs/databricks"),
    ("create_oltp_job", {"agent_id": "a", "repo_name": "r",
                         "service_user_name": "s", "collection_name": "C"},
     "/jobs/oltp"),
])
async def test_job_creators_forward_requires_review(
        httpx_mock: HTTPXMock, test_env, mcp, tool, args, path):
    """requires_review reaches the body when set, and is omitted otherwise."""
    httpx_mock.add_response(status_code=201, json={"job_id": "j1"})
    httpx_mock.add_response(status_code=201, json={"job_id": "j2"})
    fn = await get_tool(mcp, tool)

    assert (await fn(**args, requires_review=True))["success"] is True
    assert (await fn(**args))["success"] is True

    gated, default = httpx_mock.get_requests()
    assert path in str(gated.url)
    assert json.loads(gated.content)["requires_review"] is True
    assert "requires_review" not in json.loads(default.content)


@pytest.mark.parametrize("confidence,expected", [
    (["HIGH", "MEDIUM"], ["HIGH", "MEDIUM"]), ("LOW", ["LOW"])])
async def test_get_job_findings_leaves_forwards_filters(
        httpx_mock: HTTPXMock, test_env, mcp, confidence, expected):
    """Pagination and confidence tiers become query params, tiers repeated."""
    httpx_mock.add_response(json={"items": [], "next_page_token": None})
    fn = await get_tool(mcp, "get_job_findings_leaves")
    result = await fn(job_id="j-1", limit=500, page_token="pt",
                      confidence=confidence)
    assert result["success"] is True
    request = httpx_mock.get_requests()[0]
    assert request.method == "GET"
    assert request.url.path.endswith("/v1/jobs/j-1/findings/leaves")
    assert request.url.params.get_list("confidence") == expected
    assert request.url.params["limit"] == "500"
    assert request.url.params["page_token"] == "pt"


async def test_record_bulk_job_decision_sends_the_predicate(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Every filter lands in the predicate; dry_run is sent explicitly."""
    httpx_mock.add_response(json={"bulk_decision_id": "b-1",
                                  "matched_findings": 12})
    fn = await get_tool(mcp, "record_bulk_job_decision")
    result = await fn(
        job_id="j-1", confirmed_status="approved",
        classifier_names=["pii_ssn"], confidence=["HIGH"],
        database="DB", schema="SCH", table="TBL", dry_run=True)
    assert result["data"]["bulk_decision_id"] == "b-1"
    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.url.path.endswith("/v1/jobs/j-1/decisions/bulk")
    assert json.loads(request.content) == {
        "confirmed_status": "approved",
        "dry_run": True,
        "predicate": {"classifier_names": ["pii_ssn"], "confidence": ["HIGH"],
                      "database": "DB", "schema": "SCH", "table": "TBL"},
    }


async def test_record_bulk_job_decision_minimal(
        httpx_mock: HTTPXMock, test_env, mcp):
    """Only classifier_names is required; dry_run defaults to false."""
    httpx_mock.add_response(json={"bulk_decision_id": "b-2"})
    fn = await get_tool(mcp, "record_bulk_job_decision")
    await fn(job_id="j-1", confirmed_status="rejected",
             classifier_names=["pii_email"])
    assert json.loads(httpx_mock.get_requests()[0].content) == {
        "confirmed_status": "rejected",
        "dry_run": False,
        "predicate": {"classifier_names": ["pii_email"]},
    }


async def test_revoke_bulk_job_decision_encodes_both_ids(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"revoked": 12})
    fn = await get_tool(mcp, "revoke_bulk_job_decision")
    result = await fn(job_id="j/1", bulk_decision_id="b/1")
    assert result["success"] is True
    request = httpx_mock.get_requests()[0]
    assert request.method == "DELETE"
    assert request.url.raw_path.decode().endswith(
        "/v1/jobs/j%2F1/decisions/bulk/b%2F1")


@pytest.mark.parametrize("tool,action", [
    ("confirm_job_report", "confirm"), ("cancel_job_report", "cancel")])
async def test_report_review_actions_post_without_a_body(
        httpx_mock: HTTPXMock, test_env, mcp, tool, action):
    httpx_mock.add_response(status_code=202, json={"status": "ok"})
    fn = await get_tool(mcp, tool)
    result = await fn(job_id="j-1")
    assert result["success"] is True
    request = httpx_mock.get_requests()[0]
    assert request.method == "POST"
    assert request.url.path.endswith(f"/v1/jobs/j-1/report/{action}")
    assert request.content == b""


async def test_record_bulk_job_decision_refuses_an_empty_classifier_list(
        httpx_mock: HTTPXMock, test_env, mcp):
    """The engine reads [] as every classifier, so nothing is sent."""
    fn = await get_tool(mcp, "record_bulk_job_decision")
    with pytest.raises(Exception, match="at least one classifier"):
        await fn(job_id="j-1", confirmed_status="approved", classifier_names=[])
    assert not httpx_mock.get_requests()


# ── classifier tags, collection membership, managed collections ─────────


async def test_create_classifier_sends_tags_as_attributes(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=201, json={"classifier_name": "C"})
    fn = await get_tool(mcp, "create_classifier")
    await fn(classifier_name="C", compound_ruleset={"operator": "AND",
             "conditions": []}, tags=["type:ssn"])
    body = json.loads(httpx_mock.get_request().content)
    assert body["attributes"] == {"tags": ["type:ssn"]}


async def test_update_classifier_clears_tags_with_an_empty_list(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"classifier_name": "C"})
    fn = await get_tool(mcp, "update_classifier")
    await fn(classifier_name="C", tags=[])
    assert json.loads(httpx_mock.get_request().content) == {
        "attributes": {"tags": []}}


@pytest.mark.parametrize("tool,action", [
    ("add_classifier_to_collections", "append"),
    ("remove_classifier_from_collections", "remove")])
async def test_classifier_collection_membership_uses_the_classifier_route(
        httpx_mock: HTTPXMock, test_env, mcp, tool, action):
    httpx_mock.add_response(json={"success": True})
    fn = await get_tool(mcp, tool)
    await fn(classifier_name="pii/ssn", collection_names="C1")
    request = httpx_mock.get_request()
    assert request.method == "PATCH"
    assert request.url.raw_path.decode().endswith(
        f"/v1/classifiers/pii%2Fssn/collections/{action}")
    assert json.loads(request.content) == {"collection_names": ["C1"]}


async def test_list_classifier_tags_forwards_only_given_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"tags": [], "keys": []})
    fn = await get_tool(mcp, "list_classifier_tags")
    await fn(key="type", limit=10)
    request = httpx_mock.get_request()
    assert request.url.path.endswith("/v1/tags")
    assert dict(request.url.params) == {"key": "type", "limit": "10"}


@pytest.mark.parametrize("tool,collection,path", [
    ("import_altr_managed_classifiers", None,
     "/collections/altr-managed/import"),
    ("import_altr_managed_classifiers", "gdlp",
     "/collections/altr-managed/gdlp/import"),
    ("import_altr_managed_classifiers", "all",
     "/collections/altr-managed/import-all"),
    ("get_altr_managed_timestamp", None,
     "/collections/altr-managed/timestamp"),
    ("get_altr_managed_timestamp", "stoplight",
     "/collections/altr-managed/stoplight/timestamp"),
    ("get_altr_managed_timestamp", "all",
     "/collections/altr-managed/timestamps"),
    ("list_altr_managed_classifiers", None,
     "/collections/altr-managed/classifiers"),
    ("list_altr_managed_classifiers", "aws-comprehend",
     "/collections/altr-managed/aws-comprehend/classifiers"),
])
async def test_altr_managed_tools_address_a_collection_by_slug(
        httpx_mock: HTTPXMock, test_env, mcp, tool, collection, path):
    """Without a slug the original regex-collection paths are kept."""
    httpx_mock.add_response(json={"success": True})
    fn = await get_tool(mcp, tool)
    args = {} if collection is None else {"collection": collection}
    assert (await fn(**args))["success"] is True
    assert httpx_mock.get_request().url.path.endswith(path)


# ── report groups and exclusions ────────────────────────────────────────


async def test_list_report_groups_repeats_list_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"groups": []})
    fn = await get_tool(mcp, "list_report_groups")
    await fn(status=["confirmed", "needs_review"], connection_type=["mysql"])
    request = httpx_mock.get_request()
    assert request.url.path.endswith("/v1/jobs/groups")
    assert request.url.params.get_list("status") == [
        "confirmed", "needs_review"]
    assert request.url.params.get_list("connection_type") == ["mysql"]


async def test_list_report_group_runs_encodes_the_group_id(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"runs": []})
    fn = await get_tool(mcp, "list_report_group_runs")
    await fn(group_id="g/1", limit=5)
    request = httpx_mock.get_request()
    assert request.url.raw_path.decode().startswith(
        "/v1/jobs/groups/g%2F1/runs")
    assert request.url.params["limit"] == "5"


async def test_get_job_exclusions(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"applied": [], "unmatched": ["DB.X"]})
    fn = await get_tool(mcp, "get_job_exclusions")
    result = await fn(job_id="j-1")
    assert result["data"]["unmatched"] == ["DB.X"]
    assert httpx_mock.get_request().url.path.endswith(
        "/v1/jobs/j-1/exclusions")


# ── scan objects ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("args,path,extra", [
    ({"collection_name": "C 1"}, "/v1/collections/C%201/scan-objects", {}),
    ({"collection_name": "C", "classifier_name": "pii/ssn",
      "classifier": {"minimum_threshold": 50}},
     "/v1/collections/C/classifiers/pii%2Fssn/scan-objects",
     {"draft": {"minimum_threshold": 50}}),
    ({"classifier": {"classifier_name": "x", "pattern": "a+"}},
     "/v1/scan-objects",
     {"classifier": {"classifier_name": "x", "pattern": "a+"}}),
])
async def test_scan_object_routes_by_target_and_encodes_text(
        httpx_mock: HTTPXMock, test_env, mcp, args, path, extra):
    httpx_mock.add_response(json={"request_id": "r-1", "status": "COMPLETED"})
    fn = await get_tool(mcp, "scan_object")
    result = await fn(content="ssn,123-45-6789", file_name="a.csv", **args)
    assert result["data"]["request_id"] == "r-1"
    request = httpx_mock.get_request()
    assert request.method == "POST"
    assert request.url.raw_path.decode() == path
    assert json.loads(request.content) == {
        "content": "c3NuLDEyMy00NS02Nzg5", "file_name": "a.csv", **extra}


async def test_scan_object_accepts_exactly_the_limit(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"request_id": "r-1"})
    fn = await get_tool(mcp, "scan_object")
    await fn(content="x" * (128 * 1024), collection_name="C")
    assert len(httpx_mock.get_requests()) == 1


async def test_scan_object_accepts_wrapped_base64(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"request_id": "r-1"})
    fn = await get_tool(mcp, "scan_object")
    await fn(content_base64="YWJj\r\nZGVm", collection_name="C")
    assert json.loads(httpx_mock.get_request().content)["content"] == "YWJjZGVm"


async def test_list_altr_managed_classifiers_refuses_all(test_env, mcp):
    fn = await get_tool(mcp, "list_altr_managed_classifiers")
    with pytest.raises(Exception, match="one collection slug"):
        await fn(collection="all")


async def test_list_report_groups_wraps_single_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"groups": []})
    fn = await get_tool(mcp, "list_report_groups")
    await fn(status="confirmed", connection_type="mysql")
    params = httpx_mock.get_request().url.params
    assert params.get_list("status") == ["confirmed"]
    assert params.get_list("connection_type") == ["mysql"]


async def test_scan_object_passes_base64_through(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"request_id": "r-1"})
    fn = await get_tool(mcp, "scan_object")
    await fn(content_base64="AAEC", collection_name="C",
             include_lineage=True)
    assert json.loads(httpx_mock.get_request().content) == {
        "content": "AAEC", "include_lineage": True}


@pytest.mark.parametrize("args,message", [
    ({"collection_name": "C"}, "exactly one of content"),
    ({"content": "x", "content_base64": "eA==", "collection_name": "C"},
     "exactly one of content"),
    ({"content": "x"}, "Pass collection_name"),
    ({"content": "x", "classifier_name": "A"}, "needs the collection_name"),
    ({"content": "x", "collection_name": "C", "classifier": {}},
     "needs classifier_name"),
    ({"content_base64": "not base64!", "collection_name": "C"},
     "not valid base64"),
    ({"content": "x" * (128 * 1024 + 1), "collection_name": "C"},
     "scan limit is 131072 bytes"),
    ({"content_base64": base64.b64encode(b"x" * (128 * 1024 + 1)).decode(),
      "collection_name": "C"}, "scan limit is 131072 bytes"),
])
async def test_scan_object_refuses_bad_input_before_sending(
        httpx_mock: HTTPXMock, test_env, mcp, args, message):
    fn = await get_tool(mcp, "scan_object")
    with pytest.raises(Exception, match=message):
        await fn(**args)
    assert httpx_mock.get_requests() == []


@pytest.mark.parametrize("tool,args,path", [
    ("get_scan_object", {"request_id": "r/1"}, "/v1/scan-objects/r%2F1"),
    ("get_scan_object_map", {"request_id": "r-1"},
     "/v1/scan-objects/r-1/map"),
    ("get_scan_object_supported_types", {},
     "/v1/scan-objects/supported-types"),
])
async def test_scan_object_reads(
        httpx_mock: HTTPXMock, test_env, mcp, tool, args, path):
    httpx_mock.add_response(json={"success": True})
    fn = await get_tool(mcp, tool)
    assert (await fn(**args))["success"] is True
    request = httpx_mock.get_request()
    assert request.method == "GET"
    assert request.url.raw_path.decode() == path


async def test_list_scan_objects_forwards_only_given_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"scans": []})
    fn = await get_tool(mcp, "list_scan_objects")
    await fn(status="FAILED", order="asc")
    request = httpx_mock.get_request()
    assert request.url.path.endswith("/v1/scan-objects")
    assert dict(request.url.params) == {"status": "FAILED", "order": "asc"}


# ── job scope, exclusions and sampling ──────────────────────────────────

SCOPE = {"level": "SCHEMA", "database": "SALES", "schema": "PUBLIC"}
EXCLUDE = {"level": "TABLE", "database": "SALES", "schema": "PUBLIC",
           "table": "TEST_DATA"}


@pytest.mark.parametrize("tool,args", [
    ("create_job", {"job_type": "FULL", "database_id": 1,
                    "collection_name": "C"}),
    ("create_gdlp_job", {"database_id": 1}),
    ("create_databricks_job", {"database_id": 1}),
    ("create_oltp_job", {"agent_id": "a", "repo_name": "r",
                         "service_user_name": "s", "collection_name": "C"}),
])
async def test_job_creators_send_scope_and_exclusions(
        httpx_mock: HTTPXMock, test_env, mcp, tool, args):
    """A single exclusion is sent as a list; neither key is sent when unset."""
    httpx_mock.add_response(status_code=201, json={"job_id": "j1"},
                            is_reusable=True)
    fn = await get_tool(mcp, tool)
    await fn(**args, scope=SCOPE, exclusions=EXCLUDE)
    await fn(**args)
    scoped, plain = (json.loads(r.content) for r in httpx_mock.get_requests())
    assert scoped["scope"] == SCOPE and scoped["exclusions"] == [EXCLUDE]
    assert "scope" not in plain and "exclusions" not in plain


@pytest.mark.parametrize("scope,exclusions", [
    ({"database": "SALES"}, None),
    (None, [{"level": "COLUMN", "database": "SALES"}]),
    (None, ["SALES.PUBLIC"]),
])
async def test_job_creators_refuse_a_malformed_scope(
        httpx_mock: HTTPXMock, test_env, mcp, scope, exclusions):
    fn = await get_tool(mcp, "create_databricks_job")
    with pytest.raises(Exception, match="set to one of DATABASE, SCHEMA, TABLE\\."):
        await fn(database_id=1, scope=scope, exclusions=exclusions)
    assert httpx_mock.get_requests() == []


async def test_create_job_sends_sampling(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=201, json={"job_id": "j1"},
                            is_reusable=True)
    fn = await get_tool(mcp, "create_job")
    args = {"job_type": "FULL", "database_id": 1, "collection_name": "C"}
    await fn(**args, sample_strategy="COMBINED", sample_size=10,
             sample_type="PERCENT")
    await fn(**args, sample_strategy="METADATA", sample_size=500)
    combined, metadata = (json.loads(r.content)
                          for r in httpx_mock.get_requests())
    assert (combined["sample_strategy"], combined["sample_size"],
            combined["sample_type"]) == ("COMBINED", 10, "PERCENT")
    assert metadata["sample_strategy"] == "METADATA"
    assert "sample_size" not in metadata and "sample_type" not in metadata


@pytest.mark.parametrize("tool,args", [
    ("create_job", {"job_type": "FULL", "database_id": 1,
                    "collection_name": "C", "sample_type": "PERCENT"}),
    ("create_gdlp_job", {"database_id": 1, "sample_type": "PERCENT"}),
])
async def test_percent_sampling_needs_a_size(
        httpx_mock: HTTPXMock, test_env, mcp, tool, args):
    fn = await get_tool(mcp, tool)
    with pytest.raises(Exception, match="required when sample_type is PERCENT"):
        await fn(**args)
    assert httpx_mock.get_requests() == []


async def test_create_gdlp_job_sends_job_type_and_refuses_metadata(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=201, json={"job_id": "j1"})
    fn = await get_tool(mcp, "create_gdlp_job")
    await fn(database_id=1, job_type="INCREMENTAL", sample_strategy="COMBINED")
    body = json.loads(httpx_mock.get_request().content)
    assert (body["job_type"], body["sample_strategy"]) == (
        "INCREMENTAL", "COMBINED")
    with pytest.raises(Exception, match="only for ALTR-native jobs"):
        await fn(database_id=1, sample_strategy="METADATA")


async def test_create_oltp_job_sends_file_options_and_metadata_map(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(status_code=201, json={"job_id": "j1"})
    fn = await get_tool(mcp, "create_oltp_job")
    await fn(agent_id="a", repo_name="r", service_user_name="s",
             collection_name="C", file_options={"include_glob": "*.csv"},
             metadata_map={"default": "hashed"},
             scope={"level": "PATH", "paths": ["finance"]})
    body = json.loads(httpx_mock.get_request().content)
    assert body["file_options"] == {"include_glob": "*.csv"}
    assert body["metadata_map"] == {"default": "hashed"}
    assert body["scope"] == {"level": "PATH", "paths": ["finance"]}


@pytest.mark.parametrize("tool,args", [
    ("create_job", {"job_type": "FULL", "database_id": 1,
                    "collection_name": "C"}),
    ("create_gdlp_job", {"database_id": 1}),
    ("create_databricks_job", {"database_id": 1}),
])
async def test_only_oltp_jobs_take_a_path_scope(
        httpx_mock: HTTPXMock, test_env, mcp, tool, args):
    fn = await get_tool(mcp, tool)
    with pytest.raises(Exception, match="one of DATABASE, SCHEMA, TABLE\\."):
        await fn(**args, scope={"level": "PATH", "paths": ["finance"]})
    assert httpx_mock.get_requests() == []


async def test_create_oltp_job_refuses_a_malformed_exclusion(
        httpx_mock: HTTPXMock, test_env, mcp):
    fn = await get_tool(mcp, "create_oltp_job")
    with pytest.raises(Exception,
                       match="one of DATABASE, SCHEMA, TABLE, PATH\\."):
        await fn(**OLTP_ARGS, exclusions=[{"level": "COLUMN"}])
    assert httpx_mock.get_requests() == []


# ── list filters and sort options ───────────────────────────────────────


@pytest.mark.parametrize("tool,args,expected", [
    ("get_classifiers",
     {"prefix": "email", "order_by": "name", "sort_order": "desc",
      "exclude_collection": "C"},
     {"prefix": "email", "order_by": "name", "sort_order": "desc",
      "exclude_collection": "C"}),
    ("get_collections", {"sort_order": "asc"}, {"sort_order": "asc"}),
    ("get_collection_classifiers",
     {"collection_name": "C", "prefix": "pii", "sort_order": "asc"},
     {"prefix": "pii", "sort_order": "asc"}),
    ("get_active_jobs",
     {"status": "AWAITING_REVIEW", "job_type": "FULL",
      "classification_type": 5, "order": "asc"},
     {"status": "AWAITING_REVIEW", "job_type": "FULL",
      "classification_type": "5", "order": "asc"}),
])
async def test_list_tools_forward_filters(
        httpx_mock: HTTPXMock, test_env, mcp, tool, args, expected):
    httpx_mock.add_response(json={"success": True, "data": {}})
    fn = await get_tool(mcp, tool)
    await fn(**args)
    params = dict(httpx_mock.get_request().url.params)
    assert {k: params[k] for k in expected} == expected


@pytest.mark.parametrize("tool,args", [
    ("get_job_findings", {}),
    ("get_job_findings_schemas", {"database": "D"}),
    ("get_job_findings_tables", {"database": "D", "schema": "S"}),
    ("get_job_findings_columns", {"database": "D", "schema": "S",
                                  "table": "T"}),
    ("get_job_findings_classifiers", {"database": "D", "schema": "S",
                                      "table": "T", "column": "C",
                                      "classifier_name": "pii_ssn"}),
])
@pytest.mark.parametrize("confidence,expected", [
    (["HIGH", "MEDIUM"], ["HIGH", "MEDIUM"]), ("LOW", ["LOW"])])
async def test_findings_tools_repeat_list_filters(
        httpx_mock: HTTPXMock, test_env, mcp, tool, args, confidence, expected):
    httpx_mock.add_response(json={"items": []})
    fn = await get_tool(mcp, tool)
    await fn(job_id="j-1", confidence=confidence,
             confirmed_status=["approved", "pending"], **args)
    params = httpx_mock.get_request().url.params
    assert params.get_list("confidence") == expected
    assert params.get_list("confirmed_status") == ["approved", "pending"]
    if "classifier_name" in args:
        assert params.get_list("classifier_name") == ["pii_ssn"]


async def test_get_classifiers_keeps_filters_on_every_page(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={
        "classifiers": [{"classifier_name": "a"}], "contiguous_id": "p2"})
    httpx_mock.add_response(json={"classifiers": [{"classifier_name": "b"}]})
    fn = await get_tool(mcp, "get_classifiers")
    result = await fn(prefix="email", exclude_collection="C")
    first, second = httpx_mock.get_requests()
    assert "contiguous_id" not in first.url.params
    assert second.url.params["contiguous_id"] == "p2"
    for request in (first, second):
        assert request.url.params["prefix"] == "email"
        assert request.url.params["exclude_collection"] == "C"
    names = [c["classifier_name"] for c in result["data"]["data"]["classifiers"]]
    assert names == ["a", "b"]


async def test_get_active_jobs_drops_empty_filters(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(json={"jobs": []})
    fn = await get_tool(mcp, "get_active_jobs")
    await fn(status="", order="", classification_type=5)
    assert dict(httpx_mock.get_request().url.params) == {
        "classification_type": "5"}


@pytest.mark.parametrize("tool,args", [
    ("get_classifiers", {"prefix": "", "order_by": "", "sort_order": "",
                         "exclude_collection": ""}),
    ("get_collections", {"sort_order": ""}),
    ("get_collection_classifiers", {"collection_name": "C", "prefix": "",
                                    "sort_order": ""}),
])
async def test_list_tools_drop_empty_filters(
        httpx_mock: HTTPXMock, test_env, mcp, tool, args):
    httpx_mock.add_response(json={"success": True, "data": {}})
    fn = await get_tool(mcp, tool)
    await fn(**args)
    params = httpx_mock.get_request().url.params
    assert not {k for k in args if k != "collection_name"} & set(params)
