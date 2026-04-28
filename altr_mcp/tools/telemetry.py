from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from altr_mcp.utils.logging import log_tool
from altr_mcp.settings import get_settings
from altr_mcp.utils import telemetry


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_agent_instances(
            agent_id: str,
            limit: int | None = None,
            contiguous_id: str | None = None
            ) -> dict:
        """List running instances for a specific ALTR agent.

        Args:
            agent_id: Agent UUID.
            limit: Max items to return.
            contiguous_id: Pagination token from a prior call.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        response = await telemetry.get_agent_instances(
                settings.auth, settings.org_id, agent_id, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_agent_instance(agent_id: str, instance_id: str) -> dict:
        """Get details for a specific agent instance.

        Args:
            agent_id: Agent UUID.
            instance_id: Instance UUID.
        """
        settings = get_settings()
        response = await telemetry.get_agent_instance(
                settings.auth, settings.org_id, agent_id, instance_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def delete_agent_instance(agent_id: str, instance_id: str) -> dict:
        """Delete an agent instance.

        Args:
            agent_id: Agent UUID.
            instance_id: Instance UUID to delete.
        """
        settings = get_settings()
        response = await telemetry.delete_agent_instance(
                settings.auth, settings.org_id, agent_id, instance_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_agent_task_telemetry(
            agent_id: str,
            limit: int | None = None,
            contiguous_id: str | None = None
            ) -> dict:
        """Get task telemetry for a specific agent.

        Returns task status, messages, and metadata for tasks assigned to
        this agent.

        Args:
            agent_id: Agent UUID.
            limit: Max items to return.
            contiguous_id: Pagination token from a prior call.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        response = await telemetry.get_agent_task_telemetry(
                settings.auth, settings.org_id, agent_id, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_sidecar_instances(
            sidecar_id: str,
            limit: int | None = None,
            contiguous_id: str | None = None
            ) -> dict:
        """List running instances for a specific sidecar.

        Args:
            sidecar_id: Sidecar UUID.
            limit: Max items to return.
            contiguous_id: Pagination token from a prior call.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        response = await telemetry.get_sidecar_instances(
                settings.auth, settings.org_id, sidecar_id, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_sidecar_instance(sidecar_id: str, instance_id: str) -> dict:
        """Get details for a specific sidecar instance.

        Args:
            sidecar_id: Sidecar UUID.
            instance_id: Instance UUID.
        """
        settings = get_settings()
        response = await telemetry.get_sidecar_instance(
                settings.auth, settings.org_id, sidecar_id, instance_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def delete_sidecar_instance(
            sidecar_id: str, instance_id: str) -> dict:
        """Delete a sidecar instance.

        Args:
            sidecar_id: Sidecar UUID.
            instance_id: Instance UUID to delete.
        """
        settings = get_settings()
        response = await telemetry.delete_sidecar_instance(
                settings.auth, settings.org_id, sidecar_id, instance_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_task_telemetry(task_id: str) -> dict:
        """Get telemetry for a specific task by its ID.

        Args:
            task_id: Task UUID.
        """
        settings = get_settings()
        response = await telemetry.get_task_telemetry(
            settings.auth, settings.org_id, task_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def delete_task_telemetry(task_id: str) -> dict:
        """Delete telemetry for a specific task.

        Args:
            task_id: Task UUID.
        """
        settings = get_settings()
        response = await telemetry.delete_task_telemetry(
            settings.auth, settings.org_id, task_id)
        return {"success": True, "data": response, "error": None}
