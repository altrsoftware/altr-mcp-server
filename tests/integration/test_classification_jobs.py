"""Job-creation tools send what the console's Classify Data wizard sends.

Each EXPECTED body has the shape of a request the console sent for the same
choices, captured from its network traffic, with neutral names and IDs.
"""
import json
import re

import pytest
from fastmcp import FastMCP
from pytest_httpx import HTTPXMock

from altr_mcp.tools.classification import register
from tests.integration.conftest import get_tool

CONDITIONS = ["ROW_DATA", "METADATA", "COLUMN_LOCATION", "GDLP", "CONTENT_TYPE",
              "DATA_LENGTH", "COLUMN_SIZE", "AMAZON_COMPREHEND", "ENTROPY"]
SNOWFLAKE_CONDITIONS = CONDITIONS + ["SNOWFLAKE_NATIVE"]
AGENT = "00000000-0000-4000-8000-000000000001"

DATABASES = re.compile(r".*/api/databases.*")
COLLECTION = re.compile(r".*/v1/collections/[^/]+$")
REPO = re.compile(r".*/v1/repos/[^/]+$")
JOB = re.compile(r".*/v1/jobs/(snowflake|databricks|oltp)$")


@pytest.fixture
def mcp():
    _mcp = FastMCP("test")
    register(_mcp)
    return _mcp


@pytest.fixture
def lookups(httpx_mock: HTTPXMock):
    """The data source list, a collection with classifiers, and a job id."""
    httpx_mock.add_response(url=DATABASES, is_optional=True, is_reusable=True, json={
        "success": True, "data": {"count": 2, "databases": [
            {"id": 11, "databaseName": "SALES", "friendlyDatabaseName": "Sales",
             "databaseType": "snowflake_external_functions"},
            {"id": 22, "databaseName": "workspace", "friendlyDatabaseName": "Lake",
             "databaseType": "databricks"}]}})
    httpx_mock.add_response(url=COLLECTION, is_optional=True, is_reusable=True,
                            json={"collection": {"collection_name": "PII",
                                                 "classifier_count": 4}})
    httpx_mock.add_response(url=JOB, method="POST", is_optional=True, is_reusable=True,
                            status_code=201, json={"job_id": "j-1"})


def _repo(httpx_mock, repo_type):
    httpx_mock.add_response(url=REPO, is_optional=True, is_reusable=True,
                            json={"name": "repo", "type": repo_type})


def _sent(httpx_mock):
    [job] = [r for r in httpx_mock.get_requests() if r.method == "POST"]
    return job.url.path, json.loads(job.content)


# ── Snowflake ────────────────────────────────────────────────────────────


async def test_snowflake_defaults_match_the_console(
        httpx_mock: HTTPXMock, test_env, mcp, lookups):
    """ALTR Hosted, the whole database, ROWS 1000, review on."""
    fn = await get_tool(mcp, "create_snowflake_job")
    await fn(database_id=11, collection_name="PII")
    assert _sent(httpx_mock) == ("/v1/jobs/snowflake", {
        "database_id": 11, "job_type": "FULL", "classification_type": "gdlp",
        "requires_review": True, "collection_name": "PII",
        "condition_types": SNOWFLAKE_CONDITIONS,
        "sample_size": 1000, "sample_type": "ROWS"})


async def test_snowflake_in_warehouse_scoped_matches_the_console(
        httpx_mock: HTTPXMock, test_env, mcp, lookups):
    """A schema scope uses the connection's database name; exclusions are relative."""
    fn = await get_tool(mcp, "create_snowflake_job")
    await fn(database_id=11, collection_name="PII", processing_location="in_warehouse",
             schema="CUSTOMER", exclude="EMPLOYEES", sample_type="PERCENT",
             requires_review=False)
    assert _sent(httpx_mock) == ("/v1/jobs/snowflake", {
        "database_id": 11, "job_type": "FULL", "classification_type": "altr_native",
        "requires_review": False, "collection_name": "PII",
        "condition_types": SNOWFLAKE_CONDITIONS,
        "sample_size": 5, "sample_type": "PERCENT",
        "scope": {"level": "SCHEMA", "database": "SALES", "schema": "CUSTOMER"},
        "exclusions": [{"level": "TABLE", "database": "SALES", "schema": "CUSTOMER",
                        "table": "EMPLOYEES"}]})


async def test_snowflake_exclusions_alone_scope_the_whole_database(
        httpx_mock: HTTPXMock, test_env, mcp, lookups):
    fn = await get_tool(mcp, "create_snowflake_job")
    await fn(database_id=11, collection_name="PII", exclude=["STAGE", "stage", "HR.PAY"])
    body = _sent(httpx_mock)[1]
    assert body["scope"] == {"level": "DATABASE", "database": "SALES"}
    assert body["exclusions"] == [
        {"level": "SCHEMA", "database": "SALES", "schema": "STAGE"},
        {"level": "TABLE", "database": "SALES", "schema": "HR", "table": "PAY"}]


@pytest.mark.parametrize("args,message", [
    ({"processing_location": "agent"}, "altr_hosted"),
    ({"table": "T"}, "table scope needs its schema"),
    ({"sample_type": "PERCENT", "sample_size": 101}, "between 1 and 100"),
    ({"sample_size": 0}, "greater than 0"),
    ({"schema": "S", "exclude": "T.X"}, "deeper than a table"),
    ({"schema": "S#1"}, "255 characters or fewer"),
    ({"schema": "S" * 256}, "255 characters or fewer"),
    ({"exclude": [f"S{i}" for i in range(101)]}, "At most 100"),
])
async def test_snowflake_refuses_what_the_console_refuses(
        httpx_mock: HTTPXMock, test_env, mcp, lookups, args, message):
    fn = await get_tool(mcp, "create_snowflake_job")
    with pytest.raises(Exception, match=message):
        await fn(database_id=11, collection_name="PII", **args)
    assert not [r for r in httpx_mock.get_requests() if r.method == "POST"]


async def test_snowflake_refuses_a_databricks_connection(
        httpx_mock: HTTPXMock, test_env, mcp, lookups):
    fn = await get_tool(mcp, "create_snowflake_job")
    with pytest.raises(Exception, match="databricks connection"):
        await fn(database_id=22, collection_name="PII")


async def test_a_collection_without_classifiers_is_refused(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(url=DATABASES, json={"data": {"count": 1, "databases": [
        {"id": 11, "databaseName": "SALES",
         "databaseType": "snowflake_external_functions"}]}})
    httpx_mock.add_response(url=COLLECTION, json={"collection": {"classifier_count": 0}})
    fn = await get_tool(mcp, "create_snowflake_job")
    with pytest.raises(Exception, match="has no classifiers"):
        await fn(database_id=11, collection_name="EMPTY")
    assert not [r for r in httpx_mock.get_requests() if r.method == "POST"]


async def test_the_connection_is_found_on_a_later_page(
        httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(url=DATABASES, json={"data": {"count": 2, "databases": [
        {"id": 1, "databaseType": "snowflake_external_functions"}]}})
    httpx_mock.add_response(url=DATABASES, json={"data": {"count": 2, "databases": [
        {"id": 2, "databaseName": "LATE", "databaseType": "snowflake_external_functions"}]}})
    httpx_mock.add_response(url=COLLECTION, json={"collection": {"classifier_count": 1}})
    httpx_mock.add_response(url=JOB, method="POST", json={"job_id": "j"})
    fn = await get_tool(mcp, "create_snowflake_job")
    await fn(database_id=2, collection_name="PII", schema="S")
    assert _sent(httpx_mock)[1]["scope"]["database"] == "LATE"
    offsets = [r.url.params["offset"] for r in httpx_mock.get_requests()
               if "databases" in r.url.path]
    assert offsets == ["0", "1"]


# ── Databricks ───────────────────────────────────────────────────────────


async def test_databricks_scoped_matches_the_console(
        httpx_mock: HTTPXMock, test_env, mcp, lookups):
    """The catalog goes in scope.database; no classification_type or job_type."""
    fn = await get_tool(mcp, "create_databricks_job")
    await fn(database_id=22, collection_name="PII", catalog="main")
    assert _sent(httpx_mock) == ("/v1/jobs/databricks", {
        "database_id": 22, "requires_review": True, "collection_name": "PII",
        "condition_types": CONDITIONS, "sample_size": 1000, "sample_type": "ROWS",
        "scope": {"level": "DATABASE", "database": "main"}})


async def test_databricks_schema_needs_a_catalog(
        httpx_mock: HTTPXMock, test_env, mcp, lookups):
    fn = await get_tool(mcp, "create_databricks_job")
    with pytest.raises(Exception, match="needs its database"):
        await fn(database_id=22, collection_name="PII", schema="s")


# ── Database repositories through an agent ──────────────────────────────

OLTP = {"repo_name": "repo", "agent_id": AGENT, "service_user_name": "svc",
        "collection_name": "PII"}


def _oltp(**extra):
    return {"agent_id": AGENT, "classification_type": 5, "collection_name": "PII",
            "condition_types": CONDITIONS, "repo_name": "repo",
            "sample_size": 1000, "sample_type": "ROWS",
            "service_user_name": "svc", "requires_review": True, **extra}


async def test_postgres_scoped_matches_the_console(
        httpx_mock: HTTPXMock, test_env, mcp, lookups):
    _repo(httpx_mock, "Postgres")
    fn = await get_tool(mcp, "create_oltp_job")
    await fn(**OLTP, database="appdb", exclude=["archive", "staging.orders"])
    assert _sent(httpx_mock) == ("/v1/jobs/oltp", _oltp(
        scope={"level": "DATABASE", "database": "appdb"},
        exclusions=[{"level": "SCHEMA", "database": "appdb", "schema": "archive"},
                    {"level": "TABLE", "database": "appdb", "schema": "staging",
                     "table": "orders"}]))


async def test_mysql_table_scope_repeats_the_database_as_schema(
        httpx_mock: HTTPXMock, test_env, mcp, lookups):
    _repo(httpx_mock, "MySQL")
    fn = await get_tool(mcp, "create_oltp_job")
    await fn(**OLTP, database="shop", table="customers")
    assert _sent(httpx_mock)[1] == _oltp(scope={
        "level": "TABLE", "database": "shop", "schema": "shop", "table": "customers"})


async def test_mongodb_database_exclusions_are_tables(
        httpx_mock: HTTPXMock, test_env, mcp, lookups):
    _repo(httpx_mock, "MongoDB")
    fn = await get_tool(mcp, "create_oltp_job")
    await fn(**OLTP, database="app", exclude="sessions")
    assert _sent(httpx_mock)[1]["exclusions"] == [
        {"level": "TABLE", "database": "app", "schema": "app", "table": "sessions"}]


async def test_mysql_has_no_schema_level(httpx_mock: HTTPXMock, test_env, mcp, lookups):
    _repo(httpx_mock, "MySQL")
    fn = await get_tool(mcp, "create_oltp_job")
    with pytest.raises(Exception, match="no schema level"):
        await fn(**OLTP, database="shop", schema="x")


async def test_oracle_scoped_connects_by_service_name(
        httpx_mock: HTTPXMock, test_env, mcp, lookups):
    _repo(httpx_mock, "Oracle")
    fn = await get_tool(mcp, "create_oltp_job")
    await fn(**OLTP, database="ORCLPDB1", schema="HR")
    assert _sent(httpx_mock)[1] == _oltp(
        service_name="ORCLPDB1",
        scope={"level": "SCHEMA", "database": "ORCLPDB1", "schema": "HR"})


async def test_oracle_scope_defaults_to_the_service_name(
        httpx_mock: HTTPXMock, test_env, mcp, lookups):
    _repo(httpx_mock, "Oracle")
    fn = await get_tool(mcp, "create_oltp_job")
    await fn(**OLTP, service_name="ORCLPDB1", schema="HR")
    body = _sent(httpx_mock)[1]
    assert body["scope"]["database"] == body["service_name"] == "ORCLPDB1"


async def test_oracle_unscoped_keeps_the_sid(httpx_mock: HTTPXMock, test_env, mcp, lookups):
    _repo(httpx_mock, "Oracle")
    fn = await get_tool(mcp, "create_oltp_job")
    await fn(**OLTP, sid="ORCL")
    assert _sent(httpx_mock)[1] == _oltp(sid="ORCL")


@pytest.mark.parametrize("repo_type,args,message", [
    ("Oracle", {"sid": "A", "service_name": "B"}, "not both"),
    ("Oracle", {"sid": "ORCL", "schema": "HR", "database": "PDB"}, "not SID"),
    ("Oracle", {"service_name": "A", "database": "B"}, "must match"),
    ("Postgres", {"sid": "ORCL"}, "Oracle repositories only"),
    ("S3", {}, "create_file_classification_job"),
    ("Snowflake", {}, "can't be classified"),
    ("Oracle", {"sid": "ORCL#1"}, "255 characters or fewer"),
    ("Oracle", {"service_name": "S" * 256}, "255 characters or fewer"),
])
async def test_oltp_refuses_what_the_console_refuses(
        httpx_mock: HTTPXMock, test_env, mcp, lookups, repo_type, args, message):
    _repo(httpx_mock, repo_type)
    fn = await get_tool(mcp, "create_oltp_job")
    with pytest.raises(Exception, match=message):
        await fn(**OLTP, **args)
    assert not [r for r in httpx_mock.get_requests() if r.method == "POST"]


async def test_oracle_blank_identifiers_are_left_out(
        httpx_mock: HTTPXMock, test_env, mcp, lookups):
    _repo(httpx_mock, "Oracle")
    fn = await get_tool(mcp, "create_oltp_job")
    await fn(**OLTP, database="  ", sid=" ")
    body = _sent(httpx_mock)[1]
    assert "service_name" not in body and "sid" not in body and "scope" not in body


# ── Lookups ─────────────────────────────────────────────────────────────


async def test_an_unknown_data_source_is_refused(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(url=DATABASES, json={"data": {"count": 1, "databases": [
        {"id": 11, "databaseName": "SALES",
         "databaseType": "snowflake_external_functions"}]}})
    fn = await get_tool(mcp, "create_snowflake_job")
    with pytest.raises(Exception, match="No data source with ID 99"):
        await fn(database_id=99, collection_name="PII")


async def test_a_failed_data_source_lookup_is_reported(httpx_mock: HTTPXMock, test_env, mcp):
    httpx_mock.add_response(url=DATABASES, status_code=401, json={"message": "Unauthorized"})
    fn = await get_tool(mcp, "create_snowflake_job")
    with pytest.raises(Exception, match="Could not list data sources"):
        await fn(database_id=11, collection_name="PII")


@pytest.mark.parametrize("status,message", [
    (404, "No repository named repo"),
    (401, "Could not read repository repo"),
])
async def test_repository_lookup_failures(httpx_mock: HTTPXMock, test_env, mcp, status, message):
    httpx_mock.add_response(url=REPO, status_code=status, json={"message": "x"})
    fn = await get_tool(mcp, "create_oltp_job")
    with pytest.raises(Exception, match=message):
        await fn(**OLTP)


@pytest.mark.parametrize("status,message", [
    (404, "No collection named PII"),
    (401, "Could not read collection PII"),
])
async def test_collection_lookup_failures(
        httpx_mock: HTTPXMock, test_env, mcp, status, message):
    _repo(httpx_mock, "Postgres")
    httpx_mock.add_response(url=COLLECTION, status_code=status, json={"message": "x"})
    fn = await get_tool(mcp, "create_oltp_job")
    with pytest.raises(Exception, match=message):
        await fn(**OLTP)
    assert not [r for r in httpx_mock.get_requests() if r.method == "POST"]


# ── File repositories through an agent ──────────────────────────────────


async def test_s3_defaults_match_the_console(httpx_mock: HTTPXMock, test_env, mcp, lookups):
    """file_options always sent; metadata_map omitted at its default."""
    _repo(httpx_mock, "S3")
    fn = await get_tool(mcp, "create_file_classification_job")
    await fn(**OLTP)
    assert _sent(httpx_mock) == ("/v1/jobs/oltp", _oltp(file_options={
        "scan_mode": "CRAWL", "sniff_bytes": True,
        "content_classification": True, "full_file_scan": False}))


async def test_filesystem_paths_and_options(httpx_mock: HTTPXMock, test_env, mcp, lookups):
    _repo(httpx_mock, "FILESYSTEM")
    fn = await get_tool(mcp, "create_file_classification_job")
    await fn(**OLTP, paths=["finance/", "hr/payroll"], exclude_paths="finance/tmp",
             include_glob=" *.csv ", max_file_bytes=1048576,
             metadata_map="plaintext", metadata_map_by_format={"json": "none",
                                                               "csv": "plaintext"})
    assert _sent(httpx_mock)[1] == _oltp(
        scope={"level": "PATH", "paths": ["finance", "hr/payroll"]},
        exclusions=[{"level": "PATH", "paths": ["finance/tmp"]}],
        file_options={"content_classification": True, "full_file_scan": False,
                      "include_glob": "*.csv", "max_file_bytes": 1048576},
        metadata_map={"default": "plaintext", "by_format": {"json": "none"}})


async def test_s3_glue_options(httpx_mock: HTTPXMock, test_env, mcp, lookups):
    _repo(httpx_mock, "S3")
    fn = await get_tool(mcp, "create_file_classification_job")
    await fn(**OLTP, scan_mode="glue", glue_crawler="crawler", glue_start_crawler=True)
    assert _sent(httpx_mock)[1]["file_options"] == {
        "scan_mode": "GLUE", "glue_crawler": "crawler", "glue_start_crawler": True,
        "sniff_bytes": True, "content_classification": True, "full_file_scan": False}


@pytest.mark.parametrize("repo_type,args,message", [
    ("S3", {"paths": "/abs"}, "leading"),
    ("S3", {"paths": "a/../b"}, "segments"),
    ("S3", {"paths": ["a", "a"]}, "twice"),
    ("S3", {"paths": [f"p{i}" for i in range(51)]}, "At most 50"),
    ("S3", {"max_file_bytes": 64 * 1024 * 1024 + 1}, "max_file_bytes"),
    ("S3", {"metadata_map": "raw"}, "metadata_map must be"),
    ("S3", {"exclude_paths": [f"p{i}" for i in range(101)]}, "At most 100"),
    ("S3", {"paths": "a\\b"}, "separate path segments"),
    ("S3", {"max_files": 0}, "max_files"),
    ("S3", {"metadata_map_by_format": {"pdf": "none"}}, "metadata_map_by_format keys"),
    ("FILESYSTEM", {"scan_mode": "GLUE"}, "S3 repositories only"),
    ("FILESYSTEM", {"sniff_bytes": False}, "S3 repositories only"),
    ("Postgres", {}, "create_oltp_job"),
])
async def test_file_scans_refuse_what_the_console_refuses(
        httpx_mock: HTTPXMock, test_env, mcp, lookups, repo_type, args, message):
    _repo(httpx_mock, repo_type)
    fn = await get_tool(mcp, "create_file_classification_job")
    with pytest.raises(Exception, match=message):
        await fn(**OLTP, **args)
    assert not [r for r in httpx_mock.get_requests() if r.method == "POST"]
