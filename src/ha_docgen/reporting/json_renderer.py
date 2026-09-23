"""Stateless JSON rendering for reporting models.

Converts an immutable ``Report`` into deterministic, human-readable
JSON without generation, business logic or filesystem I/O.
"""

from __future__ import annotations

import json

from .models import Report, ReportSection


class JsonRenderer:
    """Render a ``Report`` as deterministic JSON."""

    def render(self, report: Report) -> str:
        """Return human-readable JSON for ``report``."""
        if not isinstance(report, Report):
            raise ValueError("report must be a Report")  # noqa: TRY004

        try:
            rendered = json.dumps(
                _report_data(report),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
        except (AttributeError, TypeError, ValueError) as error:
            raise ValueError("report is invalid") from error
        return f"{rendered}\n"


def _report_data(report: Report) -> dict[str, object]:
    """Convert all current Report fields to JSON-compatible values."""
    metadata = report.metadata
    return {
        "description": report.description,
        "metadata": {
            "execution_time": metadata.execution_time,
            "generated_at": metadata.generated_at.isoformat(),
            "project_path": str(metadata.project_path),
            "version": metadata.version,
        },
        "recommendations": list(report.recommendations),
        "sections": [_section_data(section) for section in report.sections],
        "statistics": dict(report.statistics),
        "summary": report.summary,
        "title": report.title,
    }


def _section_data(section: ReportSection) -> dict[str, object]:
    """Convert all current ReportSection fields to JSON-compatible values."""
    return {
        "description": section.description,
        "items": list(section.items),
        "severity": section.severity.value,
        "title": section.title,
    }
