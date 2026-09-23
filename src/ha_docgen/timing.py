"""Deterministic execution timing models and stateless utilities."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from .logging import Logger

_Result = TypeVar("_Result")


@dataclass(frozen=True, slots=True)
class ExecutionTiming:
    """Elapsed time for one named execution step."""

    label: str
    elapsed_seconds: float

    def __post_init__(self) -> None:
        """Reject invalid timing data."""
        if not self.label:
            raise ValueError("Timing label cannot be empty.")
        if not math.isfinite(self.elapsed_seconds) or self.elapsed_seconds < 0:
            raise ValueError("Elapsed time must be finite and non-negative.")


@dataclass(frozen=True, slots=True)
class ExecutionSummary:
    """Immutable, deterministic summary of one execution."""

    success: bool
    timings: tuple[ExecutionTiming, ...] = ()

    def __post_init__(self) -> None:
        """Sort timings independently of caller insertion order."""
        ordered = tuple(sorted(self.timings, key=lambda item: (item.label, item.elapsed_seconds)))
        object.__setattr__(self, "timings", ordered)

    @property
    def total_seconds(self) -> float:
        """Return the sum of all measured step durations."""
        return sum(timing.elapsed_seconds for timing in self.timings)


class TimingUtility:
    """Measure operations without retaining state."""

    def measure(
        self,
        label: str,
        operation: Callable[[], _Result],
        *,
        clock: Callable[[], float] = time.perf_counter,
    ) -> tuple[_Result, ExecutionTiming]:
        """Execute an operation and return its result and elapsed timing."""
        started_at = clock()
        result = operation()
        elapsed_seconds = clock() - started_at
        return result, ExecutionTiming(label, elapsed_seconds)


class ExecutionSummaryReporter:
    """Render execution summaries through an explicit logger."""

    def report(self, logger: Logger, summary: ExecutionSummary) -> None:
        """Emit a deterministic execution summary."""
        logger.section("Execution summary")
        logger.info(f"Status: {'SUCCESS' if summary.success else 'FAILED'}")
        for timing in summary.timings:
            logger.info(f"{timing.label}: {timing.elapsed_seconds:.3f}s")
        logger.info(f"Total: {summary.total_seconds:.3f}s")
