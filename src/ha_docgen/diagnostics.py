"""Runtime diagnostics for HA-DocGen."""

from __future__ import annotations

import platform
import sys
import time
import traceback
from dataclasses import dataclass

from .logging import Logger, LogLevel
from .version import APP_NAME, get_version


@dataclass(slots=True)
class RuntimeDiagnostics:
    """Snapshot of runtime environment and execution timing."""

    app_name: str
    app_version: str
    python_version: str
    platform_name: str
    started_at: float
    finished_at: float | None = None

    @property
    def elapsed_seconds(self) -> float:
        """Return elapsed seconds since start (or until finish)."""
        end = self.finished_at if self.finished_at is not None else time.perf_counter()
        return end - self.started_at

    def finish(self) -> None:
        """Mark the end of the measured run."""
        self.finished_at = time.perf_counter()


def collect_diagnostics() -> RuntimeDiagnostics:
    """Collect current runtime diagnostics."""
    return RuntimeDiagnostics(
        app_name=APP_NAME,
        app_version=get_version(),
        python_version=sys.version.split()[0],
        platform_name=platform.platform(),
        started_at=time.perf_counter(),
    )


def log_startup(logger: Logger, diagnostics: RuntimeDiagnostics) -> None:
    """Log startup diagnostics."""
    logger.section(diagnostics.app_name)
    logger.info(f"Version : {diagnostics.app_version}")
    logger.info(f"Python  : {diagnostics.python_version}")
    logger.info(f"Platform: {diagnostics.platform_name}")
    logger.blank()


def log_shutdown(logger: Logger, diagnostics: RuntimeDiagnostics) -> None:
    """Log shutdown diagnostics including elapsed time."""
    logger.blank()
    logger.info(f"Completed in {diagnostics.elapsed_seconds:.2f}s")


def report_exception(logger: Logger, exc: BaseException) -> None:
    """Report an exception in a user-friendly way.

    Full tracebacks are only shown when DEBUG logging is enabled.
    """
    logger.error(f"{type(exc).__name__}: {exc}")

    if logger.is_enabled(LogLevel.DEBUG):
        logger.debug(traceback.format_exc())
        return

    logger.info("Re-run with DEBUG logging for a full traceback.")
