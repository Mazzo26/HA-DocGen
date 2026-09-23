"""Central logging abstraction and console implementation for HA-DocGen."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Protocol

from rich.console import Console


class LogLevel(IntEnum):
    """Supported log levels."""

    DEBUG = 10
    VERBOSE = 15
    INFO = 20
    WARNING = 30
    ERROR = 40


class Logger(Protocol):
    """Output-independent application logging contract."""

    def is_enabled(self, level: LogLevel) -> bool:
        """Return whether a log level is enabled."""
        ...

    def debug(self, message: str) -> None:
        """Log diagnostic details."""
        ...

    def verbose(self, message: str) -> None:
        """Log verbose execution details."""
        ...

    def info(self, message: str) -> None:
        """Log regular execution information."""
        ...

    def warning(self, message: str) -> None:
        """Log a warning."""
        ...

    def error(self, message: str) -> None:
        """Log an error."""
        ...

    def section(self, title: str) -> None:
        """Log a section heading."""
        ...

    def blank(self) -> None:
        """Log a blank line."""
        ...


@dataclass(frozen=True, slots=True)
class ConsoleLogger:
    """Immutable Rich-backed implementation of :class:`Logger`."""

    level: LogLevel = LogLevel.INFO
    _console: Console = field(
        default_factory=lambda: Console(stderr=True),
        repr=False,
        compare=False,
    )

    def is_enabled(self, level: LogLevel) -> bool:
        """Return True when messages at the given level are emitted."""
        return level >= self.level

    def debug(self, message: str) -> None:
        """Log a debug message."""
        self._emit(LogLevel.DEBUG, message)

    def verbose(self, message: str) -> None:
        """Log a verbose message."""
        self._emit(LogLevel.VERBOSE, message)

    def info(self, message: str) -> None:
        """Log an informational message."""
        self._emit(LogLevel.INFO, message)

    def warning(self, message: str) -> None:
        """Log a warning message."""
        self._emit(LogLevel.WARNING, message)

    def error(self, message: str) -> None:
        """Log an error message."""
        self._emit(LogLevel.ERROR, message)

    def section(self, title: str) -> None:
        """Log a section header without exposing Rich to callers."""
        if self.is_enabled(LogLevel.INFO):
            self._console.rule(f"[bold]{title}[/bold]")

    def blank(self) -> None:
        """Log a blank line when INFO output is enabled."""
        if self.is_enabled(LogLevel.INFO):
            self._console.print()

    def _emit(self, level: LogLevel, message: str) -> None:
        """Emit a styled message when the level is enabled."""
        if not self.is_enabled(level):
            return

        label, style = _level_presentation(level)
        prefix = f"[{style}]{label}[/{style}]" if style else label
        self._console.print(f"{prefix}  {message}")


def logging_level(*, quiet: bool, verbose: bool, debug: bool) -> LogLevel:
    """Return the log level for mutually exclusive CLI mode flags."""
    if sum((quiet, verbose, debug)) > 1:
        raise ValueError("--quiet, --verbose and --debug are mutually exclusive.")
    if quiet:
        return LogLevel.ERROR
    if debug:
        return LogLevel.DEBUG
    if verbose:
        return LogLevel.VERBOSE
    return LogLevel.INFO


def get_logger(level: LogLevel = LogLevel.INFO) -> Logger:
    """Create an independent console logger."""
    return ConsoleLogger(level=level)


def _level_presentation(level: LogLevel) -> tuple[str, str]:
    """Return the deterministic label and Rich style for a level."""
    presentations = {
        LogLevel.DEBUG: ("DEBUG", "dim"),
        LogLevel.VERBOSE: ("VERBOSE", "cyan"),
        LogLevel.INFO: ("INFO", ""),
        LogLevel.WARNING: ("WARNING", "yellow"),
        LogLevel.ERROR: ("ERROR", "bold red"),
    }
    return presentations[level]
