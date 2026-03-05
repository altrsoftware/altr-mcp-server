from altr_mcp.utils import api


async def _tag_column(
        params: dict,
        auth,
        database_name: str,
        schema_name: str,
        table_name: str,
        column_name: str,
        tag_name: str,
        tag_value: str
        ) -> dict:
    """Tag a column with a specific tag value in Altr

    Args:
        params: Request parameters
        auth: Authentication credentials
        database_name: Name of the database
        schema_name: Name of the schema
        table_name: Name of the table
        column_name: Name of the column to tag
        tag_name: Name of the tag (e.g., "PII", "SENSITIVE")
        tag_value: Value of the tag to apply to the column

    Returns:
        API response dictionary
    """
    url = "https://api.live.altr.com/v1/dis/classification/v2/tag"
    method = "POST"
    data = {
        "database": database_name,
        "schema": schema_name,
        "table": table_name,
        "column": column_name,
        "tag": tag_name,
        "tagValue": tag_value
    }
    response = await api.request(method, url, auth, params, data)
    return response
