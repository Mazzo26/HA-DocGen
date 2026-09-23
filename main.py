"""Application entry point for HA-DocGen."""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from ._pipeline import _build_project_analysis, _ProjectAnalysis
from .config import ConfigError, ProjectConfig, load_config
from .configuration_validation import validate_runtime_configuration
from .diagnostics import (
    RuntimeDiagnostics,
    collect_diagnostics,
    log_startup,
    report_exception,
)
from .exit_codes import EXIT_CONFIG_ERROR, EXIT_RUNTIME_ERROR, EXIT_SUCCESS
from .incremental import CacheStatus, IncrementalScanner, IncrementalScanResult
from .logging import Logger, LogLevel, get_logger, logging_level
from .models import HomeAssistantModel
from .progress import ProgressReporter
from .reporting import (
    ArchitectureReportGenerator,
    ConfigurationReportGenerator,
    ConsoleRenderer,
    DependencyReportGenerator,
    DocumentationIndexReportGenerator,
    HealthReportGenerator,
    InventoryReportGenerator,
    PerformanceReportGenerator,
    Report,
    ReportMetadata,
)
from .scanner import Scanner
from .timing import (
    ExecutionSummary,
    ExecutionSummaryReporter,
    ExecutionTiming,
    TimingUtility,
)
from .version import APP_NAME, get_version

_REPORT_COMMANDS = (
    "health",
    "config",
    "architecture",
    "inventory",
    "dependencies",
    "performance",
    "docs",
)
_LOGGING_FLAGS = ("--quiet", "--verbose", "--debug")
_INCREMENTAL_FLAGS = ("--incremental", "--force", "--clean-cache")
_HELP_FLAGS = ("--help", "-h")
_VERSION_FLAGS = ("--version", "-V")
_VALUE_OPTIONS = ("--config", "--output")
_DEFAULT_CONFIG_FILE = Path("tools/config.yaml")
_USAGE = """\
{version}

Usage:
  ha-docgen [options]
  ha-docgen validate [options]
  ha-docgen report <name> [options]
  ha-docgen help
  ha-docgen version
  python -m tools.ha_docgen.main [options]

Commands:
  scan               Scan the repository when no command is given
  validate           Validate runtime configuration
  report <name>      Generate one report
  help               Show this usage information
  version            Show the application version

Report names:
  health, config, architecture, inventory, dependencies, performance, docs

Options:
  -h, --help         Show this usage information
  -V, --version      Show the application version
  --quiet            Show errors only
  --verbose          Show verbose execution details
  --debug            Show debug execution details
  --config <path>    Use a configuration file (default: tools/config.yaml)
  --output <path>    Override the documentation output directory
  --incremental      Scan only changed files
  --force            Ignore the incremental cache
  --clean-cache      Remove the incremental cache before scanning

Incremental options are valid only for the default scan command.
--quiet, --verbose and --debug are mutually exclusive.

Exit codes:
  0                  Success
  1                  Configuration error
  2                  Runtime error
"""


@dataclass(frozen=True, slots=True)
class _IncrementalOptions:
    """Validated incremental command-line options."""

    enabled: bool = False
    force: bool = False
    clean_cache: bool = False


_DEFAULT_INCREMENTAL_OPTIONS = _IncrementalOptions()


def main(argv: Sequence[str] | None = None) -> int:
    """Run HA-DocGen and return a process exit code."""
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    try:
        return _dispatch(arguments)
    except ValueError as exc:
        get_logger().error(str(exc))
        return EXIT_CONFIG_ERROR


def _dispatch(arguments: tuple[str, ...]) -> int:
    """Dispatch information, CLI and scan commands."""
    information = _information_request(arguments)
    if information is not None:
        return _run_information_command(information)
    command_arguments, level = _extract_logging_options(arguments)
    command_arguments, config_file, output_directory = _extract_configuration_options(
        command_arguments
    )
    command_arguments, incremental = _extract_incremental_options(command_arguments)
    logger = get_logger(level)
    logger.verbose(f"Arguments: {' '.join(command_arguments) or '(scan)'}")
    if not command_arguments:
        return _run_scan(logger, config_file, output_directory, incremental)
    if incremental.enabled:
        logger.error("Incremental options are only valid for the scan command.")
        return EXIT_CONFIG_ERROR
    return _run_cli(command_arguments, logger, config_file, output_directory)


def _information_request(arguments: tuple[str, ...]) -> str | None:
    """Return help or version when one information command was requested."""
    commands = _positional_arguments(arguments)
    help_requested = commands == ("help",) or any(item in _HELP_FLAGS for item in arguments)
    version_requested = commands == ("version",) or any(
        item in _VERSION_FLAGS for item in arguments
    )
    if help_requested and version_requested:
        raise ValueError("help and version are mutually exclusive.")
    if help_requested:
        return "help"
    if version_requested:
        return "version"
    return None


def _positional_arguments(arguments: tuple[str, ...]) -> tuple[str, ...]:
    """Return command tokens without flags or option values."""
    values: list[str] = []
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument in _VALUE_OPTIONS:
            index += 2
            continue
        if argument.startswith("-"):
            index += 1
            continue
        values.append(argument)
        index += 1
    return tuple(values)


def _run_information_command(command: str) -> int:
    """Write deterministic help or version output."""
    output = _usage_text() if command == "help" else _version_text()
    sys.stdout.write(output)
    return EXIT_SUCCESS


def _usage_text() -> str:
    """Return deterministic CLI usage information."""
    return _USAGE.format(version=_version_text().rstrip("\n"))


def _version_text() -> str:
    """Return the deterministic application version."""
    return f"{APP_NAME} {get_version()}\n"


def _run_cli(
    arguments: tuple[str, ...],
    logger: Logger,
    config_file: Path,
    output_directory: Path | None,
) -> int:
    """Dispatch a CLI command and return its process exit code."""
    diagnostics = collect_diagnostics()
    try:
        output, timings = _execute_cli_command(
            arguments, diagnostics, logger, config_file, output_directory
        )
    except (ConfigError, ValueError) as exc:
        report_exception(logger, exc)
        _report_execution_summary(logger, False, ())
        return EXIT_CONFIG_ERROR
    except Exception as exc:  # noqa: BLE001 - CLI boundary converts failures to exit codes.
        report_exception(logger, exc)
        _report_execution_summary(logger, False, ())
        return EXIT_RUNTIME_ERROR
    sys.stdout.write(output)
    _report_execution_summary(logger, True, timings)
    return EXIT_SUCCESS


def _execute_cli_command(
    arguments: tuple[str, ...],
    diagnostics: RuntimeDiagnostics,
    logger: Logger,
    config_file: Path,
    output_directory: Path | None,
) -> tuple[str, tuple[ExecutionTiming, ...]]:
    """Execute a validated CLI command."""
    if arguments == ("validate",):
        timings = _execute_validation(config_file, output_directory, logger)
        return "", timings
    command = _parse_report_command(arguments)
    return _execute_report(command, diagnostics, logger, config_file, output_directory)


def _execute_report(
    command: str,
    diagnostics: RuntimeDiagnostics,
    logger: Logger,
    config_file: Path,
    output_directory: Path | None,
) -> tuple[str, tuple[ExecutionTiming, ...]]:
    """Execute and time the three report pipeline stages."""
    config, configuration = _timed_step(
        logger,
        1,
        "Load and validate configuration",
        "configuration",
        lambda: _load_validated_config(config_file, output_directory),
    )
    report, generation = _timed_step(
        logger,
        2,
        "Generate report",
        "generation",
        lambda: _generate_report(command, config, diagnostics),
    )
    output, rendering = _timed_step(
        logger, 3, "Render report", "rendering", lambda: ConsoleRenderer().render(report)
    )
    return output, (configuration, generation, rendering)


def _parse_report_command(arguments: tuple[str, ...]) -> str:
    """Validate and return the requested report command."""
    if len(arguments) != 2 or arguments[0] != "report" or arguments[1] not in _REPORT_COMMANDS:
        command = " ".join(arguments) or "(empty)"
        supported = ", ".join(f"report {name}" for name in _REPORT_COMMANDS)
        raise ValueError(f"Invalid command: {command}. Supported commands: {supported}.")
    return arguments[1]


def _generate_report(
    command: str,
    config: ProjectConfig,
    diagnostics: RuntimeDiagnostics,
) -> Report:
    """Analyse the configured project and generate one report."""
    metadata = _report_metadata(config, diagnostics)
    analysis = _build_project_analysis(config)
    return _generate_report_from_analysis(command, analysis, metadata)


def _generate_report_from_analysis(
    command: str,
    analysis: _ProjectAnalysis,
    metadata: ReportMetadata,
) -> Report:
    """Generate one report from an existing production analysis."""
    if command == "health":
        return HealthReportGenerator().generate(analysis.validations, metadata)
    if command == "config":
        return ConfigurationReportGenerator().generate(
            analysis.model,
            analysis.yaml_repository,
            metadata,
        )
    if command == "performance":
        return PerformanceReportGenerator().generate(metadata)
    if command == "docs":
        return DocumentationIndexReportGenerator().generate(
            analysis.model,
            analysis.yaml_repository,
            analysis.documents,
            analysis.relationships,
            metadata,
        )
    return _generate_structural_report(command, analysis, metadata)


def _generate_structural_report(
    command: str,
    analysis: _ProjectAnalysis,
    metadata: ReportMetadata,
) -> Report:
    """Invoke a report generator that consumes project structure."""
    if command == "architecture":
        return ArchitectureReportGenerator().generate(
            analysis.project_tree,
            analysis.yaml_repository,
            analysis.graph,
            metadata,
        )
    if command == "inventory":
        return InventoryReportGenerator().generate(
            analysis.model,
            analysis.yaml_repository,
            analysis.project_tree,
            metadata,
        )
    return DependencyReportGenerator().generate(analysis.graph, metadata)


def _report_metadata(
    config: ProjectConfig,
    diagnostics: RuntimeDiagnostics,
) -> ReportMetadata:
    """Build report provenance from existing runtime and project data."""
    return ReportMetadata(
        generated_at=datetime.now(UTC),
        version=config.version,
        project_path=config.root,
        execution_time=diagnostics.elapsed_seconds,
    )


def _run_scan(
    logger: Logger,
    config_file: Path,
    output_directory: Path | None,
    incremental: _IncrementalOptions = _DEFAULT_INCREMENTAL_OPTIONS,
) -> int:
    """Run the original repository scan command."""
    diagnostics = collect_diagnostics()
    log_startup(logger, diagnostics)

    try:
        timings = _execute_scan(logger, config_file, output_directory, incremental)
    except ConfigError as exc:
        report_exception(logger, exc)
        _report_execution_summary(logger, False, ())
        return EXIT_CONFIG_ERROR
    except Exception as exc:  # noqa: BLE001 - CLI boundary converts failures to exit codes.
        report_exception(logger, exc)
        _report_execution_summary(logger, False, ())
        return EXIT_RUNTIME_ERROR

    diagnostics.finish()
    _report_execution_summary(logger, True, timings)
    return EXIT_SUCCESS


def _execute_scan(
    logger: Logger,
    config_file: Path,
    output_directory: Path | None,
    incremental: _IncrementalOptions = _DEFAULT_INCREMENTAL_OPTIONS,
) -> tuple[ExecutionTiming, ...]:
    """Execute and time the three scan pipeline stages."""
    config, configuration = _timed_step(
        logger,
        1,
        "Load and validate configuration",
        "configuration",
        lambda: _load_validated_config(config_file, output_directory),
    )
    ha, scanning = _timed_step(
        logger,
        2,
        "Scan project",
        "scanning",
        lambda: _scan_project(config, logger, incremental),
    )
    _, reporting = _timed_step(
        logger, 3, "Report results", "reporting", lambda: _report_results(logger, config, ha)
    )
    return configuration, scanning, reporting


def _scan_project(
    config: ProjectConfig,
    logger: Logger,
    options: _IncrementalOptions,
) -> HomeAssistantModel:
    """Run optional incremental selection before the existing scan."""
    if not options.enabled:
        return Scanner(config).scan()
    progress = ProgressReporter()
    progress.report(logger, 1, 4, "Scanning files...")
    progress.report(logger, 2, 4, "Hashing files...")
    result = IncrementalScanner().scan(
        config,
        force=options.force,
        clean_cache=options.clean_cache,
    )
    progress.report(logger, 3, 4, "Comparing cache...")
    _log_incremental_result(logger, result, options)
    progress.report(logger, 4, 4, "Rebuilding changed files...")
    selected = tuple(
        config.root / relative_path for relative_path in result.changes.files_to_process
    )
    return Scanner(config).scan(selected)


def _log_incremental_result(
    logger: Logger,
    result: IncrementalScanResult,
    options: _IncrementalOptions,
) -> None:
    """Log deterministic incremental cache and selection diagnostics."""
    if result.cache_status is CacheStatus.FOUND:
        logger.info("Cache found.")
    elif result.cache_status is CacheStatus.CORRUPT:
        logger.warning("Cache invalid.")
    else:
        logger.info("Cache created.")
    if options.clean_cache:
        logger.info("Cache cleaned.")
    if result.changes.full_scan_required:
        logger.info("Full scan required.")
    logger.info(f"Changed files: {len(result.changes.files_to_process)}")
    logger.info(f"Skipped files: {len(result.changes.skipped)}")


def _execute_validation(
    config_file: Path,
    output_directory: Path | None,
    logger: Logger,
) -> tuple[ExecutionTiming, ...]:
    """Execute and time standalone runtime configuration validation."""
    config, loading = _timed_step(
        logger,
        1,
        "Load configuration",
        "configuration",
        lambda: _load_config_with_override(config_file, output_directory),
    )
    _, validation = _timed_step(
        logger,
        2,
        "Validate configuration",
        "validation",
        lambda: _ensure_valid_configuration(config),
    )
    _, reporting = _timed_step(
        logger,
        3,
        "Report validation",
        "reporting",
        lambda: logger.info("Configuration is valid."),
    )
    return loading, validation, reporting


def _load_validated_config(
    config_file: Path,
    output_directory: Path | None,
) -> ProjectConfig:
    """Load overrides and validate runtime configuration."""
    config = _load_config_with_override(config_file, output_directory)
    _ensure_valid_configuration(config)
    return config


def _load_config_with_override(
    config_file: Path,
    output_directory: Path | None,
) -> ProjectConfig:
    """Load configuration and apply the explicit documentation output."""
    config = load_config(config_file)
    if output_directory is None:
        return config
    return replace(config, output_docs=output_directory)


def _ensure_valid_configuration(config: ProjectConfig) -> None:
    """Raise one configuration error containing all validation failures."""
    version = (sys.version_info.major, sys.version_info.minor)
    errors = validate_runtime_configuration(config, version)
    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise ConfigError(f"Invalid configuration:\n{details}")


def _timed_step[Result](
    logger: Logger,
    completed: int,
    message: str,
    label: str,
    operation: Callable[[], Result],
) -> tuple[Result, ExecutionTiming]:
    """Report progress and measure one operation."""
    ProgressReporter().report(logger, completed, 3, message)
    return TimingUtility().measure(label, operation)


def _extract_logging_options(
    arguments: tuple[str, ...],
) -> tuple[tuple[str, ...], LogLevel]:
    """Remove logging flags and return command arguments plus level."""
    selected = tuple(argument for argument in arguments if argument in _LOGGING_FLAGS)
    if len(selected) > 1:
        raise ValueError("--quiet, --verbose and --debug are mutually exclusive.")
    remaining = tuple(argument for argument in arguments if argument not in _LOGGING_FLAGS)
    level = logging_level(
        quiet="--quiet" in selected,
        verbose="--verbose" in selected,
        debug="--debug" in selected,
    )
    return remaining, level


def _extract_configuration_options(
    arguments: tuple[str, ...],
) -> tuple[tuple[str, ...], Path, Path | None]:
    """Remove configuration flags and return their path values."""
    remaining: list[str] = []
    values: dict[str, Path] = {}
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument not in ("--config", "--output"):
            remaining.append(argument)
            index += 1
            continue
        if argument in values:
            raise ValueError(f"{argument} may only be specified once.")
        if index + 1 >= len(arguments) or arguments[index + 1].startswith("--"):
            raise ValueError(f"{argument} requires a path.")
        values[argument] = Path(arguments[index + 1])
        index += 2
    return (
        tuple(remaining),
        values.get("--config", _DEFAULT_CONFIG_FILE),
        values.get("--output"),
    )


def _extract_incremental_options(
    arguments: tuple[str, ...],
) -> tuple[tuple[str, ...], _IncrementalOptions]:
    """Remove incremental flags and return their immutable settings."""
    selected = tuple(argument for argument in arguments if argument in _INCREMENTAL_FLAGS)
    if len(selected) != len(set(selected)):
        duplicate = next(flag for flag in _INCREMENTAL_FLAGS if selected.count(flag) > 1)
        raise ValueError(f"{duplicate} may only be specified once.")
    remaining = tuple(argument for argument in arguments if argument not in _INCREMENTAL_FLAGS)
    return remaining, _IncrementalOptions(
        enabled=bool(selected),
        force="--force" in selected,
        clean_cache="--clean-cache" in selected,
    )


def _report_execution_summary(
    logger: Logger,
    success: bool,
    timings: tuple[ExecutionTiming, ...],
) -> None:
    """Build and report one immutable execution summary."""
    summary = ExecutionSummary(success=success, timings=timings)
    ExecutionSummaryReporter().report(logger, summary)


def _report_results(
    logger: Logger,
    config: ProjectConfig,
    ha: HomeAssistantModel,
) -> None:
    """Report scan results through the application logger."""
    logger.info(f"Project : {config.project_name}")
    logger.blank()
    _report_file_stats(logger, ha)
    logger.blank()
    _report_structure(logger, ha)
    logger.blank()
    _report_folders(logger, ha)


def _report_file_stats(logger: Logger, ha: HomeAssistantModel) -> None:
    """Report file type statistics."""
    logger.section("Bestandsstatistieken")
    logger.info(f"YAML   : {ha.scan.yaml_files}")
    logger.info(f"JSON   : {ha.scan.json_files}")
    logger.info(f"Python : {ha.scan.python_files}")


def _report_structure(logger: Logger, ha: HomeAssistantModel) -> None:
    """Report high-level project structure counts."""
    logger.section("Projectstructuur")
    logger.info(f"Packages          : {ha.scan.package_count}")
    logger.info(f"Dashboards        : {ha.scan.dashboard_count}")
    logger.info(f"ESPHome           : {ha.scan.esphome_count}")
    logger.info(f"Themes            : {ha.scan.theme_count}")
    logger.info(f"Custom Components : {ha.scan.custom_component_count}")


def _report_folders(logger: Logger, ha: HomeAssistantModel) -> None:
    """Report discovered folders."""
    logger.section("Gedetecteerde mappen")
    for folder in ha.folders:
        status = "OK" if folder.exists else "MISSING"
        logger.info(f"{status:<8} {folder.name:<20} {folder.file_count:>6} bestanden")


if __name__ == "__main__":
    raise SystemExit(main())
