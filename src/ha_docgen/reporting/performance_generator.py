"""Build a Performance Report from existing timing information.

Aggregates already-collected operation timings and report metadata into
immutable report models. Performs no benchmarking, scanning, parsing,
rendering or filesystem writes.
"""

from __future__ import annotations

from collections.abc import Mapping

from .models import Report, ReportMetadata, ReportSection, Severity

_TITLE = "Performance Report"
_DESCRIPTION = "Performance overview derived from existing execution timings."
_SLOW_OPERATION_THRESHOLD_SECONDS = 1.0


class PerformanceReportGenerator:
    """Generate a Performance Report from already-collected timings."""

    def generate(
        self,
        metadata: ReportMetadata,
        operation_timings: tuple[tuple[str, float], ...] = (),
    ) -> Report:
        """Return an output-independent Performance Report.

        ``operation_timings`` must already be collected by the caller
        (for example scan duration or validator timings). This generator
        never measures or invents timings.
        """
        timings = _normalise_timings(operation_timings)
        statistics = _statistics(metadata, timings)
        return Report(
            title=_TITLE,
            metadata=metadata,
            description=_DESCRIPTION,
            sections=_sections(metadata, timings, statistics),
            statistics=statistics,
            recommendations=_recommendations(metadata, timings),
            summary=_summary(metadata, timings),
        )


def _normalise_timings(
    operation_timings: tuple[tuple[str, float], ...],
) -> tuple[tuple[str, float], ...]:
    """Deduplicate by operation name and sort deterministically by name."""
    by_name = {name: duration for name, duration in operation_timings if name}
    return tuple(sorted(by_name.items(), key=lambda item: item[0]))


def _statistics(
    metadata: ReportMetadata,
    timings: tuple[tuple[str, float], ...],
) -> dict[str, int | float]:
    """Build performance statistics from metadata and operation timings."""
    durations = tuple(duration for _, duration in timings)
    statistics: dict[str, int | float] = {
        "execution_time_seconds": metadata.execution_time,
        "total_operations": len(timings),
        "total_operation_time_seconds": sum(durations) if durations else 0.0,
    }
    if durations:
        statistics["average_operation_seconds"] = sum(durations) / len(durations)
        statistics["slowest_operation_seconds"] = max(durations)
        statistics["fastest_operation_seconds"] = min(durations)
    for name, duration in timings:
        statistics[f"operation_{_stat_key(name)}_seconds"] = duration
    return statistics


def _stat_key(name: str) -> str:
    """Convert an operation name into a stable statistics key fragment."""
    return name.strip().lower().replace(" ", "_")


def _summary(
    metadata: ReportMetadata,
    timings: tuple[tuple[str, float], ...],
) -> str:
    """Build the overall performance summary."""
    if metadata.execution_time == 0 and not timings:
        return "No performance information is available."
    if not timings:
        return (
            f"Performance overview: execution time "
            f"{metadata.execution_time:.2f}s; no operation timings supplied."
        )
    slowest_name, slowest_duration = max(timings, key=lambda item: item[1])
    return (
        f"Performance overview: execution time {metadata.execution_time:.2f}s, "
        f"{len(timings)} timed operation(s); "
        f"slowest is {slowest_name} ({slowest_duration:.2f}s)."
    )


def _sections(
    metadata: ReportMetadata,
    timings: tuple[tuple[str, float], ...],
    statistics: Mapping[str, int | float],
) -> tuple[ReportSection, ...]:
    """Build summary, performance and statistics sections."""
    if metadata.execution_time == 0 and not timings:
        return ()
    return (
        _summary_section(metadata, timings),
        _performance_section(metadata, timings),
        _statistics_section(statistics),
    )


def _summary_section(
    metadata: ReportMetadata,
    timings: tuple[tuple[str, float], ...],
) -> ReportSection:
    """Build the performance count overview section."""
    return ReportSection(
        title="Summary",
        severity=Severity.INFO,
        items=(
            f"Execution time: {metadata.execution_time:.2f}s",
            f"Timed operations: {len(timings)}",
        ),
    )


def _performance_section(
    metadata: ReportMetadata,
    timings: tuple[tuple[str, float], ...],
) -> ReportSection:
    """Build scan duration, validator timings and slowest operations."""
    items = [f"Scan duration: {metadata.execution_time:.2f}s"]
    items.extend(_operation_items(timings))
    items.extend(_slowest_items(timings))
    return ReportSection(
        title="Performance",
        severity=Severity.INFO,
        description="Scan duration, validator timings and slowest operations.",
        items=tuple(items),
    )


def _operation_items(timings: tuple[tuple[str, float], ...]) -> tuple[str, ...]:
    """Format all supplied operation timings."""
    return tuple(f"Operation: {name} = {duration:.2f}s" for name, duration in timings)


def _slowest_items(timings: tuple[tuple[str, float], ...]) -> tuple[str, ...]:
    """List operations ordered from slowest to fastest."""
    ordered = sorted(timings, key=lambda item: (-item[1], item[0]))
    return tuple(f"Slowest: {name} = {duration:.2f}s" for name, duration in ordered)


def _statistics_section(statistics: Mapping[str, int | float]) -> ReportSection:
    """Build a plain-text statistics section."""
    return ReportSection(
        title="Statistics",
        severity=Severity.INFO,
        items=tuple(f"{key}: {value}" for key, value in sorted(statistics.items())),
    )


def _recommendations(
    metadata: ReportMetadata,
    timings: tuple[tuple[str, float], ...],
) -> tuple[str, ...]:
    """Recommend actions only when existing metrics justify them."""
    recommendations: list[str] = []
    if metadata.execution_time >= _SLOW_OPERATION_THRESHOLD_SECONDS:
        recommendations.append(
            "Overall execution time exceeds one second; review scan and " "validation cost."
        )
    slow = [name for name, duration in timings if duration >= _SLOW_OPERATION_THRESHOLD_SECONDS]
    if slow:
        recommendations.append("Investigate slow operations: " + ", ".join(sorted(slow)) + ".")
    return tuple(recommendations)
