"""Verify MCP tool annotations match naming convention.

All get_* and list_* tools must have readOnlyHint=True.
All delete_* tools must have destructiveHint=True.
All other tools must have no annotations set.
"""
import asyncio
import os
import pytest
from fastmcp import FastMCP
from altr_mcp.tools import register_all


@pytest.fixture(scope="module")
def annotated_mcp():
    """Create a FastMCP instance with all tools registered."""
    os.environ.setdefault("ORG_ID", "test")
    os.environ.setdefault("MAPI_KEY", "test")
    os.environ.setdefault("MAPI_SECRET", "test")
    mcp = FastMCP("test")
    register_all(mcp)
    return mcp


def _get_component(mcp, tool_name):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(mcp.get_tool(tool_name))
    finally:
        loop.close()


# -- Complete lists derived from naming convention --

GET_LIST_TOOLS = [
    # tag.py
    "get_tags", "get_tag_values",
    "get_tag_details_by_group_id", "get_tag_details",
    # policy.py
    "get_policies", "get_rules", "get_roles",
    # classification.py
    "get_classifiers", "get_collections",
    "get_jobs", "get_classification_report",
    # database.py
    "get_databases", "get_database_id", "get_service_users",
    # access_request.py
    "get_access_requests", "get_access_request",
    # telemetry.py
    "get_agent_instances", "get_agent_instance",
    "get_agent_task_telemetry",
    "get_sidecar_instances", "get_sidecar_instance",
    "get_task_telemetry",
    # audit.py
    "get_audit_results",
    "get_query_audit_results",
    "get_system_audit_results",
    # sidecar_config.py
    "list_sc_agents", "get_sc_agent",
    "list_sc_agent_tasks",
    "list_sc_repos", "get_sc_repo",
    "list_sc_repo_users", "get_sc_repo_user",
    "list_sc_service_users", "get_sc_service_user",
    "list_sc_sidecars", "get_sc_sidecar",
    "list_sc_sidecar_listeners",
    "list_sc_sidecar_bindings",
    "list_sc_repo_bindings", "get_sc_sidecar_binding",
]

DELETE_TOOLS = [
    # tag.py
    "delete_tag", "delete_tag_by_details",
    # policy.py
    "delete_policy", "delete_rule",
    # classification.py
    "delete_classifier", "delete_collection",
    # database.py
    "delete_database",
    # telemetry.py
    "delete_agent_instance",
    "delete_sidecar_instance", "delete_task_telemetry",
    # sidecar_config.py
    "delete_sc_agent", "delete_sc_agent_task",
    "delete_sc_repo", "delete_sc_repo_user",
    "delete_sc_service_user",
    "delete_sc_sidecar", "delete_sc_sidecar_binding",
]

NO_ANNOTATION_TOOLS = [
    # tag.py
    "update_tag", "connect_tag",
    # policy.py
    "create_policy", "add_rules", "update_rule",
    # classification.py
    "create_classifier", "create_collection",
    "create_job", "create_databricks_job", "update_job_status",
    "add_classifiers_to_collection",
    "remove_classifiers_from_collection",
    # database.py
    "create_database", "create_databricks_database", "update_database",
    "trigger_database_status_sync",
    # access_management.py
    "create_snowflake_access_policy",
    "update_snowflake_access_policy",
    "create_oltp_access_policy",
    "trigger_access_policy_check",
    # access_request.py
    "create_access_request",
    "approve_access_request",
    "deny_access_request", "cancel_access_request",
    # audit.py
    "search_audits",
    "search_query_audits", "search_system_audits",
    # sidecar_config.py
    "create_sc_agent", "update_sc_agent",
    "create_sc_agent_task", "update_sc_agent_task",
    "create_sc_repo", "update_sc_repo",
    "create_sc_repo_user", "update_sc_repo_user",
    "create_sc_service_user", "update_sc_service_user",
    "create_sc_sidecar", "update_sc_sidecar",
    "register_sc_sidecar_listener",
    "deregister_sc_sidecar_listener",
    "create_sc_sidecar_binding",
]


def test_total_tools_is_99(annotated_mcp):
    """Sanity check: all three lists account for all 99 tools."""
    total = (
        len(GET_LIST_TOOLS)
        + len(DELETE_TOOLS)
        + len(NO_ANNOTATION_TOOLS)
    )
    assert total == 99, (
        f"Expected 99, got {total} "
        f"({len(GET_LIST_TOOLS)} + {len(DELETE_TOOLS)} "
        f"+ {len(NO_ANNOTATION_TOOLS)})"
    )


@pytest.mark.parametrize("tool_name", GET_LIST_TOOLS)
def test_get_list_tools_have_read_only_hint(
        annotated_mcp, tool_name):
    component = _get_component(annotated_mcp, tool_name)
    assert component.annotations is not None, (
        f"{tool_name} has no annotations"
    )
    assert component.annotations.readOnlyHint is True, (
        f"{tool_name} missing readOnlyHint"
    )


@pytest.mark.parametrize("tool_name", DELETE_TOOLS)
def test_delete_tools_have_destructive_hint(
        annotated_mcp, tool_name):
    component = _get_component(annotated_mcp, tool_name)
    assert component.annotations is not None, (
        f"{tool_name} has no annotations"
    )
    assert component.annotations.destructiveHint is True, (
        f"{tool_name} missing destructiveHint"
    )


@pytest.mark.parametrize("tool_name", NO_ANNOTATION_TOOLS)
def test_other_tools_have_no_annotation(
        annotated_mcp, tool_name):
    component = _get_component(annotated_mcp, tool_name)
    assert component.annotations is None, (
        f"{tool_name} should have no annotations"
        f" but has {component.annotations}"
    )
