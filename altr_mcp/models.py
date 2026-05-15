from typing import Optional

from pydantic import BaseModel, Field, ValidationError


class TimeRange(BaseModel):
    hour: int
    minute: int


class AccessRateThreshold(BaseModel):
    access_rate_unit: str
    access_rate_limit: int
    action: str


class TimeWindowThreshold(BaseModel):
    day: list[str]
    start_time: TimeRange
    end_time: TimeRange
    timezone: str
    action: str


def validate_access_rate_thresholds(items: list[dict]) -> Optional[str]:
    """Validate a list of access rate threshold dicts.

    Returns None if all items are valid, or a newline-joined string of
    field-level error messages if any items are invalid.
    """
    if items is None:
        return None

    errors = []
    for i, item in enumerate(items):
        try:
            AccessRateThreshold.model_validate(item)
        except ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(p) for p in err["loc"])
                msg = err["msg"]
                errors.append(f"access_rate_thresholds[{i}].{loc}: {msg}")

    return "\n".join(errors) if errors else None


class MaskingRule(BaseModel):
    """Single masking rule for add_rules tool."""
    masking_policy: int = Field(ge=10000, le=10009)
    role: str
    tag_value: str


def validate_masking_rules(items: list[dict]) -> Optional[str]:
    """Validate a list of masking rule dicts.

    Returns None if valid, error string if invalid.
    """
    if not items:
        return "No rules provided"
    errors = []
    for i, item in enumerate(items):
        try:
            MaskingRule.model_validate(item)
        except ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(p) for p in err["loc"])
                errors.append(f"rules[{i}].{loc}: {err['msg']}")
    return "\n".join(errors) if errors else None


class SidecarBinding(BaseModel):
    """Sidecar listener binding parameters."""
    port: int = Field(gt=0, le=65535)
    repo_name: str


def validate_time_window_thresholds(items: list[dict]) -> Optional[str]:
    """Validate a list of time window threshold dicts.

    Returns None if all items are valid, or a newline-joined string of
    field-level error messages if any items are invalid.
    """
    if items is None:
        return None

    errors = []
    for i, item in enumerate(items):
        try:
            TimeWindowThreshold.model_validate(item)
        except ValidationError as exc:
            for err in exc.errors():
                loc = ".".join(str(p) for p in err["loc"])
                msg = err["msg"]
                errors.append(f"time_window_thresholds[{i}].{loc}: {msg}")

    return "\n".join(errors) if errors else None
