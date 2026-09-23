"""Tests for execution timing and summary reporting."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import Mock, call

import pytest

from tools.ha_docgen import (
    ExecutionSummary,
    ExecutionSummaryReporter,
    ExecutionTiming,
    TimingUtility,
)


def test_timing_utility_uses_injected_clock() -> None:
    """Timing is deterministic when supplied with a deterministic clock."""
    clock = Mock(side_effect=(10.0, 10.125))

    result, timing = TimingUtility().measure("scan", lambda: "result", clock=clock)

    assert result == "result"
    assert timing == ExecutionTiming(label="scan", elapsed_seconds=0.125)


def test_execution_timing_is_immutable() -> None:
    """Public timing models cannot be mutated after construction."""
    timing = ExecutionTiming(label="scan", elapsed_seconds=0.1)

    with pytest.raises(FrozenInstanceError):
        timing.label = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("label", "elapsed_seconds"),
    (("", 0.1), ("scan", -0.1), ("scan", float("inf")), ("scan", float("nan"))),
)
def test_execution_timing_rejects_invalid_values(
    label: str,
    elapsed_seconds: float,
) -> None:
    """Invalid labels and durations cannot enter an execution summary."""
    with pytest.raises(ValueError):
        ExecutionTiming(label=label, elapsed_seconds=elapsed_seconds)


def test_timing_utility_propagates_operation_errors() -> None:
    """Timing does not hide errors raised by the measured operation."""

    def fail() -> None:
        raise RuntimeError("failed")

    with pytest.raises(RuntimeError, match="failed"):
        TimingUtility().measure("scan", fail, clock=Mock(return_value=1.0))


def test_execution_summary_sorts_timings_deterministically() -> None:
    """Summary order never depends on caller insertion order."""
    summary = ExecutionSummary(
        success=True,
        timings=(
            ExecutionTiming("render", 0.2),
            ExecutionTiming("load", 0.1),
        ),
    )

    assert tuple(item.label for item in summary.timings) == ("load", "render")
    assert summary.total_seconds == pytest.approx(0.3)


@pytest.mark.parametrize(
    ("success", "status"),
    ((True, "SUCCESS"), (False, "FAILED")),
)
def test_execution_summary_reporter_prints_complete_summary(
    success: bool,
    status: str,
) -> None:
    """The stateless reporter emits status, steps and total duration."""
    logger = Mock()
    summary = ExecutionSummary(
        success=success,
        timings=(ExecutionTiming("scan", 0.125),),
    )

    ExecutionSummaryReporter().report(logger, summary)

    assert logger.method_calls == [
        call.section("Execution summary"),
        call.info(f"Status: {status}"),
        call.info("scan: 0.125s"),
        call.info("Total: 0.125s"),
    ]
