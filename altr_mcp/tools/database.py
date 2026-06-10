from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from altr_mcp.settings import get_settings
from altr_mcp.utils import database
from altr_mcp.utils.logging import log_tool


def register(mcp: FastMCP) -> None:

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_databases() -> dict:
        """Discover which Snowflake databases are connected to ALTR.

        Returns connection metadata including database names and IDs. Use
        `get_database_id` to get the numeric ID required
        for classification jobs.
        """
        settings = get_settings()
        databases = await database._get_databases({}, settings.auth)
        return {"success": True, "data": databases, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_database_id(database_name: str) -> dict:
        """Get the ALTR database ID for a database name.

        Required before creating classification jobs. The
        database ID is a numeric identifier that ALTR uses
        internally to reference your Snowflake database.

        Typical workflow: After identifying your database with `get_databases`,
        call this to get the ID needed for `create_job`.

        Args:
            database_name: Friendly database name as shown
                in the ALTR UI.
        """
        settings = get_settings()
        response = await database._get_database_id(
            database_name, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_service_users() -> dict:
        """List Snowflake service users available for database connections.

        Returns service user IDs needed for `create_database` when using
        keypair authentication (the recommended approach for Snowflake).
        """
        settings = get_settings()
        response = await database._get_service_users(settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_database(
            friendly_database_name: str,
            database_type: str,
            database_name: str,
            service_user_id: str | None = None,
            database_username: str | None = None,
            database_password: str | None = None,
            hostname: str | None = None,
            database_port: int | None = None
            ) -> dict:
        """Connect a new data source to the ALTR platform.

        Supports two authentication modes:

        1. **Service user (keypair auth — recommended for Snowflake):**
           Provide `service_user_id` from `get_service_users`. No password,
           hostname, or port needed.

        2. **Password auth:** Provide `database_username`, `database_password`,
           `hostname`, and `database_port`.

        After creation, use `get_databases` to confirm the connection.

        Args:
            friendly_database_name: Display name for the database in ALTR.
            database_type: Database type (e.g. "snowflake_external_functions").
            database_name: Actual database name (e.g. "MY_DATABASE_NAME").
            service_user_id: Service user ID from `get_service_users`
                for keypair auth. Preferred for Snowflake connections.
            database_username: Username (password auth only).
            database_password: Password (password auth only).
            hostname: Database server hostname (password auth only).
            database_port: Database server port (password auth only).
        """
        data = {
            "friendlyDatabaseName": friendly_database_name,
            "databaseType": database_type,
            "databaseName": database_name,
        }
        if service_user_id is not None:
            data["serviceUserID"] = service_user_id
        else:
            if database_username is not None:
                data["databaseUsername"] = database_username
            if database_password is not None:
                data["databasePassword"] = database_password
            if hostname is not None:
                data["hostname"] = hostname
            if database_port is not None:
                data["databasePort"] = database_port

        settings = get_settings()
        response = await database._create_database(data, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_databricks_database(
            friendly_database_name: str,
            database_name: str,
            hostname: str,
            database_username: str | None = None,
            database_password: str | None = None,
            service_user_id: str | None = None
            ) -> dict:
        """Connect a Databricks workspace to the ALTR platform.

        Supports two authentication modes:

        1. **Service user (token auth — recommended):**
           Provide `service_user_id` from `get_service_users`.

        2. **Password auth:** Provide `database_username` and
           `database_password`.

        After creation, use `get_databases` to confirm the connection.

        Args:
            friendly_database_name: Display name for the database in ALTR.
            database_name: Databricks catalog or workspace name.
            hostname: Databricks workspace URL
                (e.g. "https://adb-1234567890.azuredatabricks.net").
            database_username: Username (password auth only).
            database_password: Password (password auth only).
            service_user_id: Service user ID from `get_service_users`
                for token auth. Preferred.
        """
        data = {
            "friendlyDatabaseName": friendly_database_name,
            "databaseType": "databricks",
            "databaseName": database_name,
            "hostname": hostname,
        }
        if service_user_id is not None:
            data["serviceUserID"] = service_user_id
        else:
            if database_username is not None:
                data["databaseUsername"] = database_username
            if database_password is not None:
                data["databasePassword"] = database_password

        settings = get_settings()
        response = await database._create_database(data, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_database(
            database_id: int,
            friendly_database_name: str | None = None,
            max_number_of_connections: int | None = None,
            max_number_of_batches: int | None = None,
            service_user_id: str | None = None,
            connection_string: str | None = None,
            database_password: str | None = None,
            database_username: str | None = None,
            snowflake_role: str | None = None,
            warehouse_name: str | None = None,
            should_classify: bool | None = None,
            data_usage_history: bool | None = None,
            classification_type: str | None = None,
            reinvoke: bool | None = None
            ) -> dict:
        """Update a database connection's properties.

        Only the fields you provide will be updated; omitted fields
        remain unchanged.

        Args:
            database_id: Numeric ALTR database ID (from `get_databases`).
            friendly_database_name: Updated display name.
            max_number_of_connections: Max concurrent connections.
            max_number_of_batches: Max concurrent batches.
            service_user_id: Service user identifier.
            connection_string: Database connection string.
            database_password: Updated password.
            database_username: Updated username.
            snowflake_role: Snowflake role to use.
            warehouse_name: Snowflake warehouse to use.
            should_classify: Enable/disable classification.
            data_usage_history: Enable/disable data usage history.
            classification_type: Classification type code.
            reinvoke: Trigger reinvocation of the database setup.
        """
        data = {}
        if friendly_database_name is not None:
            data["friendlyDatabaseName"] = friendly_database_name
        if max_number_of_connections is not None:
            data["maxNumberOfConnections"] = max_number_of_connections
        if max_number_of_batches is not None:
            data["maxNumberOfBatches"] = max_number_of_batches
        if service_user_id is not None:
            data["serviceUserID"] = service_user_id
        if connection_string is not None:
            data["connectionString"] = connection_string
        if database_password is not None:
            data["databasePassword"] = database_password
        if database_username is not None:
            data["databaseUsername"] = database_username
        if snowflake_role is not None:
            data["snowflakeRole"] = snowflake_role
        if warehouse_name is not None:
            data["warehouseName"] = warehouse_name
        if should_classify is not None:
            data["shouldClassify"] = should_classify
        if data_usage_history is not None:
            data["dataUsageHistory"] = data_usage_history
        if classification_type is not None:
            data["classificationType"] = classification_type
        if reinvoke is not None:
            data["reinvoke"] = reinvoke

        settings = get_settings()
        response = await database._update_database(
            database_id, data, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def trigger_database_status_sync(database_id: int) -> dict:
        """Trigger a database status sync.

        Sets the database to "in progress" until the status check
        completes. Use `get_databases` afterward to see the updated status.

        Args:
            database_id: Numeric ALTR database ID (from `get_databases`).
        """
        settings = get_settings()
        response = await database._trigger_database_status_sync(
            database_id, settings.auth)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def disconnect_database(
            database_id: int,
            ignore_errors: bool = False
            ) -> dict:
        """Disconnect a data source from ALTR.

        Removes the ALTR connection to the data source. This does not
        affect the underlying database — only the ALTR connection to it.

        Args:
            database_id: Numeric ALTR database ID (from `get_databases`).
            ignore_errors: If true, force disconnection even if cleanup fails.
        """
        settings = get_settings()
        response = await database._delete_database(
            database_id, settings.auth, ignore_errors)
        return {"success": True, "data": response, "error": None}
