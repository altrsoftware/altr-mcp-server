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


def _add_credential(
        data: dict,
        aws_secrets_manager,
        azure_key_vault,
        environment_variable,
        secret_file) -> None:
    """Copy the credential source given into a request body.

    The API takes at most one source, so a second is refused here.
    """
    sources = {
        "aws_secrets_manager": aws_secrets_manager,
        "azure_key_vault": azure_key_vault,
        "environment_variable": environment_variable,
        "secret_file": secret_file,
    }
    given = {k: v for k, v in sources.items() if v is not None}
    if len(given) > 1:
        raise ValueError(
            "Give only one credential source, not "
            + " and ".join(given) + ".")
    for key, value in given.items():
        data[key] = _parse_dict(value)


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
            settings.auth, params)
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
            settings.auth, data)
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
            settings.auth, agent_id)
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
            settings.auth, agent_id, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def disconnect_sc_agent(agent_id: str) -> dict:
        """Disconnect an agent from ALTR. Agent must have task_count of 0.

        Args:
            agent_id: Agent UUID.
        """
        settings = get_settings()
        response = await sidecar_config.delete_agent(
            settings.auth, agent_id)
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
            settings.auth, agent_id, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_sc_agent_task(agent_id: str, task_id: str) -> dict:
        """Get one task of an agent, with its configuration and schedule.

        Args:
            agent_id: Agent UUID.
            task_id: Task UUID.
        """
        settings = get_settings()
        response = await sidecar_config.get_agent_task(
            settings.auth, agent_id, task_id)
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
        Configuration depends on the agent type (check with
        `get_sc_agent` first) and the repo type.

        **CLASSIFIER agent** configuration, any repo type:
        - classification_type: 5, the only accepted value.
        - collection_name: classifier collection name. Required.
        - condition_types: condition targets to evaluate, e.g.
          ["ROW_DATA", "METADATA", "COLUMN_LOCATION"]. Others include
          GDLP, SNOWFLAKE_NATIVE, CONTENT_TYPE, DATA_LENGTH,
          COLUMN_SIZE and AMAZON_COMPREHEND.
        - sample_strategy: legacy alternative to condition_types:
          ROWS, METADATA or PERCENT. Give at least one of the two.
        - sample_size and sample_type: optional sampling budget, sent
          together. sample_type ROWS makes sample_size a row count;
          PERCENT makes it 1-100. Rejected with METADATA.
        - requires_review: hold each job's report for human review.
        - scope: limit runs to one database, schema or table, e.g.
          {"level": "TABLE", "database": "db", "schema": "s",
          "table": "t"}. S3 and FILESYSTEM repos take
          {"level": "PATH", "paths": ["dir/"]}. Omit for the whole
          source.
        - exclusions: list of scopes to skip, at most 100.
        - file_options (S3 and FILESYSTEM only):
          content_classification, full_file_scan, include_glob,
          exclude_glob, max_files, max_file_bytes; S3 also scan_mode
          (CRAWL or GLUE), sniff_bytes, glue_crawler,
          glue_start_crawler.
        - metadata_map (S3 and FILESYSTEM only): "hashed" (default),
          "plaintext" or "none", or
          {"default": ..., "by_format": {"csv": ...}}.
        Do NOT include SIS fields for classifier agents.

        **SIS (audit) agent** configuration varies by repo type:
        - Oracle: optional 'service_name'.
        - MSSQL: 'audit_file_path' (required, absolute path).
        - Postgres: 'audit_file_path', 'audit_file_type' ("stderr",
          "csv" or "json"). 'log_line_prefix' is required with
          "stderr" and rejected otherwise.
        - MySQL: either 'table_name' or 'audit_file_path'.
        - Snowflake: 'table_name': QUERY_HISTORY, LOGIN_HISTORY or
          SESSIONS.
        - Databricks: 'table_name' (QUERY_HISTORY or ACCESS_AUDIT) and
          'workspace_id' (numeric).
        - Any type: optional 'initial_audit_timestamp' (RFC 3339) and
          'ssl_config' (enabled, trust_server_certificate,
          trust_store_path, trust_store_password_arn,
          hostname_in_certificate).
        MongoDB, Cassandra, S3 and FILESYSTEM repos take no SIS tasks.
        Do NOT include classifier fields for SIS agents.

        Schedule: 'type' ("CRON"), 'value' (cron expression),
        optional 'max_duration' (ISO 8601), optional
        'timezone' (default "UTC").

        Args:
            agent_id: Agent UUID.
            name: Task name (max 64 chars).
            repo_name: Target repository name.
            configuration: Agent-type-specific config dict
                or JSON string. See above for required fields.
            schedule: Schedule dict or JSON string.
            description: Optional task description.
            service_user: Service user the agent signs in as.
                SIS: required for Oracle, MSSQL, Snowflake,
                Databricks and MySQL with 'table_name'; rejected for
                Postgres and MySQL with 'audit_file_path'.
                CLASSIFIER: required except on FILESYSTEM repos.
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
            settings.auth, agent_id, data)
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

        CLASSIFIER tasks: configuration fields not sent are kept, and
        the merged result must pass the create rules. scope,
        exclusions, file_options and metadata_map replace the stored
        value; send null (or [] for exclusions) to clear one.

        SIS tasks: 'initial_audit_timestamp' cannot change. Every type
        takes 'ssl_config'. Oracle also takes 'service_name'; MSSQL
        'audit_file_path'; Postgres any of 'audit_file_path',
        'audit_file_type', 'log_line_prefix'; MySQL only the field it
        was created with; Snowflake 'table_name'; Databricks
        'table_name' and 'workspace_id'.

        See `create_sc_agent_task` for the field rules.

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
            settings.auth,
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
            settings.auth, agent_id, task_id)
        return {"success": True, "data": response, "error": None}

    # -- Repos -------------------------------------------------------------

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_sc_repos(
            limit: int | None = None,
            contiguous_id: str | None = None,
            repo_type: str | None = None,
            name_starts_with: str | None = None
            ) -> dict:
        """List repos: the data sources sidecars and agents connect to.

        Args:
            limit: Max items (default 50, max 100).
            contiguous_id: Pagination token.
            repo_type: Filter by "Oracle", "MSSQL", "MySQL", "Postgres",
                "MongoDB", "Cassandra", "Snowflake", "Databricks", "S3"
                or "FILESYSTEM".
            name_starts_with: Case-insensitive name prefix filter.
        """
        settings = get_settings()
        params = {}
        if limit is not None:
            params["limit"] = limit
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        if repo_type is not None:
            params["repo_type"] = repo_type
        if name_starts_with is not None:
            params["name_starts_with"] = name_starts_with
        response = await sidecar_config.list_repos(
            settings.auth, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_sc_repo(
            name: str,
            repo_type: str,
            hostname: str | None = None,
            port: int | None = None,
            description: str | None = None,
            connection_properties: str | dict | None = None,
            audit_properties: str | dict | None = None
            ) -> dict:
        """Create a repo: a database, warehouse or file store.

        Args:
            name: Repo name: lowercase letters, digits and
                underscores, max 32 chars.
            repo_type: "Oracle", "MSSQL", "MySQL", "Postgres",
                "MongoDB", "Cassandra", "Snowflake", "Databricks",
                "S3" or "FILESYSTEM".
            hostname: Server hostname. Required for every type but S3
                and FILESYSTEM, which reject it. Snowflake:
                "<account>.snowflakecomputing.com"; Databricks: the
                workspace host.
            port: Server port. Required and rejected like hostname.
                Snowflake and Databricks use 443.
            description: Repository description (max 100 chars).
            connection_properties: Dict of strings, or JSON string.
                Accepted only for these types:
                S3: 'bucket' and 'region' (required), 'prefix',
                'glue_database'. FILESYSTEM: 'root_path' (required).
                Databricks: 'http_path' of the SQL warehouse
                (required). MongoDB: 'auth_database', 'replica_set',
                'srv' ("true" or "false"), 'connection_options'.
            audit_properties: Dict, or JSON string. The only key is
                'redact_comments': "*" redacts SQL comments from
                audited query text; "" (the default) keeps them.
        """
        settings = get_settings()
        data = {"name": name, "type": repo_type}
        if hostname is not None:
            data["hostname"] = hostname
        if port is not None:
            data["port"] = port
        if description is not None:
            data["description"] = description
        if connection_properties is not None:
            data["connection_properties"] = _parse_dict(
                connection_properties)
        if audit_properties is not None:
            data["audit_properties"] = _parse_dict(audit_properties)
        response = await sidecar_config.create_repo(
            settings.auth, data)
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
            settings.auth, repo_name)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_sc_repo(
            repo_name: str,
            description: str | None = None,
            connection_properties: str | dict | None = None,
            audit_properties: str | dict | None = None
            ) -> dict:
        """Update a repo. Only provided fields are changed.

        Args:
            repo_name: Repository name.
            description: Updated description.
            connection_properties: Keys to add or change, merged into
                the repo's stored connection_properties. Same keys as
                `create_sc_repo`.
            audit_properties: Merged the same way. 'redact_comments'
                "*" redacts SQL comments; "" keeps them.
        """
        settings = get_settings()
        data = {}
        if description is not None:
            data["description"] = description
        if connection_properties is not None:
            data["connection_properties"] = _parse_dict(
                connection_properties)
        if audit_properties is not None:
            data["audit_properties"] = _parse_dict(audit_properties)
        response = await sidecar_config.update_repo(
                settings.auth, repo_name, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def disconnect_sc_repo(repo_name: str) -> dict:
        """Disconnect a repository from ALTR. Must have no users or bindings.

        Args:
            repo_name: Repository name.
        """
        settings = get_settings()
        response = await sidecar_config.delete_repo(
            settings.auth, repo_name)
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
                settings.auth, repo_name, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_sc_repo_user(
            repo_name: str,
            username: str,
            aws_secrets_manager: str | dict | None = None,
            azure_key_vault: str | dict | None = None,
            environment_variable: str | dict | None = None,
            secret_file: str | dict | None = None
            ) -> dict:
        """Create a repo user with credential reference.

        Provide exactly one credential source.

        Args:
            repo_name: Repository name.
            username: Database username.
            aws_secrets_manager: Dict with 'secrets_path' and optional
                'iam_role'. S3 and FILESYSTEM repos also accept
                'iam_role' alone.
            azure_key_vault: Dict with 'key_vault_uri' and 'secret_name'.
            environment_variable: Dict with 'variable_name', the OS
                environment variable holding the secret.
            secret_file: Dict with 'path', a file name (no directories)
                read from /altr/secrets/.
        """
        settings = get_settings()
        data = {"username": username}
        _add_credential(
            data, aws_secrets_manager, azure_key_vault,
            environment_variable, secret_file)
        response = await sidecar_config.create_repo_user(
                settings.auth, repo_name, data)
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
                settings.auth, repo_name, username)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_sc_repo_user(
            repo_name: str,
            username: str,
            aws_secrets_manager: str | dict | None = None,
            azure_key_vault: str | dict | None = None,
            environment_variable: str | dict | None = None,
            secret_file: str | dict | None = None
            ) -> dict:
        """Change a repo user's credential reference.

        Provide exactly one credential source, shaped as in
        `create_sc_repo_user`. A new source type clears the old one.
        An aws_secrets_manager update changes only the keys sent, so a
        stored 'iam_role' stays unless replaced.

        Args:
            repo_name: Repository name.
            username: Database username.
            aws_secrets_manager: AWS Secrets Manager config.
            azure_key_vault: Azure Key Vault config.
            environment_variable: Environment variable config.
            secret_file: Secret file config.
        """
        settings = get_settings()
        data = {}
        _add_credential(
            data, aws_secrets_manager, azure_key_vault,
            environment_variable, secret_file)
        response = await sidecar_config.update_repo_user(
                settings.auth, repo_name, username, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def disconnect_sc_repo_user(repo_name: str, username: str) -> dict:
        """Disconnect a repo user from ALTR.

        Args:
            repo_name: Repository name.
            username: Database username to disconnect.
        """
        settings = get_settings()
        response = await sidecar_config.delete_repo_user(
                settings.auth, repo_name, username)
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
                    settings.auth, repo_name, params)
        else:
            response = await sidecar_config.list_service_users(
                    settings.auth, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_sc_service_user(
            repo_name: str,
            username: str,
            resource: str,
            aws_secrets_manager: str | dict | None = None,
            azure_key_vault: str | dict | None = None,
            environment_variable: str | dict | None = None,
            secret_file: str | dict | None = None
            ) -> dict:
        """Create a service user: the account an agent signs in as.

        Provide exactly one credential source, shaped as in
        `create_sc_repo_user`.

        Args:
            repo_name: Repository name.
            username: Service user name: lowercase letters, digits and
                underscores, max 32 chars.
            resource: The database the credential connects to: the
                Oracle service name; the MySQL, MSSQL, Postgres or
                Snowflake database; the Databricks catalog; the
                MongoDB database or Cassandra keyspace ("*" for all,
                classifier tasks only).
            aws_secrets_manager: AWS Secrets Manager config.
            azure_key_vault: Azure Key Vault config.
            environment_variable: Environment variable config.
            secret_file: Secret file config.
        """
        settings = get_settings()
        data = {"username": username, "resource": resource}
        _add_credential(
            data, aws_secrets_manager, azure_key_vault,
            environment_variable, secret_file)
        response = await sidecar_config.create_service_user(
                settings.auth, repo_name, data)
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
                settings.auth, repo_name, username)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_sc_service_user(
            repo_name: str,
            username: str,
            resource: str | None = None,
            aws_secrets_manager: str | dict | None = None,
            azure_key_vault: str | dict | None = None,
            environment_variable: str | dict | None = None,
            secret_file: str | dict | None = None
            ) -> dict:
        """Update a service user. Only provided fields are changed.

        Give at most one credential source. A new source type clears
        the old one. An aws_secrets_manager update changes only the
        keys sent, so a stored 'iam_role' stays unless replaced.

        Args:
            repo_name: Repository name.
            username: Service user name.
            resource: Updated resource (see `create_sc_service_user`).
            aws_secrets_manager: AWS Secrets Manager config.
            azure_key_vault: Azure Key Vault config.
            environment_variable: Environment variable config.
            secret_file: Secret file config.
        """
        settings = get_settings()
        data = {}
        if resource is not None:
            data["resource"] = resource
        _add_credential(
            data, aws_secrets_manager, azure_key_vault,
            environment_variable, secret_file)
        response = await sidecar_config.update_service_user(
                settings.auth, repo_name, username, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def disconnect_sc_service_user(repo_name: str, username: str) -> dict:
        """Disconnect a service user from ALTR.

        Args:
            repo_name: Repository name.
            username: Service user name to disconnect.
        """
        settings = get_settings()
        response = await sidecar_config.delete_service_user(
                settings.auth, repo_name, username)
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
            settings.auth, params)
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
            settings.auth, data)
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
            settings.auth, sidecar_id)
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
                settings.auth, sidecar_id, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def disconnect_sc_sidecar(sidecar_id: str) -> dict:
        """Disconnect a sidecar from ALTR. Must have no listeners.

        Args:
            sidecar_id: Sidecar UUID.
        """
        settings = get_settings()
        response = await sidecar_config.delete_sidecar(
            settings.auth, sidecar_id)
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
                settings.auth, sidecar_id, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def register_sc_sidecar_listener(
            sidecar_id: str,
            port: int,
            database_type: str,
            advertised_version: str
            ) -> dict:
        """Register a listener port on a sidecar.

        Args:
            sidecar_id: Sidecar UUID.
            port: Port number to listen on.
            database_type: "Oracle", "MSSQL", "MySQL", "Postgres",
                "MongoDB" or "Cassandra".
            advertised_version: Database version string the sidecar
                advertises to clients (max 128 chars).
        """
        settings = get_settings()
        data = {
            "port": port,
            "database_type": database_type,
            "advertised_version": advertised_version,
        }
        response = await sidecar_config.register_sidecar_listener(
                settings.auth, sidecar_id, data)
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
                settings.auth, sidecar_id, port)
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
                settings.auth, sidecar_id, params)
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
                settings.auth, repo_name, params)
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
                settings.auth, sidecar_id, port, repo_name)
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
                settings.auth, sidecar_id, port, repo_name)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def disconnect_sc_sidecar_binding(
            sidecar_id: str, port: int, repo_name: str) -> dict:
        """Remove a repo binding from a sidecar listener port.

        Args:
            sidecar_id: Sidecar UUID.
            port: Listener port number.
            repo_name: Repository name to unbind.
        """
        settings = get_settings()
        response = await sidecar_config.delete_sidecar_binding(
                settings.auth, sidecar_id, port, repo_name)
        return {"success": True, "data": response, "error": None}
