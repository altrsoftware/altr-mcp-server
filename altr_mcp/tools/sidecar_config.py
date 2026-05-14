from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from altr_mcp.utils.logging import log_tool
from altr_mcp.settings import get_settings
from altr_mcp.utils import sidecar_config


def _parse_dict(val):
    """Accept a dict or a JSON string encoding a dict."""
    if val is None:
        return None
    if isinstance(val, str):
        import json
        return json.loads(val)
    return val


def register(mcp: FastMCP) -> None:
    # -- Agents ------------------------------------------------------------

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_sc_agents(
            limit: int | None = None,
            contiguous_id: str | None = None,
            agent_type: str | None = None,
            name_starts_with: str | None = None
            ) -> dict:
        """List ALTR agents (SIS or CLASSIFIER) in your organization.

        Args:
            limit: Max items (default 50, max 100).
            contiguous_id: Pagination token.
            agent_type: Filter by "SIS" or "CLASSIFIER".
            name_starts_with: Case-insensitive name prefix filter.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        if agent_type is not None:
            params["type"] = agent_type
        if name_starts_with is not None:
            params["name_starts_with"] = name_starts_with
        response = await sidecar_config.list_agents(
            settings.auth, settings.org_id, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_sc_agent(
            agent_type: str,
            name: str,
            description: str | None = None,
            public_key_1: str | None = None,
            public_key_2: str | None = None
            ) -> dict:
        """Create a new ALTR agent.

        Args:
            agent_type: "SIS" or "CLASSIFIER".
            name: Agent name.
            description: Agent description.
            public_key_1: First public key for mTLS.
            public_key_2: Second public key for mTLS rotation.
        """
        settings = get_settings()
        data = {"type": agent_type, "name": name}
        if description is not None:
            data["description"] = description
        if public_key_1 is not None:
            data["public_key_1"] = public_key_1
        if public_key_2 is not None:
            data["public_key_2"] = public_key_2
        response = await sidecar_config.create_agent(
            settings.auth, settings.org_id, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_sc_agent(agent_id: str) -> dict:
        """Get details for a specific agent.

        Args:
            agent_id: Agent UUID.
        """
        settings = get_settings()
        response = await sidecar_config.get_agent(
            settings.auth, settings.org_id, agent_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_sc_agent(
            agent_id: str,
            name: str | None = None,
            description: str | None = None,
            public_key_1: str | None = None,
            public_key_2: str | None = None
            ) -> dict:
        """Update an existing agent. Only provided fields are changed.

        Args:
            agent_id: Agent UUID.
            name: Updated name.
            description: Updated description.
            public_key_1: Updated first public key.
            public_key_2: Updated second public key.
        """
        settings = get_settings()
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if public_key_1 is not None:
            data["public_key_1"] = public_key_1
        if public_key_2 is not None:
            data["public_key_2"] = public_key_2
        response = await sidecar_config.update_agent(
            settings.auth, settings.org_id, agent_id, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def delete_sc_agent(agent_id: str) -> dict:
        """Delete an agent. Agent must have task_count of 0.

        Args:
            agent_id: Agent UUID.
        """
        settings = get_settings()
        response = await sidecar_config.delete_agent(
            settings.auth, settings.org_id, agent_id)
        return {"success": True, "data": response, "error": None}

    # -- Agent Tasks -------------------------------------------------------

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_sc_agent_tasks(
            agent_id: str,
            limit: int | None = None,
            contiguous_id: str | None = None
            ) -> dict:
        """List tasks assigned to an agent.

        Args:
            agent_id: Agent UUID.
            limit: Max items (default 50, max 100).
            contiguous_id: Pagination token.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        response = await sidecar_config.list_agent_tasks(
            settings.auth, settings.org_id, agent_id, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_sc_agent_task(
            agent_id: str,
            name: str,
            repo_name: str,
            configuration: str | dict,
            schedule: str | dict,
            description: str | None = None,
            service_user: str | None = None
            ) -> dict:
        """Create a task for an agent.

        A task runs against a specific repo on a schedule.
        Configuration depends on agent type (check with
        `get_sc_agent` first).

        **CLASSIFIER agent** configuration:
        - classification_type: must be 5
        - sample_strategy: "ROWS" or "PERCENT"
        - collection_name: classifier collection name
        Do NOT include SIS fields (service_name,
        audit_file_path, etc.) for classifier agents.

        **SIS (audit) agent** configuration varies by DB:
        - Oracle: optional 'initial_audit_timestamp',
          'service_name'
        - MSSQL: 'audit_file_path' (required, absolute path)
        - PostgreSQL: 'audit_file_path', 'audit_file_type'
          (log/csv/json), optional 'log_line_prefix'
        - MySQL: either 'table_name' or 'audit_file_path'
        Do NOT include classifier fields for SIS agents.

        Schedule: 'type' ("CRON"), 'value' (cron expression),
        optional 'max_duration' (ISO 8601), optional
        'timezone' (e.g. "America/New_York").

        Args:
            agent_id: Agent UUID.
            name: Task name.
            repo_name: Target repository name.
            configuration: Agent-type-specific config dict
                or JSON string. See above for required fields.
            schedule: Schedule dict or JSON string.
            description: Optional task description.
            service_user: Service user for auth. Required
                for Oracle, MSSQL, MySQL (table_name mode).
                Forbidden for PostgreSQL and MySQL
                (audit_file_path mode).
        """
        configuration = _parse_dict(configuration)
        schedule = _parse_dict(schedule)
        data = {
            "name": name,
            "repo_name": repo_name,
            "configuration": configuration,
            "schedule": schedule,
        }
        if description is not None:
            data["description"] = description
        if service_user is not None:
            data["service_user"] = service_user
        settings = get_settings()
        response = await sidecar_config.create_agent_task(
            settings.auth, settings.org_id, agent_id, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_sc_agent_task(
            agent_id: str,
            task_id: str,
            name: str | None = None,
            description: str | None = None,
            configuration: str | dict | None = None,
            schedule: str | dict | None = None
            ) -> dict:
        """Update an agent task. Only provided fields change.

        Configuration update rules vary by database type.
        See `create_sc_agent_task` for details.

        Args:
            agent_id: Agent UUID.
            task_id: Task UUID.
            name: Updated task name.
            description: Updated description.
            configuration: Updated config dict or JSON string.
            schedule: Updated schedule dict or JSON string.
        """
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if configuration is not None:
            data["configuration"] = _parse_dict(configuration)
        if schedule is not None:
            data["schedule"] = _parse_dict(schedule)
        settings = get_settings()
        response = await sidecar_config.update_agent_task(
            settings.auth, settings.org_id,
            agent_id, task_id, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def delete_sc_agent_task(
            agent_id: str,
            task_id: str
            ) -> dict:
        """Delete an agent task.

        Atomically removes the task and decrements the agent's
        and service user's task counts.

        Args:
            agent_id: Agent UUID.
            task_id: Task UUID.
        """
        settings = get_settings()
        response = await sidecar_config.delete_agent_task(
            settings.auth, settings.org_id, agent_id, task_id)
        return {"success": True, "data": response, "error": None}

    # -- Repos -------------------------------------------------------------

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_sc_repos(
            limit: int | None = None,
            contiguous_id: str | None = None,
            repo_type: str | None = None
            ) -> dict:
        """List database repositories configured for sidecar proxying.

        Args:
            limit: Max items (default 50, max 100).
            contiguous_id: Pagination token.
            repo_type: Filter by "Oracle", "MSSQL", "MySQL", or "Postgres".
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        if repo_type is not None:
            params["repo_type"] = repo_type
        response = await sidecar_config.list_repos(
            settings.auth, settings.org_id, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_sc_repo(
            name: str,
            repo_type: str,
            hostname: str,
            port: int,
            description: str | None = None
            ) -> dict:
        """Create a new database repository for sidecar proxying.

        Args:
            name: Repository name.
            repo_type: Database type (e.g., "Oracle",
                "MSSQL", "MySQL", "Postgres").
            hostname: Database server hostname.
            port: Database server port.
            description: Repository description.
        """
        settings = get_settings()
        data = {
            "name": name,
            "type": repo_type,
            "hostname": hostname,
            "port": port,
        }
        if description is not None:
            data["description"] = description
        response = await sidecar_config.create_repo(
            settings.auth, settings.org_id, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_sc_repo(repo_name: str) -> dict:
        """Get details for a specific repository.

        Args:
            repo_name: Repository name.
        """
        settings = get_settings()
        response = await sidecar_config.get_repo(
            settings.auth, settings.org_id, repo_name)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_sc_repo(repo_name: str, description: str) -> dict:
        """Update a repository's description.

        Args:
            repo_name: Repository name.
            description: Updated description.
        """
        settings = get_settings()
        data = {"description": description}
        response = await sidecar_config.update_repo(
                settings.auth, settings.org_id, repo_name, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def delete_sc_repo(repo_name: str) -> dict:
        """Delete a repository. Must have no users or bindings.

        Args:
            repo_name: Repository name.
        """
        settings = get_settings()
        response = await sidecar_config.delete_repo(
            settings.auth, settings.org_id, repo_name)
        return {"success": True, "data": response, "error": None}

    # -- Repo Users --------------------------------------------------------

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_sc_repo_users(
            repo_name: str,
            limit: int | None = None,
            contiguous_id: str | None = None
            ) -> dict:
        """List users configured for a repository.

        Args:
            repo_name: Repository name.
            limit: Max items (default 50, max 100).
            contiguous_id: Pagination token.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        response = await sidecar_config.list_repo_users(
                settings.auth, settings.org_id, repo_name, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_sc_repo_user(
            repo_name: str,
            username: str,
            aws_secrets_manager: str | dict | None = None,
            azure_key_vault: str | dict | None = None
            ) -> dict:
        """Create a repo user with credential reference.

        Provide exactly one of aws_secrets_manager or azure_key_vault.

        Args:
            repo_name: Repository name.
            username: Database username.
            aws_secrets_manager: Dict with 'secrets_path' (required) and
                'iam_role' (optional).
            azure_key_vault: Dict with 'key_vault_uri' and 'secret_name'.
        """
        settings = get_settings()
        data = {"username": username}
        if aws_secrets_manager is not None:
            data["aws_secrets_manager"] = _parse_dict(aws_secrets_manager)
        if azure_key_vault is not None:
            data["azure_key_vault"] = _parse_dict(azure_key_vault)
        response = await sidecar_config.create_repo_user(
                settings.auth, settings.org_id, repo_name, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_sc_repo_user(repo_name: str, username: str) -> dict:
        """Get details for a specific repo user.

        Args:
            repo_name: Repository name.
            username: Database username.
        """
        settings = get_settings()
        response = await sidecar_config.get_repo_user(
                settings.auth, settings.org_id, repo_name, username)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_sc_repo_user(
            repo_name: str,
            username: str,
            aws_secrets_manager: str | dict | None = None,
            azure_key_vault: str | dict | None = None
            ) -> dict:
        """Update a repo user's credential reference.

        Args:
            repo_name: Repository name.
            username: Database username.
            aws_secrets_manager: Updated AWS Secrets Manager config.
            azure_key_vault: Updated Azure Key Vault config.
        """
        settings = get_settings()
        data = {}
        if aws_secrets_manager is not None:
            data["aws_secrets_manager"] = _parse_dict(aws_secrets_manager)
        if azure_key_vault is not None:
            data["azure_key_vault"] = _parse_dict(azure_key_vault)
        response = await sidecar_config.update_repo_user(
                settings.auth, settings.org_id, repo_name, username, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def delete_sc_repo_user(repo_name: str, username: str) -> dict:
        """Delete a repo user.

        Args:
            repo_name: Repository name.
            username: Database username to delete.
        """
        settings = get_settings()
        response = await sidecar_config.delete_repo_user(
                settings.auth, settings.org_id, repo_name, username)
        return {"success": True, "data": response, "error": None}

    # -- Service Users -----------------------------------------------------

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_sc_service_users(
            repo_name: str | None = None,
            limit: int | None = None,
            contiguous_id: str | None = None,
            username_starts_with: str | None = None
            ) -> dict:
        """List service users. Optionally filter by repo.

        Args:
            repo_name: If provided, list only service users for this repo.
            limit: Max items (default 50, max 100).
            contiguous_id: Pagination token.
            username_starts_with: Filter by username prefix
                (only works with repo_name).
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id

        if repo_name is not None:
            if username_starts_with is not None:
                params["username_starts_with"] = username_starts_with
            response = await sidecar_config.list_repo_service_users(
                    settings.auth, settings.org_id, repo_name, params)
        else:
            response = await sidecar_config.list_service_users(
                    settings.auth, settings.org_id, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_sc_service_user(
            repo_name: str,
            username: str,
            resource: str,
            aws_secrets_manager: str | dict | None = None,
            azure_key_vault: str | dict | None = None
            ) -> dict:
        """Create a service user for a repository.

        Provide exactly one of aws_secrets_manager or azure_key_vault.

        Args:
            repo_name: Repository name.
            username: Service user name.
            resource: Resource identifier.
            aws_secrets_manager: Dict with 'secrets_path'
                and optional 'iam_role'.
            azure_key_vault: Dict with 'key_vault_uri'
                and 'secret_name'.
        """
        settings = get_settings()
        data = {"username": username, "resource": resource}
        if aws_secrets_manager is not None:
            data["aws_secrets_manager"] = _parse_dict(aws_secrets_manager)
        if azure_key_vault is not None:
            data["azure_key_vault"] = _parse_dict(azure_key_vault)
        response = await sidecar_config.create_service_user(
                settings.auth, settings.org_id, repo_name, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_sc_service_user(repo_name: str, username: str) -> dict:
        """Get details for a specific service user.

        Args:
            repo_name: Repository name.
            username: Service user name.
        """
        settings = get_settings()
        response = await sidecar_config.get_service_user(
                settings.auth, settings.org_id, repo_name, username)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_sc_service_user(
            repo_name: str,
            username: str,
            resource: str | None = None,
            aws_secrets_manager: str | dict | None = None,
            azure_key_vault: str | dict | None = None
            ) -> dict:
        """Update a service user. Only provided fields are changed.

        Args:
            repo_name: Repository name.
            username: Service user name.
            resource: Updated resource identifier.
            aws_secrets_manager: Updated AWS config.
            azure_key_vault: Updated Azure config.
        """
        settings = get_settings()
        data = {}
        if resource is not None:
            data["resource"] = resource
        if aws_secrets_manager is not None:
            data["aws_secrets_manager"] = _parse_dict(aws_secrets_manager)
        if azure_key_vault is not None:
            data["azure_key_vault"] = _parse_dict(azure_key_vault)
        response = await sidecar_config.update_service_user(
                settings.auth, settings.org_id, repo_name, username, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def delete_sc_service_user(repo_name: str, username: str) -> dict:
        """Delete a service user.

        Args:
            repo_name: Repository name.
            username: Service user name to delete.
        """
        settings = get_settings()
        response = await sidecar_config.delete_service_user(
                settings.auth, settings.org_id, repo_name, username)
        return {"success": True, "data": response, "error": None}

    # -- Sidecars ----------------------------------------------------------

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_sc_sidecars(
            limit: int | None = None,
            contiguous_id: str | None = None
            ) -> dict:
        """List sidecars in your organization.

        Args:
            limit: Max items (default 50, max 100).
            contiguous_id: Pagination token.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        response = await sidecar_config.list_sidecars(
            settings.auth, settings.org_id, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_sc_sidecar(
            name: str,
            hostname: str,
            description: str | None = None,
            public_key_1: str | None = None,
            public_key_2: str | None = None,
            unsupported_query_bypass: bool | None = None,
            disable_platform_audits: bool | None = None
            ) -> dict:
        """Create a new sidecar.

        Args:
            name: Sidecar name (max 64 chars).
            hostname: Sidecar hostname (max 500 chars).
            description: Sidecar description (max 400 chars).
            public_key_1: First public key for mTLS.
            public_key_2: Second public key for mTLS rotation.
            unsupported_query_bypass: If true, unsupported queries bypass
                the query parser.
            disable_platform_audits: If true, sidecar won't
                send activity audits.
        """
        settings = get_settings()
        data = {"name": name, "hostname": hostname}
        if description is not None:
            data["description"] = description
        if public_key_1 is not None:
            data["public_key_1"] = public_key_1
        if public_key_2 is not None:
            data["public_key_2"] = public_key_2
        if unsupported_query_bypass is not None:
            data["unsupported_query_bypass"] = unsupported_query_bypass
        if disable_platform_audits is not None:
            data["disable_platform_audits"] = disable_platform_audits
        response = await sidecar_config.create_sidecar(
            settings.auth, settings.org_id, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_sc_sidecar(sidecar_id: str) -> dict:
        """Get details for a specific sidecar.

        Args:
            sidecar_id: Sidecar UUID.
        """
        settings = get_settings()
        response = await sidecar_config.get_sidecar(
            settings.auth, settings.org_id, sidecar_id)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_sc_sidecar(
            sidecar_id: str,
            name: str | None = None,
            hostname: str | None = None,
            description: str | None = None,
            public_key_1: str | None = None,
            public_key_2: str | None = None,
            unsupported_query_bypass: bool | None = None,
            disable_platform_audits: bool | None = None
            ) -> dict:
        """Update a sidecar. Only provided fields are changed.

        Args:
            sidecar_id: Sidecar UUID.
            name: Updated name.
            hostname: Updated hostname.
            description: Updated description.
            public_key_1: Updated first public key.
            public_key_2: Updated second public key.
            unsupported_query_bypass: Updated bypass setting.
            disable_platform_audits: Updated audit setting.
        """
        settings = get_settings()
        data = {}
        if name is not None:
            data["name"] = name
        if hostname is not None:
            data["hostname"] = hostname
        if description is not None:
            data["description"] = description
        if public_key_1 is not None:
            data["public_key_1"] = public_key_1
        if public_key_2 is not None:
            data["public_key_2"] = public_key_2
        if unsupported_query_bypass is not None:
            data["unsupported_query_bypass"] = unsupported_query_bypass
        if disable_platform_audits is not None:
            data["disable_platform_audits"] = disable_platform_audits
        response = await sidecar_config.update_sidecar(
                settings.auth, settings.org_id, sidecar_id, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def delete_sc_sidecar(sidecar_id: str) -> dict:
        """Delete a sidecar. Must have no listeners.

        Args:
            sidecar_id: Sidecar UUID.
        """
        settings = get_settings()
        response = await sidecar_config.delete_sidecar(
            settings.auth, settings.org_id, sidecar_id)
        return {"success": True, "data": response, "error": None}

    # -- Listeners ---------------------------------------------------------

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_sc_sidecar_listeners(
            sidecar_id: str,
            limit: int | None = None,
            contiguous_id: str | None = None
            ) -> dict:
        """List listener ports registered on a sidecar.

        Args:
            sidecar_id: Sidecar UUID.
            limit: Max items (default 50, max 100).
            contiguous_id: Pagination token.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        response = await sidecar_config.list_sidecar_listeners(
                settings.auth, settings.org_id, sidecar_id, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def register_sc_sidecar_listener(
            sidecar_id: str,
            port: int,
            database_type: str,
            advertised_version: str | None = None
            ) -> dict:
        """Register a listener port on a sidecar.

        Args:
            sidecar_id: Sidecar UUID.
            port: Port number to listen on.
            database_type: Database type for this listener.
            advertised_version: Optional version string to advertise.
        """
        settings = get_settings()
        data = {"port": port, "database_type": database_type}
        if advertised_version is not None:
            data["advertised_version"] = advertised_version
        response = await sidecar_config.register_sidecar_listener(
                settings.auth, settings.org_id, sidecar_id, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def deregister_sc_sidecar_listener(
            sidecar_id: str, port: int) -> dict:
        """Remove a listener port from a sidecar.

        Args:
            sidecar_id: Sidecar UUID.
            port: Port number to deregister.
        """
        settings = get_settings()
        response = await sidecar_config.deregister_sidecar_listener(
                settings.auth, settings.org_id, sidecar_id, port)
        return {"success": True, "data": response, "error": None}

    # -- Bindings ----------------------------------------------------------

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_sc_sidecar_bindings(
            sidecar_id: str,
            ports: str | None = None,
            repo_names: str | None = None,
            limit: int | None = None,
            contiguous_id: str | None = None
            ) -> dict:
        """List repo bindings for a sidecar.

        Args:
            sidecar_id: Sidecar UUID.
            ports: Comma-separated port filter.
            repo_names: Comma-separated repo name filter.
            limit: Max items (default 50, max 100).
            contiguous_id: Pagination token.
        """
        settings = get_settings()
        params = {}
        if ports is not None:
            params["ports"] = ports
        if repo_names is not None:
            params["repo_names"] = repo_names
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        response = await sidecar_config.list_sidecar_bindings(
                settings.auth, settings.org_id, sidecar_id, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_sc_repo_bindings(
            repo_name: str,
            ports: str | None = None,
            sidecar_ids: str | None = None,
            limit: int | None = None,
            contiguous_id: str | None = None
            ) -> dict:
        """List sidecar bindings for a repository.

        Args:
            repo_name: Repository name.
            ports: Comma-separated port filter.
            sidecar_ids: Comma-separated sidecar ID filter.
            limit: Max items (default 50, max 100).
            contiguous_id: Pagination token.
        """
        settings = get_settings()
        params = {}
        if ports is not None:
            params["ports"] = ports
        if sidecar_ids is not None:
            params["sidecar_ids"] = sidecar_ids
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        response = await sidecar_config.list_repo_bindings(
                settings.auth, settings.org_id, repo_name, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_sc_sidecar_binding(
            sidecar_id: str, port: int, repo_name: str) -> dict:
        """Get a specific sidecar-repo binding.

        Args:
            sidecar_id: Sidecar UUID.
            port: Listener port number.
            repo_name: Repository name.
        """
        settings = get_settings()
        response = await sidecar_config.get_sidecar_binding(
                settings.auth, settings.org_id, sidecar_id, port, repo_name)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_sc_sidecar_binding(
            sidecar_id: str, port: int, repo_name: str) -> dict:
        """Bind a repository to a sidecar listener port.

        Args:
            sidecar_id: Sidecar UUID.
            port: Listener port number.
            repo_name: Repository name to bind.
        """
        settings = get_settings()
        response = await sidecar_config.create_sidecar_binding(
                settings.auth, settings.org_id, sidecar_id, port, repo_name)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def delete_sc_sidecar_binding(
            sidecar_id: str, port: int, repo_name: str) -> dict:
        """Remove a repo binding from a sidecar listener port.

        Args:
            sidecar_id: Sidecar UUID.
            port: Listener port number.
            repo_name: Repository name to unbind.
        """
        settings = get_settings()
        response = await sidecar_config.delete_sidecar_binding(
                settings.auth, settings.org_id, sidecar_id, port, repo_name)
        return {"success": True, "data": response, "error": None}
