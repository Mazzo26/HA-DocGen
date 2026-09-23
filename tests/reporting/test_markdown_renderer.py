"""Unit tests for MarkdownRenderer."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ha_docgen.reporting import (
    MarkdownRenderer,
    Report,
    ReportMetadata,
    ReportSection,
    Severity,
)


def _metadata() -> ReportMetadata:
    return ReportMetadata(
        generated_at=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
        version="0.2|beta",
        project_path=Path("config"),
        execution_time=0.25,
    )


def _report() -> Report:
    return Report(
        title="Health Report",
        metadata=_metadata(),
        description="Configuration health.",
        summary="Healthy.",
        sections=(
            ReportSection(
                title="Findings",
                severity=Severity.WARNING,
                description="Review the detected findings.",
                items=(
                    "Read the [documentation](https://example.com/docs).",
                    "```yaml\nsensor:\n  - platform: template\n```",
                ),
            ),
        ),
        statistics={"warnings": 1, "empty": 0},
        recommendations=("Review warnings.", "Run validation again."),
    )


def test_render_complete_report_as_github_markdown() -> None:
    rendered = MarkdownRenderer().render(_report())

    assert rendered.startswith("# Health Report\n\nConfiguration health.")
    assert "## Summary\n\nHealthy." in rendered
    assert "| Version | 0.2\\|beta |" in rendered
    assert "| Generated at | 2026-09-21T12:00:00+00:00 |" in rendered
    assert "| Execution time | 0.25s |" in rendered
    assert "| empty | 0 |\n| warnings | 1 |" in rendered
    assert "## Findings\n\n### Severity: Warning" in rendered
    assert "- Read the [documentation](https://example.com/docs)." in rendered
    assert "```yaml\nsensor:\n  - platform: template\n```" in rendered
    assert "1. Review warnings.\n2. Run validation again." in rendered
    assert "\n\n---\n\n" in rendered
    assert rendered.endswith("\n")


def test_render_empty_report_omits_optional_blocks() -> None:
    rendered = MarkdownRenderer().render(Report(title="Empty", metadata=_metadata()))

    assert rendered.startswith("# Empty\n\n---\n\n## Metadata")
    assert "## Summary" not in rendered
    assert "## Statistics" not in rendered
    assert "## Recommendations" not in rendered


def test_multiline_items_remain_one_bullet() -> None:
    report = Report(
        title="Multiline",
        metadata=_metadata(),
        sections=(
            ReportSection(
                title="Details",
                severity=Severity.INFO,
                items=("first line\nsecond line",),
            ),
        ),
    )

    rendered = MarkdownRenderer().render(report)

    assert "- first line\n  second line" in rendered


def test_render_is_stateless_and_deterministic() -> None:
    renderer = MarkdownRenderer()
    report = _report()

    assert vars(renderer) == {}
    assert renderer.render(report) == renderer.render(report)


def test_render_rejects_non_report_input() -> None:
    with pytest.raises(TypeError, match="report must be a Report"):
        MarkdownRenderer().render(None)  # type: ignore[arg-type]
