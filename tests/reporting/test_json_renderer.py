"""Unit tests for JsonRenderer."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ha_docgen.reporting import (
    JsonRenderer,
    Report,
    ReportMetadata,
    ReportSection,
    Severity,
)


def _metadata() -> ReportMetadata:
    return ReportMetadata(
        generated_at=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
        version="0.2.0",
        project_path=Path("config"),
        execution_time=0.25,
    )


def _report() -> Report:
    return Report(
        title="Health Report",
        metadata=_metadata(),
        description="Configuratiegezondheid.",
        sections=(
            ReportSection(
                title="Warnings",
                severity=Severity.WARNING,
                items=("Eerste waarschuwing.", "Tweede waarschuwing."),
                description="Controleer deze waarschuwingen.",
            ),
            ReportSection(
                title="Information",
                severity=Severity.INFO,
            ),
        ),
        statistics={"warnings": 2, "score": 98.5},
        recommendations=("Controleer de configuratie.",),
        summary="Gezond met waarschuwingen.",
    )


def test_render_preserves_every_current_report_field() -> None:
    payload = json.loads(JsonRenderer().render(_report()))

    assert payload == {
        "description": "Configuratiegezondheid.",
        "metadata": {
            "execution_time": 0.25,
            "generated_at": "2026-09-21T12:00:00+00:00",
            "project_path": "config",
            "version": "0.2.0",
        },
        "recommendations": ["Controleer de configuratie."],
        "sections": [
            {
                "description": "Controleer deze waarschuwingen.",
                "items": ["Eerste waarschuwing.", "Tweede waarschuwing."],
                "severity": "warning",
                "title": "Warnings",
            },
            {
                "description": None,
                "items": [],
                "severity": "info",
                "title": "Information",
            },
        ],
        "statistics": {"score": 98.5, "warnings": 2},
        "summary": "Gezond met waarschuwingen.",
        "title": "Health Report",
    }


def test_render_empty_report_keeps_empty_values_and_collections() -> None:
    payload = json.loads(JsonRenderer().render(Report(title="", metadata=_metadata())))

    assert payload["title"] == ""
    assert payload["description"] == ""
    assert payload["summary"] == ""
    assert payload["sections"] == []
    assert payload["statistics"] == {}
    assert payload["recommendations"] == []


def test_render_is_human_readable_unicode_json_with_one_newline() -> None:
    report = Report(
        title="Energie ⚡",
        metadata=_metadata(),
        description="Temperatuur: 21 °C",
    )

    rendered = JsonRenderer().render(report)

    assert '"title": "Energie ⚡"' in rendered
    assert '"description": "Temperatuur: 21 °C"' in rendered
    assert '\n  "metadata": {' in rendered
    assert rendered.endswith("\n")
    assert not rendered.endswith("\n\n")


def test_render_is_deterministic_and_keys_are_sorted() -> None:
    renderer = JsonRenderer()
    report = _report()

    first = renderer.render(report)
    second = renderer.render(report)
    top_level_keys = tuple(json.loads(first))

    assert vars(renderer) == {}
    assert first == second
    assert top_level_keys == tuple(sorted(top_level_keys))
    assert first.index('"score"') < first.index('"warnings"')


@pytest.mark.parametrize(
    "invalid_report",
    (
        None,
        "not a report",
        Report(title="Broken", metadata=None),  # type: ignore[arg-type]
    ),
)
def test_render_rejects_invalid_report(invalid_report: object) -> None:
    with pytest.raises(ValueError, match="report"):
        JsonRenderer().render(invalid_report)  # type: ignore[arg-type]
