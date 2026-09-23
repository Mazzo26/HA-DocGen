"""Unit tests for PerformanceReportGenerator."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ha_docgen.reporting import (
    PerformanceReportGenerator,
    Report,
    ReportMetadata,
    ReportSection,
    Severity,
)


def _metadata(*, execution_time: float = 0.25) -> ReportMetadata:
    return ReportMetadata(
        generated_at=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
        version="0.2.0",
        project_path=Path("/config"),
        execution_time=execution_time,
    )


def _section(report: Report, title: str) -> ReportSection:
    return next(section for section in report.sections if section.title == title)


def test_empty_performance() -> None:
    report = PerformanceReportGenerator().generate(_metadata(execution_time=0.0))
    assert isinstance(report, Report)
    assert report.title == "Performance Report"
    assert report.summary == "No performance information is available."
    assert report.sections == ()
    assert report.recommendations == ()
    assert report.statistics["execution_time_seconds"] == 0.0
    assert report.statistics["total_operations"] == 0


def test_execution_time_without_operation_timings() -> None:
    report = PerformanceReportGenerator().generate(_metadata(execution_time=1.5))
    assert report.summary == (
        "Performance overview: execution time 1.50s; " "no operation timings supplied."
    )
    performance = _section(report, "Performance")
    assert performance.severity is Severity.INFO
    assert performance.items == ("Scan duration: 1.50s",)
    assert report.recommendations == (
        ("Overall execution time exceeds one second; review scan and " "validation cost."),
    )


def test_operation_timings_validators_and_slowest() -> None:
    report = PerformanceReportGenerator().generate(
        _metadata(execution_time=2.0),
        (
            ("Validator: entity", 0.40),
            ("scan", 1.20),
            ("Validator: automation", 0.30),
            ("scan", 0.90),
        ),
    )
    performance = _section(report, "Performance")
    assert performance.items == (
        "Scan duration: 2.00s",
        "Operation: Validator: automation = 0.30s",
        "Operation: Validator: entity = 0.40s",
        "Operation: scan = 0.90s",
        "Slowest: scan = 0.90s",
        "Slowest: Validator: entity = 0.40s",
        "Slowest: Validator: automation = 0.30s",
    )
    # Last-write wins for duplicate names; sorted by name for operations.
    assert report.statistics["operation_scan_seconds"] == 0.90
    assert report.statistics["total_operations"] == 3
    assert report.statistics["slowest_operation_seconds"] == 0.90
    assert report.statistics["fastest_operation_seconds"] == 0.30
    assert report.summary == (
        "Performance overview: execution time 2.00s, 3 timed operation(s); "
        "slowest is scan (0.90s)."
    )


def test_slowest_items_are_ordered_by_duration_descending() -> None:
    report = PerformanceReportGenerator().generate(
        _metadata(),
        (
            ("fast", 0.10),
            ("slow", 2.50),
            ("medium", 1.10),
        ),
    )
    performance = _section(report, "Performance")
    slowest = tuple(item for item in performance.items if item.startswith("Slowest:"))
    assert slowest == (
        "Slowest: slow = 2.50s",
        "Slowest: medium = 1.10s",
        "Slowest: fast = 0.10s",
    )
    assert report.recommendations == ("Investigate slow operations: medium, slow.",)


def test_statistics_keys_are_sorted() -> None:
    report = PerformanceReportGenerator().generate(
        _metadata(execution_time=0.5),
        (("scan", 0.4),),
    )
    statistics = _section(report, "Statistics")
    assert statistics.items == tuple(sorted(statistics.items))
    assert list(report.statistics.keys()) == sorted(report.statistics.keys())


def test_generator_is_stateless_deterministic_and_preserves_metadata() -> None:
    generator = PerformanceReportGenerator()
    metadata = _metadata(execution_time=0.8)
    timings = (("scan", 0.5), ("Validator: entity", 0.2))
    first = generator.generate(metadata, timings)
    second = generator.generate(metadata, timings)
    assert first == second
    assert first.metadata is metadata
