import re
import urllib.parse

from fastmcp import FastMCP
from altr_mcp.utils.logging import log_tool
from altr_mcp.settings import get_settings
from altr_mcp.utils import access_management, sidecar_config

ACCESS = {"read": ["read"], "write": ["write"], "read_write": ["read", "write"]}
SNOWFLAKE_OBJECT_LEVELS = ["database", "schema", "table", "view"]
WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

# Repository type -> (database_type, database_type_name, levels from the top
# down). The levels are the object types an OLTP rule can target there.
OLTP_DATABASES = {
    "oracle": (4, "oracle", ["database", "schema", "table", "column"]),
    "mssql": (1, "mssql", ["database", "schema", "table", "column"]),
    "postgres": (2, "postgres", ["database", "schema", "table", "column"]),
    "mysql": (3, "mysql", ["database", "table", "column"]),
    "mongodb": (23, "mongodb", ["database", "collection", "field"]),
    "cassandra": (6, "cassandra", ["keyspace", "table", "column"]),
}
OLTP_ACCESS = ["create", "read", "update", "delete"]


def _failed(response) -> bool:
    return isinstance(response, dict) and response.get("success") is False


def _failure(response: dict) -> str:
    if "body" in response:
        body = (response.get("body") or "").strip()[:200]
        return f"HTTP {response.get('status_code')}" + (f": {body}" if body else "")
    return str(response.get("message"))


def _names(value, label: str) -> list[str]:
    names = [value] if isinstance(value, str) else list(value or [])
    names = [n.strip() for n in names if isinstance(n, str) and n.strip()]
    if not names:
        raise ValueError(f"{label} needs at least one name.")
    return names


def _snowflake_rule(roles, access, object_type, names, database, schema,
                    tag_check_against, tag_database, tag_schema, tag_names,
                    tag_values) -> dict:
    """One rule in the shape the console's Snowflake rule editor builds."""
    if access not in ACCESS:
        raise ValueError('access must be "read", "write" or "read_write".')
    rule = {
        "access": [{"name": name} for name in ACCESS[access]],
        "actors": [{"type": "role", "condition": "equals",
                    "identifiers": _names(roles, "roles")}],
    }
    if (object_type is None) == (tag_names is None):
        raise ValueError(
            "Target objects by name (object_type and names) or by tag "
            "(tag_names), not both.")
    if object_type is not None:
        if object_type not in SNOWFLAKE_OBJECT_LEVELS:
            raise ValueError(
                'object_type must be "database", "schema", "table" or "view".')
        parents = SNOWFLAKE_OBJECT_LEVELS[:min(
            SNOWFLAKE_OBJECT_LEVELS.index(object_type), 2)]
        given = {"database": database, "schema": schema}
        for level in parents:
            if not given[level]:
                raise ValueError(f"A {object_type} target needs {level}.")
        rule["objects"] = [{
            "type": object_type,
            "condition": "fully_qualified",
            "fully_qualified_identifiers": [
                {**{level: given[level] for level in parents}, object_type: name}
                for name in _names(names, "names")],
        }]
        return rule
    if tag_check_against not in SNOWFLAKE_OBJECT_LEVELS:
        raise ValueError('tag_check_against must be "database", "schema", '
                         '"table" or "view".')
    if not tag_database or not tag_schema:
        raise ValueError("A tag target needs tag_database and tag_schema.")
    tag_names = _names(tag_names, "tag_names")
    where = {"database": tag_database, "schema": tag_schema}
    if tag_values is None:
        tagged_with = [{**where, "name": name} for name in tag_names]
    elif len(tag_names) != 1:
        raise ValueError("tag_values needs exactly one tag name.")
    else:
        tagged_with = [{**where, "name": tag_names[0], "value": value}
                       for value in _names(tag_values, "tag_values")]
    rule["tagged_objects"] = [{
        "check_against": [f"{tag_check_against}s"],
        "tagged_with": tagged_with,
        "tag_condition": "or",
    }]
    return rule


def _policy_maintenance(refresh, refresh_time, refresh_day, refresh_week):
    """The console's refresh schedules as an AWS cron in UTC; None for none."""
    if refresh == "none":
        return None
    if refresh not in ("daily", "weekly", "monthly"):
        raise ValueError(
            'refresh must be "none", "daily", "weekly" or "monthly".')
    match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", refresh_time or "")
    if not match:
        raise ValueError('refresh_time must be "HH:MM" in UTC, e.g. "02:30".')
    hour, minute = int(match.group(1)), int(match.group(2))
    if refresh == "daily":
        return {"rate": "cron", "value": f"{minute} {hour} ? * * *"}
    day = (refresh_day or "").strip().upper()[:3]
    if day not in WEEKDAYS:
        raise ValueError(f"A {refresh} refresh needs refresh_day, MON to SUN.")
    if refresh == "weekly":
        return {"rate": "cron", "value": f"{minute} {hour} ? * {day} *"}
    if refresh_week not in (1, 2, 3, 4):
        raise ValueError("A monthly refresh needs refresh_week, 1 to 4.")
    return {"rate": "cron", "value": f"{minute} {hour} ? * {day}#{refresh_week} *"}


def _oltp_rules(rules, levels: list[str]) -> list[dict]:
    """Rules in the shape the console's OLTP rule editor builds."""
    if isinstance(rules, str):
        import json
        rules = json.loads(rules)
    if not isinstance(rules, list) or not rules:
        raise ValueError("rules needs at least one rule.")
    built = []
    for number, rule in enumerate(rules, 1):
        if not isinstance(rule, dict):
            raise ValueError(f"Rule {number} must be an object.")
        access = rule.get("access", "read")
        if access not in OLTP_ACCESS:
            raise ValueError(f"Rule {number}: access must be one of "
                             f"{', '.join(OLTP_ACCESS)}.")
        if ("users" in rule) == ("groups" in rule):
            raise ValueError(f"Rule {number} needs users or groups, not both.")
        actor_type = "idp_user" if "users" in rule else "idp_group"
        actors = _names(rule.get("users", rule.get("groups")),
                        f"Rule {number} users or groups")
        object_type = rule.get("object_type")
        if object_type not in levels:
            raise ValueError(f"Rule {number}: object_type must be one of "
                             f"{', '.join(levels)} for this repository.")
        path = levels[:levels.index(object_type) + 1]
        for level in path[:-1]:
            if not isinstance(rule.get(level), str) or not rule[level].strip():
                raise ValueError(
                    f'Rule {number} needs {level}: a name, or "*" for any.')
        parents = {level: {"wildcard": True} if rule[level] == "*"
                   else {"name": rule[level]} for level in path[:-1]}
        leaves = rule.get(object_type)
        if leaves == "*":
            identifiers = [{**parents, object_type: {"wildcard": True}}]
        else:
            identifiers = [{**parents, object_type: {"name": name}} for name
                           in _names(leaves, f"Rule {number} {object_type}")]
        built.append({
            "type": access,
            "actors": [{"type": actor_type, "condition": "equals",
                        "identifiers": actors}],
            "objects": [{"type": object_type, "identifiers": identifiers}],
        })
    return built


async def _oltp_database(repo_name: str) -> tuple:
    repo = await sidecar_config.get_repo(get_settings().auth, repo_name)
    if _failed(repo) and repo.get("status_code") != 404:
        raise ValueError(f"Could not read repository {repo_name}: {_failure(repo)}")
    repo = repo.get("data", repo) if isinstance(repo, dict) else {}
    if not repo.get("type"):
        raise ValueError(f"No repository named {repo_name}.")
    kind = repo["type"].lower()
    if kind not in OLTP_DATABASES:
        raise ValueError(
            f"{repo_name} is a {repo['type']} repository. Access management "
            "policies cover Oracle, MSSQL, Postgres, MySQL, MongoDB and "
            "Cassandra repositories.")
    return OLTP_DATABASES[kind]


async def _policy(policy_id: str, prefix: str) -> dict:
    """The stored policy, checked to be the expected kind."""
    if not urllib.parse.unquote(policy_id).startswith(prefix):
        raise ValueError(f"{policy_id} is not an access management policy of "
                         f"this kind; its ID must start with {prefix}.")
    response = await access_management.get_policy(get_settings().auth, policy_id)
    if _failed(response):
        raise ValueError(f"Could not read policy {policy_id}: {_failure(response)}")
    return response.get("data", response)


def _current_rules(policy: dict) -> list:
    """The rules the console's editor starts from."""
    for key in ("rules_pending", "rules_failed", "rules_applied", "rules"):
        if policy.get(key):
            return policy[key]
    return []


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    @log_tool
    async def create_snowflake_access_policy(
            policy_name: str,
            connection_id: int,
            roles: str | list[str],
            refresh: str,
            access: str = "read",
            object_type: str | None = None,
            names: str | list[str] | None = None,
            database: str | None = None,
            schema: str | None = None,
            tag_check_against: str | None = None,
            tag_database: str | None = None,
            tag_schema: str | None = None,
            tag_names: str | list[str] | None = None,
            tag_values: str | list[str] | None = None,
            refresh_time: str | None = None,
            refresh_day: str | None = None,
            refresh_week: int | None = None
            ) -> dict:
        """Create an access management policy for a Snowflake database, as
        the console does: grant one set of roles read and/or write access to
        named objects or to objects carrying a tag. ALTR applies the grants
        asynchronously and re-applies them on the refresh schedule.

        Target either by name (object_type and names) or by tag (tag_names):
        - By name: object_type "database" with database names; "schema" with
          `database` and schema names; "table" or "view" with `database`,
          `schema` and table or view names.
        - By tag: objects of kind tag_check_against carrying any of tag_names
          (the tag lives in tag_database.tag_schema), or carrying one tag
          name with any of tag_values.

        Args:
            policy_name: Name for the policy (1-255 chars).
            connection_id: Snowflake connection ID (from `get_databases`).
            roles: Snowflake roles that get access.
            refresh: How often ALTR re-applies the grants: "none", "daily",
                "weekly" or "monthly".
            access: "read" (the default), "write" or "read_write".
            object_type: "database", "schema", "table" or "view".
            names: Names of the objects of object_type.
            database: Database holding the schemas, tables or views.
            schema: Schema holding the tables or views.
            tag_check_against: "database", "schema", "table" or "view".
            tag_database: Database the tag is defined in.
            tag_schema: Schema the tag is defined in.
            tag_names: Tag names; with tag_values, exactly one.
            tag_values: Tag values to match on the one tag name.
            refresh_time: "HH:MM" in UTC; needed unless refresh is "none".
            refresh_day: Day for a weekly or monthly refresh, MON to SUN.
            refresh_week: Week of the month for a monthly refresh, 1 to 4.
        """
        rule = _snowflake_rule(roles, access, object_type, names, database,
                               schema, tag_check_against, tag_database,
                               tag_schema, tag_names, tag_values)
        data = {
            "policy_name": policy_name,
            "connection_ids": [connection_id],
            "rules": [rule],
        }
        maintenance = _policy_maintenance(refresh, refresh_time, refresh_day,
                                          refresh_week)
        if maintenance:
            data["policy_maintenance"] = maintenance

        settings = get_settings()
        response = await access_management.create_snowflake_access_policy(
                settings.auth, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_snowflake_access_policy(
            policy_id: str,
            policy_name: str | None = None,
            roles: str | list[str] | None = None,
            access: str | None = None,
            object_type: str | None = None,
            names: str | list[str] | None = None,
            database: str | None = None,
            schema: str | None = None,
            tag_check_against: str | None = None,
            tag_database: str | None = None,
            tag_schema: str | None = None,
            tag_names: str | list[str] | None = None,
            tag_values: str | list[str] | None = None,
            refresh: str | None = None,
            refresh_time: str | None = None,
            refresh_day: str | None = None,
            refresh_week: int | None = None
            ) -> dict:
        """Update a Snowflake access management policy, as the console's
        editor does. Anything left out keeps its current value: the name,
        the rule and the refresh schedule. Saving re-applies the grants, so
        there is no need to call `trigger_access_policy_check` afterwards.

        To change the rule, pass all of it: roles, access and a target, in
        the form `create_snowflake_access_policy` takes. A policy whose rule
        the console can't edit keeps that rule; only its name and schedule
        can change. A policy still applying a previous change can't be
        updated until it finishes.

        Args:
            policy_id: Policy ID, starting GRANT#. Do not URL-encode.
            policy_name: New name (1-255 chars).
            roles: Snowflake roles that get access.
            access: "read", "write" or "read_write".
            object_type: "database", "schema", "table" or "view".
            names: Names of the objects of object_type.
            database: Database holding the schemas, tables or views.
            schema: Schema holding the tables or views.
            tag_check_against: "database", "schema", "table" or "view".
            tag_database: Database the tag is defined in.
            tag_schema: Schema the tag is defined in.
            tag_names: Tag names; with tag_values, exactly one.
            tag_values: Tag values to match on the one tag name.
            refresh: "none" to remove the schedule, or "daily", "weekly" or
                "monthly" to replace it.
            refresh_time: "HH:MM" in UTC.
            refresh_day: Day for a weekly or monthly refresh, MON to SUN.
            refresh_week: Week of the month for a monthly refresh, 1 to 4.
        """
        policy = await _policy(policy_id, "GRANT#")
        new_rule = [roles, access, object_type, names, database, schema,
                    tag_check_against, tag_database, tag_schema, tag_names,
                    tag_values]
        if any(value is not None for value in new_rule):
            new_rule[1] = access or "read"
            rules = [_snowflake_rule(*new_rule)]
        else:
            rules = _current_rules(policy)
        data = {
            "policy_name": policy_name or policy.get("policy_name"),
            "rules": rules,
        }
        if refresh is None:
            maintenance = policy.get("policy_maintenance")
        else:
            maintenance = _policy_maintenance(refresh, refresh_time,
                                              refresh_day, refresh_week)
        # The API removes the schedule when the update leaves it out.
        if maintenance:
            data["policy_maintenance"] = maintenance

        settings = get_settings()
        response = await access_management.update_snowflake_access_policy(
                settings.auth, policy_id, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_oltp_access_policy(
            policy_name: str,
            repo_name: str,
            rules: str | list[dict]
            ) -> dict:
        """Create an access management policy for a database repository, as
        the console does: which ALTR users or IdP groups may create, read,
        update or delete which objects through the sidecar. Supports Oracle,
        MSSQL, Postgres, MySQL, MongoDB and Cassandra repositories.

        Each rule grants one kind of access to one set of users or groups on
        objects of one type:
        - access: "create", "read" (the default), "update" or "delete".
        - users (ALTR usernames, which are emails) or groups (IdP group
          names), as a list.
        - object_type: one level of the repository's hierarchy. Oracle,
          MSSQL and Postgres: database, schema, table, column. MySQL:
          database, table, column. MongoDB: database, collection, field.
          Cassandra: keyspace, table, column.
        - One key per level above object_type, each a name or "*" for any,
          and the object_type key itself: a list of names, or "*" for any.

        Example: {"access": "read", "users": ["ana@example.com"],
        "object_type": "column", "database": "sales", "schema": "*",
        "table": "orders", "column": ["email", "phone"]}

        Args:
            policy_name: Name for the policy (1-255 chars).
            repo_name: Repository name (from `list_sc_repos`).
            rules: List of rules as above, or a JSON string encoding one.
        """
        database_type, database_type_name, levels = await _oltp_database(
            repo_name)
        data = {
            "policy_name": policy_name,
            "repo_name": repo_name,
            "database_type": database_type,
            "database_type_name": database_type_name,
            "case_sensitivity": "case_sensitive",
            "rules": _oltp_rules(rules, levels),
        }

        settings = get_settings()
        response = await access_management.create_oltp_access_policy(
            settings.auth, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def update_oltp_access_policy(
            policy_id: str,
            policy_name: str | None = None,
            rules: str | list[dict] | None = None
            ) -> dict:
        """Update a database repository's access management policy, as the
        console's editor does. Anything left out keeps its current value.
        The repository can't change.

        Args:
            policy_id: Policy ID, starting OLTP#. Do not URL-encode.
            policy_name: New name (1-255 chars).
            rules: The complete new list of rules, in the form
                `create_oltp_access_policy` takes. Replaces every rule.
        """
        policy = await _policy(policy_id, "OLTP#")
        name = (policy.get("database_type_name") or "").lower()
        if name not in OLTP_DATABASES:
            raise ValueError(f"Policy {policy_id} has no supported database type.")
        database_type, database_type_name, levels = OLTP_DATABASES[name]
        data = {
            "policy_name": policy_name or policy.get("policy_name"),
            "database_type": database_type,
            "database_type_name": database_type_name,
            "case_sensitivity": policy.get("case_sensitivity", "case_sensitive"),
            "rules": (_oltp_rules(rules, levels) if rules is not None
                      else _current_rules(policy)),
        }
        # The API clears a description the update leaves out.
        if policy.get("description"):
            data["description"] = policy["description"]

        settings = get_settings()
        response = await access_management.update_oltp_access_policy(
            settings.auth, policy_id, data)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def trigger_access_policy_check(policy_id: str) -> dict:
        """Re-apply a Snowflake access management policy's grants now, as
        the console's Refresh button does, instead of waiting for its
        schedule. The run is queued and the policy shows as pending until it
        finishes. Database repository policies don't need it.

        Args:
            policy_id: Policy ID, starting GRANT#. Do not URL-encode.
        """
        if not urllib.parse.unquote(policy_id).startswith("GRANT#"):
            raise ValueError("Only Snowflake access management policies "
                             "(IDs starting GRANT#) can be refreshed.")
        settings = get_settings()
        response = await access_management.trigger_access_policy_check(
                settings.auth, policy_id)
        return {"success": True, "data": response, "error": None}
