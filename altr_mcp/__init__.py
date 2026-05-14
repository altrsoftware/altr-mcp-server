from importlib.metadata import PackageNotFoundError, version

from altr_mcp.models import (
    AccessRateThreshold,
    TimeRange,
    TimeWindowThreshold,
    validate_access_rate_thresholds,
    validate_time_window_thresholds,
)
from altr_mcp.settings import get_settings

try:
    __version__ = version("altr-mcp")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

__all__ = [
    "__version__",
    "get_settings",
    "AccessRateThreshold",
    "TimeRange",
    "TimeWindowThreshold",
    "validate_access_rate_thresholds",
    "validate_time_window_thresholds",
]
