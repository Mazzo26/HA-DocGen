"""CLI integration tests for reporting commands."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from ha_docgen import LogLevel
from ha_docgen import main as cli
from ha_docgen.incremental import (
    CacheStatus,
    ChangeSet,
    IncrementalScanResult,
)
from ha_docgen.reporting import Report, ReportMetadata
from ha_docgen.version import APP_NAME, VERSION

_REPORT_COMMANDS = (
    ("health", "Health Report"),
    ("config", "Configuration Report"),
    ("architecture", "Architecture Report"),
    ("inventory", "Inventory Report"),
    ("dependencies", "Dependency Report"),
    ("performance", "Performance Report"),
    ("docs", "Documentation Index Report"),
)


@pytest.fixture(autouse=True)
def _accept_runtime_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep existing CLI tests focused on dispatch and reporting."""
    monkeypatch.setattr(cli, "validate_runtime_configuration", Mock(return_value=()))


def _report() -> Report:
    """Return a minimal generated report for CLI dispatch tests."""
    return Report(
        title="Generated Report",
        metadata=ReportMetadata(
            generated_at=datetime(2026, 9, 21, tzinfo=UTC),
            version="0.1.0",
            project_path=Path("config"),
            execution_time=0.1,
        ),
    )


@pytest.mark.parametrize(
    ("command", "generator_name"),
    (
        ("health", "HealthReportGenerator"),
        ("config", "ConfigurationReportGenerator"),
        ("architecture", "ArchitectureReportGenerator"),
        ("inventory", "InventoryReportGenerator"),
        ("dependencies", "DependencyReportGenerator"),
        ("performance", "PerformanceReportGenerator"),
        ("docs", "DocumentationIndexReportGenerator"),
    ),
)
def test_report_command_dispatches_generator_and_renderer(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    generator_name: str,
) -> None:
    """Each report command invokes its generator, renderer and emits output."""
    config = Mock(version="0.1.0", root=Path("config"))
    generator = Mock()
    generator.generate.return_value = _report()
    renderer = Mock()
    renderer.render.return_value = "rendered report\n"

    monkeypatch.setattr(cli, "load_config", Mock(return_value=config))
    monkeypatch.setattr(cli, generator_name, Mock(return_value=generator))
    monkeypatch.setattr(cli, "ConsoleRenderer", Mock(return_value=renderer))

    exit_code = cli.main(("report", command))

    assert exit_code == 0
    generator.generate.assert_called_once()
    renderer.render.assert_called_once_with(generator.generate.return_value)
    assert capsys.readouterr().out == "rendered report\n"


@pytest.mark.parametrize(("command", "expected_title"), _REPORT_COMMANDS)
def test_report_command_runs_complete_pipeline_deterministically(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    command: str,
    expected_title: str,
) -> None:
    """The real generator and renderer produce stable output through main."""
    config = Mock(version="0.1.0", root=Path("project"))
    monkeypatch.setattr(cli, "load_config", Mock(return_value=config))
    monkeypatch.setattr(cli, "_report_metadata", Mock(return_value=_report().metadata))

    first_exit_code = cli.main(("report", command))
    first_output = capsys.readouterr().out
    second_exit_code = cli.main(("report", command))
    second_output = capsys.readouterr().out

    assert first_exit_code == second_exit_code == 0
    assert first_output == second_output
    assert first_output.startswith(f"{expected_title}\n")
    assert "| Metadata" in first_output


@pytest.mark.parametrize(
    ("arguments", "command_text"),
    (
        (("unknown",), "unknown"),
        (("report", "unknown"), "report unknown"),
        (("report", "health", "extra"), "report health extra"),
        (("report",), "report"),
    ),
)
def test_invalid_report_arguments_return_nonzero_readable_error(
    monkeypatch: pytest.MonkeyPatch,
    arguments: tuple[str, ...],
    command_text: str,
) -> None:
    """Unknown, invalid and incomplete commands fail with readable errors."""
    logger = Mock()
    monkeypatch.setattr(cli, "get_logger", Mock(return_value=logger))

    exit_code = cli.main(arguments)

    assert exit_code != 0
    logger.error.assert_called_once()
    assert f"Invalid command: {command_text}" in logger.error.call_args.args[0]
    assert "Supported commands:" in logger.error.call_args.args[0]


@pytest.mark.parametrize(
    ("flag", "expected_level"),
    (
        ("--quiet", LogLevel.ERROR),
        ("--verbose", LogLevel.VERBOSE),
        ("--debug", LogLevel.DEBUG),
    ),
)
def test_logging_options_configure_logger_and_preserve_command(
    monkeypatch: pytest.MonkeyPatch,
    flag: str,
    expected_level: LogLevel,
) -> None:
    """Logging flags configure one logger without changing dispatch."""
    logger = Mock()
    logger_factory = Mock(return_value=logger)
    run_cli = Mock(return_value=0)
    monkeypatch.setattr(cli, "get_logger", logger_factory)
    monkeypatch.setattr(cli, "_run_cli", run_cli)

    exit_code = cli.main((flag, "report", "health"))

    assert exit_code == 0
    logger_factory.assert_called_once_with(expected_level)
    run_cli.assert_called_once_with(("report", "health"), logger, Path("config.yaml"), None)


def test_conflicting_logging_options_fail_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Conflicting modes return a configuration error without dispatch."""
    logger = Mock()
    monkeypatch.setattr(cli, "get_logger", Mock(return_value=logger))
    run_cli = Mock()
    monkeypatch.setattr(cli, "_run_cli", run_cli)

    exit_code = cli.main(("--quiet", "--debug", "report", "health"))

    assert exit_code != 0
    run_cli.assert_not_called()
    logger.error.assert_called_once()
    assert "mutually exclusive" in logger.error.call_args.args[0]


def test_report_execution_emits_progress_and_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A successful report command reports all stages and a summary."""
    logger = Mock()
    config = Mock(version="0.1.0", root=Path("config"))
    monkeypatch.setattr(cli, "get_logger", Mock(return_value=logger))
    monkeypatch.setattr(cli, "load_config", Mock(return_value=config))
    monkeypatch.setattr(cli, "_generate_report", Mock(return_value=_report()))
    monkeypatch.setattr(
        cli, "ConsoleRenderer", Mock(return_value=Mock(render=Mock(return_value="")))
    )

    assert cli.main(("report", "health")) == 0

    messages = tuple(call.args[0] for call in logger.info.call_args_list)
    assert "Progress [1/3] Load and validate configuration" in messages
    assert "Progress [2/3] Generate report" in messages
    assert "Progress [3/3] Render report" in messages
    logger.section.assert_called_with("Execution summary")


def test_scan_execution_emits_progress_and_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The default scan path reports all stages and a success summary."""
    logger = Mock()
    config = Mock()
    scanner = Mock()
    scanner.scan.return_value = Mock()
    monkeypatch.setattr(cli, "get_logger", Mock(return_value=logger))
    monkeypatch.setattr(cli, "load_config", Mock(return_value=config))
    monkeypatch.setattr(cli, "Scanner", Mock(return_value=scanner))
    monkeypatch.setattr(cli, "_report_results", Mock())

    assert cli.main(()) == 0

    messages = tuple(call.args[0] for call in logger.info.call_args_list)
    assert "Progress [1/3] Load and validate configuration" in messages
    assert "Progress [2/3] Scan project" in messages
    assert "Progress [3/3] Report results" in messages
    assert "Status: SUCCESS" in messages


@pytest.mark.parametrize(
    ("failure", "expected_exit_code"),
    (
        (cli.ConfigError("invalid config"), cli.EXIT_CONFIG_ERROR),
        (RuntimeError("failed"), cli.EXIT_RUNTIME_ERROR),
    ),
)
def test_report_execution_summarizes_failures(
    monkeypatch: pytest.MonkeyPatch,
    failure: Exception,
    expected_exit_code: int,
) -> None:
    """Expected and unexpected failures receive stable exit handling."""
    logger = Mock()
    monkeypatch.setattr(cli, "get_logger", Mock(return_value=logger))
    monkeypatch.setattr(cli, "load_config", Mock(side_effect=failure))

    assert cli.main(("report", "health")) == expected_exit_code

    messages = tuple(call.args[0] for call in logger.info.call_args_list)
    assert "Status: FAILED" in messages
    logger.error.assert_called_once()


def test_validate_command_uses_existing_progress_and_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Standalone validation reports through Module 10.2 infrastructure."""
    logger = Mock()
    monkeypatch.setattr(cli, "get_logger", Mock(return_value=logger))
    monkeypatch.setattr(cli, "load_config", Mock(return_value=Mock()))

    assert cli.main(("validate",)) == 0

    messages = tuple(call.args[0] for call in logger.info.call_args_list)
    assert "Progress [1/3] Load configuration" in messages
    assert "Progress [2/3] Validate configuration" in messages
    assert "Progress [3/3] Report validation" in messages
    assert "Configuration is valid." in messages
    assert "Status: SUCCESS" in messages


def test_config_and_output_options_are_forwarded_without_changing_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configuration path options remain independent from dispatch."""
    logger = Mock()
    run_cli = Mock(return_value=0)
    monkeypatch.setattr(cli, "get_logger", Mock(return_value=logger))
    monkeypatch.setattr(cli, "_run_cli", run_cli)

    exit_code = cli.main(("report", "health", "--config", "custom.yaml", "--output", "build/docs"))

    assert exit_code == 0
    run_cli.assert_called_once_with(
        ("report", "health"),
        logger,
        Path("custom.yaml"),
        Path("build/docs"),
    )


@pytest.mark.parametrize(
    "arguments",
    (
        ("validate", "--config"),
        ("validate", "--output"),
        ("validate", "--config", "one.yaml", "--config", "two.yaml"),
    ),
)
def test_invalid_configuration_options_fail_before_execution(
    monkeypatch: pytest.MonkeyPatch,
    arguments: tuple[str, ...],
) -> None:
    """Missing and duplicate option values return a configuration error."""
    logger = Mock()
    run_cli = Mock()
    monkeypatch.setattr(cli, "get_logger", Mock(return_value=logger))
    monkeypatch.setattr(cli, "_run_cli", run_cli)

    assert cli.main(arguments) == cli.EXIT_CONFIG_ERROR

    run_cli.assert_not_called()
    logger.error.assert_called_once()


def test_invalid_configuration_prevents_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validation failures block scanner execution."""
    logger = Mock()
    scanner = Mock()
    monkeypatch.setattr(cli, "get_logger", Mock(return_value=logger))
    monkeypatch.setattr(cli, "load_config", Mock(return_value=Mock()))
    monkeypatch.setattr(
        cli,
        "validate_runtime_configuration",
        Mock(return_value=("Project root does not exist: missing",)),
    )
    monkeypatch.setattr(cli, "Scanner", scanner)

    assert cli.main(()) == cli.EXIT_CONFIG_ERROR

    scanner.assert_not_called()
    assert "Invalid configuration" in logger.error.call_args.args[0]


@pytest.mark.parametrize(
    ("flags", "force", "clean_cache"),
    (
        (("--incremental",), False, False),
        (("--force",), True, False),
        (("--clean-cache",), False, True),
        (("--incremental", "--force", "--clean-cache"), True, True),
    ),
)
def test_incremental_options_are_forwarded_to_scan(
    monkeypatch: pytest.MonkeyPatch,
    flags: tuple[str, ...],
    force: bool,
    clean_cache: bool,
) -> None:
    """Incremental flags compose without duplicating the scan command."""
    logger = Mock()
    run_scan = Mock(return_value=0)
    monkeypatch.setattr(cli, "get_logger", Mock(return_value=logger))
    monkeypatch.setattr(cli, "_run_scan", run_scan)

    assert cli.main(flags) == 0

    options = run_scan.call_args.args[3]
    assert options.enabled is True
    assert options.force is force
    assert options.clean_cache is clean_cache


def test_duplicate_or_command_scoped_incremental_options_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Duplicate flags and report combinations are rejected before execution."""
    logger = Mock()
    monkeypatch.setattr(cli, "get_logger", Mock(return_value=logger))

    assert cli.main(("--incremental", "--incremental")) == cli.EXIT_CONFIG_ERROR
    assert cli.main(("report", "health", "--incremental")) == cli.EXIT_CONFIG_ERROR


def test_incremental_scan_reuses_progress_logging_and_existing_scanner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Incremental selection reports cache and work counts through Logger."""
    logger = Mock()
    changes = ChangeSet(
        changed=("changed.yaml",),
        unchanged=("same.yaml",),
        full_scan_required=True,
    )
    result = IncrementalScanResult((), changes, CacheStatus.CORRUPT)
    incremental_scanner = Mock()
    incremental_scanner.scan.return_value = result
    scanner = Mock()
    model = Mock()
    scanner.scan.return_value = model
    monkeypatch.setattr(cli, "IncrementalScanner", Mock(return_value=incremental_scanner))
    monkeypatch.setattr(cli, "Scanner", Mock(return_value=scanner))
    options = cli._IncrementalOptions(enabled=True, force=True, clean_cache=True)

    config = Mock(root=Path("project"))
    assert cli._scan_project(config, logger, options) is model

    messages = tuple(call.args[0] for call in logger.info.call_args_list)
    assert "Progress [1/4] Scanning files..." in messages
    assert "Progress [2/4] Hashing files..." in messages
    assert "Progress [3/4] Comparing cache..." in messages
    assert "Progress [4/4] Rebuilding changed files..." in messages
    assert "Cache invalid." in tuple(call.args[0] for call in logger.warning.call_args_list)
    assert "Cache cleaned." in messages
    assert "Full scan required." in messages
    assert "Changed files: 1" in messages
    assert "Skipped files: 1" in messages
    scanner.scan.assert_called_once_with((Path("project/changed.yaml"),))


def test_incremental_scan_logs_found_and_created_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valid and initially missing cache states receive explicit diagnostics."""
    logger = Mock()
    scanner = Mock()
    scanner.scan.return_value = Mock()
    monkeypatch.setattr(cli, "Scanner", Mock(return_value=scanner))
    incremental = Mock()
    monkeypatch.setattr(cli, "IncrementalScanner", Mock(return_value=incremental))
    options = cli._IncrementalOptions(enabled=True)

    for status, expected in (
        (CacheStatus.FOUND, "Cache found."),
        (CacheStatus.MISSING, "Cache created."),
    ):
        logger.reset_mock()
        incremental.scan.return_value = IncrementalScanResult((), ChangeSet(), status)
        cli._scan_project(Mock(), logger, options)
        assert expected in tuple(call.args[0] for call in logger.info.call_args_list)


@pytest.mark.parametrize(
    "arguments",
    (("help",), ("--help",), ("-h",), ("report", "health", "--help")),
)
def test_help_output_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
) -> None:
    """Help commands and flags share one usage text and do not execute work."""
    load_config = Mock()
    monkeypatch.setattr(cli, "load_config", load_config)

    assert cli.main(arguments) == cli.EXIT_SUCCESS

    output = capsys.readouterr().out
    assert output == cli._usage_text()
    assert output.startswith(f"{APP_NAME} {VERSION}\n")
    assert "ha-docgen init" in output
    assert "init               Create a default config.yaml" in output
    assert "health, config, architecture, inventory, dependencies, performance, docs" in output
    assert "--config <path>    Use a configuration file (default: config.yaml)" in output
    assert "Exit codes:" in output
    load_config.assert_not_called()


def test_init_creates_config_and_prints_next_steps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ha-docgen init writes config.yaml and prints the success guidance."""
    monkeypatch.chdir(tmp_path)

    assert cli.main(("init",)) == cli.EXIT_SUCCESS

    output = capsys.readouterr().out
    assert output == cli._INIT_SUCCESS
    assert "✓ config.yaml created" in output
    assert "Next steps:" in output
    assert "Set paths.root" in output
    assert "ha-docgen" in output
    assert (tmp_path / "config.yaml").is_file()


def test_init_refuses_existing_config_without_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Existing config.yaml yields a configuration error and no file changes."""
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.yaml"
    config_file.write_text("keep\n", encoding="utf-8")

    assert cli.main(("init",)) == cli.EXIT_CONFIG_ERROR

    assert capsys.readouterr().out == (
        "Configuration already exists.\n\nNo changes were made.\n"
    )
    assert config_file.read_text(encoding="utf-8") == "keep\n"


def test_init_reports_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Filesystem failures print a clear reason and exit non-zero."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        cli.InitializationService,
        "initialize",
        Mock(side_effect=cli.InitializationError("access denied")),
    )

    assert cli.main(("init",)) == cli.EXIT_RUNTIME_ERROR

    assert capsys.readouterr().out == (
        "Initialization failed.\n\nReason:\naccess denied\n"
    )
    assert not (tmp_path / "config.yaml").exists()


def test_init_rejects_extra_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """init accepts no additional positional arguments."""
    logger = Mock()
    monkeypatch.setattr(cli, "get_logger", Mock(return_value=logger))
    run_init = Mock()
    monkeypatch.setattr(cli, "_run_init", run_init)

    assert cli.main(("init", "extra")) == cli.EXIT_CONFIG_ERROR

    run_init.assert_not_called()
    logger.error.assert_called_once()
    assert "Invalid command: init extra" in logger.error.call_args.args[0]
    assert "init" in logger.error.call_args.args[0]


def test_write_stdout_reconfigures_legacy_console_encoding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy console encodings are upgraded so the success mark can print."""
    stream = Mock()
    stream.encoding = "cp1252"
    stream.reconfigure = Mock()
    monkeypatch.setattr(cli.sys, "stdout", stream)

    cli._write_stdout("✓ config.yaml created\n")

    stream.reconfigure.assert_called_once_with(encoding="utf-8")
    stream.write.assert_called_once_with("✓ config.yaml created\n")


def test_write_stdout_falls_back_to_utf8_buffer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When text encoding still fails, bytes are written through the buffer."""
    buffer = Mock()
    stream = Mock()
    stream.encoding = "cp1252"
    stream.reconfigure = Mock(side_effect=OSError("unsupported"))
    stream.write = Mock(side_effect=UnicodeEncodeError("cp1252", "✓", 0, 1, "no"))
    stream.buffer = buffer
    monkeypatch.setattr(cli.sys, "stdout", stream)

    cli._write_stdout("✓ ok\n")

    buffer.write.assert_called_once_with("✓ ok\n".encode())
    buffer.flush.assert_called_once_with()


@pytest.mark.parametrize("arguments", (("version",), ("--version",), ("-V",)))
def test_version_output_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
) -> None:
    """Version commands and flags share one version line."""
    load_config = Mock()
    monkeypatch.setattr(cli, "load_config", load_config)

    assert cli.main(arguments) == cli.EXIT_SUCCESS

    assert capsys.readouterr().out == f"{APP_NAME} {VERSION}\n"
    load_config.assert_not_called()


def test_help_and_version_are_mutually_exclusive(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Combined information requests fail before command execution."""
    logger = Mock()
    monkeypatch.setattr(cli, "get_logger", Mock(return_value=logger))

    assert cli.main(("help", "--version")) == cli.EXIT_CONFIG_ERROR

    assert capsys.readouterr().out == ""
    logger.error.assert_called_once()
    assert "mutually exclusive" in logger.error.call_args.args[0]


@pytest.mark.parametrize("arguments", (("help", "extra"), ("version", "extra")))
def test_information_commands_reject_extra_arguments(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    arguments: tuple[str, ...],
) -> None:
    """Information commands accept no additional positional arguments."""
    logger = Mock()
    monkeypatch.setattr(cli, "get_logger", Mock(return_value=logger))

    assert cli.main(arguments) == cli.EXIT_CONFIG_ERROR

    assert capsys.readouterr().out == ""
    logger.error.assert_called()


@pytest.mark.parametrize("command", tuple(name for name, _ in _REPORT_COMMANDS))
def test_report_command_parser_accepts_each_supported_name(command: str) -> None:
    """The isolated command parser accepts every advertised report name."""
    assert cli._parse_report_command(("report", command)) == command


def test_configuration_option_parser_uses_defaults_and_preserves_command() -> None:
    """No path options keeps the command and documented defaults intact."""
    arguments, config_file, output_directory = cli._extract_configuration_options(
        ("report", "health")
    )

    assert arguments == ("report", "health")
    assert config_file == Path("config.yaml")
    assert output_directory is None


def test_default_config_file_is_cwd_config_yaml() -> None:
    """Default config path is config.yaml in the current working directory."""
    assert cli._DEFAULT_CONFIG_FILE == Path("config.yaml")
    assert "examples/config.yaml" not in cli._usage_text()
    assert "(default: config.yaml)" in cli._usage_text()


def test_configuration_option_parser_accepts_options_in_any_position() -> None:
    """Path options are removed without reordering positional command tokens."""
    arguments, config_file, output_directory = cli._extract_configuration_options(
        ("--output", "docs", "report", "--config", "custom.yaml", "health")
    )

    assert arguments == ("report", "health")
    assert config_file == Path("custom.yaml")
    assert output_directory == Path("docs")


@pytest.mark.parametrize(
    ("failure", "expected_exit_code"),
    (
        (ValueError("bad arguments"), cli.EXIT_CONFIG_ERROR),
        (OSError("broken output"), cli.EXIT_RUNTIME_ERROR),
    ),
)
def test_cli_boundary_converts_errors_without_writing_output(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: Exception,
    expected_exit_code: int,
) -> None:
    """The isolated CLI boundary maps failures and never emits partial stdout."""
    logger = Mock()
    monkeypatch.setattr(cli, "collect_diagnostics", Mock(return_value=Mock()))
    monkeypatch.setattr(cli, "_execute_cli_command", Mock(side_effect=failure))
    summary = Mock()
    monkeypatch.setattr(cli, "_report_execution_summary", summary)

    exit_code = cli._run_cli(
        ("report", "health"),
        logger,
        Path("config.yaml"),
        None,
    )

    assert exit_code == expected_exit_code
    assert capsys.readouterr().out == ""
    logger.error.assert_called_once()
    summary.assert_called_once_with(logger, False, ())
