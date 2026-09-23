"""Unit tests for ConsoleRenderer."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.ha_docgen.reporting import (
    ConsoleRenderer,
    Report,
    ReportMetadata,
    ReportSection,
    Severity,
)


def _metadata(*, execution_time: float = 0.25) -> ReportMetadata:
    return ReportMetadata(
        generated_at=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
        version="0.2.0",
        project_path=Path("config"),
        execution_time=execution_time,
    )


def _report() -> Report:
    return Report(
        title="Health Report",
        metadata=_metadata(),
        description="Configuration health.",
        summary="Healthy.",
        sections=(
            ReportSection(
                title="Errors",
                severity=Severity.ERROR,
                description="Validation errors.",
                items=("sensor.invalid: missing state",),
            ),
            ReportSection(
                title="Information",
                severity=Severity.INFO,
            ),
        ),
        statistics={"warnings": 1, "errors": 0},
        recommendations=("Review the warning.",),
    )


def test_render_complete_report_as_plain_text() -> None:
    rendered = ConsoleRenderer().render(_report())

    assert rendered.startswith("Health Report\n=============\n\nConfiguration health.")
    assert "| Summary  |\n+----------+\n| Healthy. |" in rendered
    assert "| Generated at   | 2026-09-21T12:00:00+00:00 |" in rendered
    assert "| Execution time | 0.25s                     |" in rendered
    assert "Errors [ERROR]\n--------------\nValidation errors." in rendered
    assert "- sensor.invalid: missing state" in rendered
    assert "Information [INFO]\n------------------" in rendered
    assert "| errors    | 0     |\n| warnings  | 1     |" in rendered
    assert "Recommendations\n---------------\n- Review the warning." in rendered
    assert rendered.endswith("\n")
    assert "\x1b[" not in rendered


def test_render_empty_report_omits_optional_blocks() -> None:
    rendered = ConsoleRenderer().render(Report(title="Empty", metadata=_metadata()))

    assert rendered.startswith("Empty\n=====\n\n+")
    assert "Summary" not in rendered
    assert "Recommendations" not in rendered
    assert "Statistic" not in rendered
    assert "[INFO]" not in rendered
    assert "| Metadata       | Value                     |" in rendered


@pytest.mark.parametrize(
    ("severity", "code"),
    (
        (Severity.INFO, "\x1b[36m"),
        (Severity.WARNING, "\x1b[33m"),
        (Severity.ERROR, "\x1b[31m"),
    ),
)
def test_optional_ansi_colour_by_severity(severity: Severity, code: str) -> None:
    report = Report(
        title="Report",
        metadata=_metadata(),
        sections=(ReportSection(title="Finding", severity=severity),),
    )

    rendered = ConsoleRenderer().render(report, colour=True)

    assert rendered.startswith("\x1b[1mReport\x1b[0m\n======")
    assert f"{code}Finding [{severity.value.upper()}]\x1b[0m" in rendered
    assert "------" in rendered


def test_plain_and_coloured_rendering_have_same_visible_layout() -> None:
    renderer = ConsoleRenderer()
    report = _report()
    plain = renderer.render(report)
    coloured = renderer.render(report, colour=True)

    for code in ("\x1b[1m", "\x1b[36m", "\x1b[31m", "\x1b[0m"):
        coloured = coloured.replace(code, "")
    assert coloured == plain


def test_tables_align_mixed_key_and_value_lengths() -> None:
    report = Report(
        title="Statistics",
        metadata=_metadata(),
        statistics={"a": 12345, "long_name": 2.5},
    )
    rendered = ConsoleRenderer().render(report)
    lines = rendered.splitlines()
    header_index = next(index for index, line in enumerate(lines) if "| Statistic " in line)
    table_lines = lines[header_index - 1 : header_index + 5]

    assert len({len(line) for line in table_lines}) == 1
    assert "| a         | 12345 |" in rendered
    assert "| long_name | 2.5   |" in rendered


def test_render_is_stateless_and_deterministic() -> None:
    renderer = ConsoleRenderer()
    report = _report()

    assert vars(renderer) == {}
    assert renderer.render(report) == renderer.render(report)


def test_render_rejects_non_report_input() -> None:
    with pytest.raises(TypeError, match="report must be a Report"):
        ConsoleRenderer().render(None)  # type: ignore[arg-type]
