import httpx
from dotenv import load_dotenv
import os


load_dotenv()


def _add_column(TAG_NAME: str, values: dict):
    sql_statements = ""
    for value in values.keys():
        for column in values[value]['columns']:
            sql_statements += (f"""
  ALTER TABLE {values[value]['table']}
  MODIFY COLUMN {column}
  SET TAG {TAG_NAME} = '{value}';
            """)

    return sql_statements


async def create_snowflake_tags(
        allowed_values_list: dict, DATABASE: str, SCHEMA: str, TAG_NAME: str):
    URL = (
        f"https://{os.getenv('SNOWFLAKE_ACCOUNT').upper().strip()}"
        f".snowflakecomputing.com/api/v2/statements"
    )
    PAT = os.getenv('SNOWFLAKE_PAT', '').strip()

    allowed_values_sql = ', '.join(
        f"'{value}'" for value in allowed_values_list.keys()
    )

    # Count total number of columns being tagged
    total_columns = sum(len(value['columns']) for
                        value in allowed_values_list.values())

    # 3 base statements
    # (USE DATABASE, USE SCHEMA, CREATE TAG) + ALTER TABLE statements
    statment_count = 3 + total_columns
    sql_query = f"""USE DATABASE {DATABASE};
USE SCHEMA {SCHEMA};
CREATE TAG {TAG_NAME}
  ALLOWED_VALUES {allowed_values_sql};
{_add_column(TAG_NAME, allowed_values_list)}"""
    print(sql_query)
    headers = {
        "Authorization": f"Bearer {PAT}",
        "Content-Type": "application/json"
    }

    payload = {
        "statement": sql_query,
        "parameters": {
            "MULTI_STATEMENT_COUNT": statment_count,
        },
        "role": os.getenv('SNOWFLAKE_ROLE', 'ACCOUNTADMIN'),
        "warehouse": os.getenv('SNOWFLAKE_WAREHOUSE', 'DAILY_XS_WH'),
    }

    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(URL, headers=headers, json=payload)

    if response.status_code == 200:
        return f"{DATABASE}.{SCHEMA}.{TAG_NAME}"
    else:
        return f"Request failed ({response.status_code}): {response.text})"
