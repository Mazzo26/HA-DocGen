"""Public API for HA-DocGen runtime infrastructure."""

from .config import ConfigError, ProjectConfig, load_config
from .configuration_validation import (
    ConfigurationValidator,
    EnvironmentValidator,
    OutputValidator,
    PathValidator,
    validate_runtime_configuration,
)
from .logging import ConsoleLogger, Logger, LogLevel, get_logger, logging_level
from .progress import ProgressReporter
from .timing import (
    ExecutionSummary,
    ExecutionSummaryReporter,
    ExecutionTiming,
    TimingUtility,
)
from .version import (
    APP_NAME,
    VERSION,
    InvalidVersionError,
    SemanticVersion,
    get_version,
    parse_version,
    validate_version,
)

__version__ = VERSION

__all__ = [
    "APP_NAME",
    "VERSION",
    "ConfigError",
    "ConfigurationValidator",
    "ConsoleLogger",
    "EnvironmentValidator",
    "ExecutionSummary",
    "ExecutionSummaryReporter",
    "ExecutionTiming",
    "InvalidVersionError",
    "LogLevel",
    "Logger",
    "OutputValidator",
    "PathValidator",
    "ProgressReporter",
    "ProjectConfig",
    "SemanticVersion",
    "TimingUtility",
    "get_logger",
    "get_version",
    "load_config",
    "logging_level",
    "parse_version",
    "validate_runtime_configuration",
    "validate_version",
]
