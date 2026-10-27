"""Build classification job requests the way the ALTR console's scan wizard does.

Every job the console starts is an ALTR Native run: a collection, a processing
location, sampling, an optional scope and exclusions. These helpers produce
the same request fields, so a job started here matches one started there.
"""

CONDITION_TYPES = ["ROW_DATA", "METADATA", "COLUMN_LOCATION", "GDLP", "CONTENT_TYPE",
                   "DATA_LENGTH", "COLUMN_SIZE", "AMAZON_COMPREHEND", "ENTROPY"]
SNOWFLAKE_CONDITION_TYPES = CONDITION_TYPES + ["SNOWFLAKE_NATIVE"]

ALTR_NATIVE = 5
DEFAULT_SAMPLE_SIZE = {"ROWS": 1000, "PERCENT": 5}
MAX_EXCLUSIONS = 100
MAX_SCOPE_PATHS = 50
MAX_PATH_EXCLUSIONS = 100
MAX_NAME_LENGTH = 255
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_FILES = 2147483647

# Vendors whose databases hold tables directly. Their scopes repeat the
# database in `schema`, which is how the agent names the namespace.
TWO_LEVEL_REPO_TYPES = {"mysql", "mongodb", "cassandra"}
FILE_REPO_TYPES = {"s3", "filesystem"}
RELATIONAL_REPO_TYPES = {"oracle", "mssql", "postgres"} | TWO_LEVEL_REPO_TYPES
METADATA_MAP_POLICIES = ("hashed", "plaintext", "none")
METADATA_MAP_FORMATS = ("csv", "json", "xml", "html", "yaml")


def sampling(sample_type: str, sample_size: int | None) -> dict:
    """sample_type and sample_size, with the console's defaults and limits."""
    sample_type = (sample_type or "ROWS").upper()
    if sample_type not in DEFAULT_SAMPLE_SIZE:
        raise ValueError('sample_type must be "ROWS" or "PERCENT".')
    if sample_size is None:
        sample_size = DEFAULT_SAMPLE_SIZE[sample_type]
    if isinstance(sample_size, bool) or not isinstance(sample_size, int) or sample_size < 1:
        raise ValueError("sample_size must be a whole number greater than 0.")
    if sample_type == "PERCENT" and sample_size > 100:
        raise ValueError("sample_size must be between 1 and 100 for PERCENT sampling.")
    return {"sample_size": sample_size, "sample_type": sample_type}


def _name(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if len(value) > MAX_NAME_LENGTH or "#" in value:
        raise ValueError(f'{field} must be {MAX_NAME_LENGTH} characters or fewer, without "#".')
    return value


def _wire(parts: list[str], two_level: bool) -> dict:
    """{level, database, schema?, table?} for a path from the database down."""
    if two_level:
        database, table = (parts + [None])[:2]
        scope = {"level": "TABLE" if table else "DATABASE", "database": database}
        if table:
            scope.update(schema=database, table=table)
        return scope
    level = ("DATABASE", "SCHEMA", "TABLE")[len(parts) - 1]
    return dict(zip(("database", "schema", "table"), parts), level=level)


def object_scope(database: str | None, schema: str | None, table: str | None,
                 two_level: bool = False) -> list[str] | None:
    """The scope path from the database down, or None for an unscoped scan."""
    database = _name(database, "database")
    schema = _name(schema, "schema")
    table = _name(table, "table")
    if two_level and schema:
        raise ValueError("This source has no schema level; give the database and table only.")
    if not database:
        if schema or table:
            raise ValueError("A schema or table scope needs its database.")
        return None
    if table and not two_level and not schema:
        raise ValueError("A table scope needs its schema.")
    return [p for p in (database, schema, table) if p]


def scope_and_exclusions(parts: list[str] | None, exclude, two_level: bool = False) -> dict:
    """`scope` and `exclusions` fields. Exclusions are paths relative to the scope,
    such as "archive" or "archive.orders", as the console collects them."""
    if isinstance(exclude, str):
        exclude = [exclude]
    exclude = list(exclude or [])
    if exclude and not parts:
        raise ValueError("Exclusions need a scope: name at least the database.")
    if not parts:
        return {}
    if len(exclude) > MAX_EXCLUSIONS:
        raise ValueError(f"At most {MAX_EXCLUSIONS} exclusions.")
    depth = 2 if two_level else 3
    seen, exclusions = set(), []
    for path in exclude:
        segments = [s.strip() for s in str(path).split(".") if s.strip()]
        if not segments:
            continue
        for segment in segments:
            _name(segment, "exclusion")
        full = parts + segments
        if len(full) > depth:
            raise ValueError(f'"{path}" goes deeper than a table under this scope.')
        key = ".".join(segments).lower()
        if key not in seen:
            seen.add(key)
            exclusions.append(_wire(full, two_level))
    fields = {"scope": _wire(parts, two_level)}
    if exclusions:
        fields["exclusions"] = exclusions
    return fields


def _paths(values, noun: str, maximum: int) -> list[str]:
    if isinstance(values, str):
        values = [values]
    paths = []
    for value in values or []:
        path = str(value).strip().rstrip("/")
        if not path:
            raise ValueError(f"A {noun} can't be empty.")
        if path.startswith("/"):
            raise ValueError(
                f'A {noun} is relative to the repository root; remove the leading "/".')
        if "\\" in path:
            raise ValueError('Use "/" to separate path segments.')
        if "#" in path or len(path) > MAX_NAME_LENGTH:
            raise ValueError(
                f'A {noun} must be {MAX_NAME_LENGTH} characters or fewer, without "#".')
        segments = path.split("/")
        if "" in segments or "." in segments or ".." in segments:
            raise ValueError(f'A {noun} must not have empty, "." or ".." segments.')
        if path in paths:
            raise ValueError(f"{path} is listed twice.")
        paths.append(path)
    if len(paths) > maximum:
        raise ValueError(f"At most {maximum} {noun}s.")
    return paths


def path_scope_and_exclusions(paths, exclude_paths) -> dict:
    """PATH-level `scope` and `exclusions` for a file source."""
    fields = {}
    scope_paths = _paths(paths, "path", MAX_SCOPE_PATHS)
    if scope_paths:
        fields["scope"] = {"level": "PATH", "paths": scope_paths}
    excluded = _paths(exclude_paths, "excluded path", MAX_PATH_EXCLUSIONS)
    if excluded:
        fields["exclusions"] = [{"level": "PATH", "paths": excluded}]
    return fields


def file_options(is_s3: bool, *, content_classification: bool, full_file_scan: bool,
                 include_glob: str | None, exclude_glob: str | None,
                 max_files: int | None, max_file_bytes: int | None,
                 scan_mode: str | None, glue_crawler: str | None,
                 glue_start_crawler: bool, sniff_bytes: bool) -> dict:
    """`file_options` as the console sends it: S3-only fields only for S3."""
    options = {}
    if is_s3:
        scan_mode = (scan_mode or "CRAWL").upper()
        if scan_mode not in ("CRAWL", "GLUE"):
            raise ValueError('scan_mode must be "CRAWL" or "GLUE".')
        options["scan_mode"] = scan_mode
        if scan_mode == "GLUE":
            if glue_crawler and glue_crawler.strip():
                options["glue_crawler"] = glue_crawler.strip()
            options["glue_start_crawler"] = bool(glue_start_crawler)
        options["sniff_bytes"] = bool(sniff_bytes)
    elif scan_mode or glue_crawler or glue_start_crawler:
        raise ValueError("scan_mode and the Glue options are for S3 repositories only.")
    options["content_classification"] = bool(content_classification)
    options["full_file_scan"] = bool(full_file_scan)
    for key, glob in (("include_glob", include_glob), ("exclude_glob", exclude_glob)):
        if glob and glob.strip():
            options[key] = glob.strip()
    for key, value, upper in (("max_files", max_files, MAX_FILES),
                              ("max_file_bytes", max_file_bytes, MAX_FILE_BYTES)):
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= upper:
                raise ValueError(f"{key} must be a whole number from 1 to {upper}.")
            options[key] = value
    return options


def metadata_map(default: str = "hashed", by_format: dict | None = None) -> dict | None:
    """`metadata_map`, or None when it is the untouched default (hashed, no overrides)."""
    default = (default or "hashed").lower()
    if default not in METADATA_MAP_POLICIES:
        raise ValueError(f"metadata_map must be one of {', '.join(METADATA_MAP_POLICIES)}.")
    overrides = {}
    for fmt, policy in (by_format or {}).items():
        fmt, policy = str(fmt).lower(), str(policy).lower()
        if fmt not in METADATA_MAP_FORMATS:
            raise ValueError(f"metadata_map_by_format keys are {', '.join(METADATA_MAP_FORMATS)}.")
        if policy not in METADATA_MAP_POLICIES:
            raise ValueError(f"metadata_map values are {', '.join(METADATA_MAP_POLICIES)}.")
        if policy != default:
            overrides[fmt] = policy
    if default == "hashed" and not overrides:
        return None
    result = {"default": default}
    if overrides:
        result["by_format"] = overrides
    return result
