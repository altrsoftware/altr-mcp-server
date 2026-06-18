"""Integration tests for classification tools (altr_mcp/tools/classification.py).

Tests each of the 11 classification tools using pytest-httpx to mock HTTP responses.
Verifies the {success, data, error} response shape for happy paths.
"""
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
            "pattern": r"\d{3}-\d{2}-\d{4}",
            "minimum_threshold": 80,
            "sample_size": 100,
            "sample_type": "ROWS",
            "collection_names": [],
            "collection_count": 0,
        },
    })
    fn = await get_tool(mcp, "create_classifier")
    result = await fn(
        classifier_name="MY_CLASSIFIER",
        description="Test classifier",
        minimum_threshold=80,
        pattern=r"\d{3}-\d{2}-\d{4}",
        sample_size=100,
    )
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result


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


# ── create_gdlp_job ──────────────────────────────────────────────────────

async def test_create_gdlp_job_happy_path(
        httpx_mock: HTTPXMock, test_env, mcp):
    """create_gdlp_job (Snowflake GDLP) posts only database_id and wraps the
    response."""
    httpx_mock.add_response(status_code=201, json={
        "job_id": "gdlp-job-uuid-1234",
        "database_id": 42,
        "status": "CREATED",
        "classification_type": 6,
    })
    fn = await get_tool(mcp, "create_gdlp_job")
    result = await fn(database_id=42)
    assert result["success"] is True
    assert result["error"] is None
    assert "data" in result
    import json as _json
    body = _json.loads(httpx_mock.get_request().content)
    assert body == {"database_id": 42}
    assert "/jobs/gdlp" in str(httpx_mock.get_request().url)


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
    import json as _json
    request = httpx_mock.get_request()
    assert "/jobs/oltp" in str(request.url)
    body = _json.loads(request.content)
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
    import json as _json
    body = _json.loads(httpx_mock.get_request().content)
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
    import json as _json
    body = _json.loads(httpx_mock.get_request().content)
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
