"""Tests for centralized logging modes and console output."""

from __future__ import annotations

import pytest

from ha_docgen import (
    ConsoleLogger,
    LogLevel,
    logging_level,
)


@pytest.mark.parametrize(
    ("quiet", "verbose", "debug", "expected"),
    (
        (False, False, False, LogLevel.INFO),
        (True, False, False, LogLevel.ERROR),
        (False, True, False, LogLevel.VERBOSE),
        (False, False, True, LogLevel.DEBUG),
    ),
)
def test_logging_level_maps_cli_modes(
    quiet: bool,
    verbose: bool,
    debug: bool,
    expected: LogLevel,
) -> None:
    """Each supported CLI mode maps to one explicit minimum level."""
    assert logging_level(quiet=quiet, verbose=verbose, debug=debug) is expected


def test_logging_level_rejects_conflicting_modes() -> None:
    """Mutually exclusive logging modes fail with a readable error."""
    with pytest.raises(ValueError, match="mutually exclusive"):
        logging_level(quiet=True, verbose=True, debug=False)


def test_console_logger_filters_messages_by_level(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """ConsoleLogger emits only messages enabled by its immutable level."""
    logger = ConsoleLogger(level=LogLevel.VERBOSE)

    logger.debug("hidden")
    logger.verbose("details")
    logger.info("visible")

    captured = capsys.readouterr()
    assert "hidden" not in captured.err
    assert "VERBOSE  details" in captured.err
    assert "INFO  visible" in captured.err
    assert captured.out == ""


def test_quiet_console_logger_still_emits_errors(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Quiet mode suppresses regular output without hiding failures."""
    logger = ConsoleLogger(level=LogLevel.ERROR)

    logger.info("hidden")
    logger.warning("hidden")
    logger.error("failure")

    captured = capsys.readouterr()
    assert "failure" in captured.err
    assert "hidden" not in captured.err


def test_debug_console_logger_emits_debug_sections_and_spacing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Debug mode exposes diagnostics and supports shared layout methods."""
    logger = ConsoleLogger(level=LogLevel.DEBUG)

    logger.debug("diagnostic")
    logger.section("Details")
    logger.blank()

    captured = capsys.readouterr()
    assert "DEBUG  diagnostic" in captured.err
    assert "Details" in captured.err
    assert captured.err.endswith("\n\n")
