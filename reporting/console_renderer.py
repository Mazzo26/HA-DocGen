"""Stateless plain-text rendering for reporting models.

Converts an immutable ``Report`` into deterministic console text. The
renderer performs no generation, logging, CLI handling or filesystem I/O.
"""

from __future__ import annotations

from collections.abc import Sequence

from .models import Report, ReportSection, Severity

_RESET = "\x1b[0m"
_BOLD = "\x1b[1m"
_SEVERITY_COLOURS = {
    Severity.INFO: "\x1b[36m",
    Severity.WARNING: "\x1b[33m",
    Severity.ERROR: "\x1b[31m",
}


class ConsoleRenderer:
    """Render a ``Report`` as plain text with optional ANSI colours."""

    def render(self, report: Report, *, colour: bool = False) -> str:
        """Return deterministic console text for ``report``."""
        if not isinstance(report, Report):
            raise TypeError("report must be a Report")

        blocks = [_heading(report.title, colour=colour)]
        if report.description:
            blocks.append(report.description)
        if report.summary:
            blocks.append(_summary_block(report.summary))
        blocks.append(_metadata_table(report))
        blocks.extend(_section_block(section, colour=colour) for section in report.sections)
        if report.statistics:
            blocks.append(_statistics_table(report))
        if report.recommendations:
            blocks.append(_recommendations_block(report.recommendations))
        return "\n\n".join(blocks) + "\n"


def _heading(title: str, *, colour: bool) -> str:
    """Render the report title and underline."""
    rendered_title = _colourise(title, _BOLD, enabled=colour)
    return f"{rendered_title}\n{'=' * len(title)}"


def _summary_block(summary: str) -> str:
    """Render a summary in a one-column table."""
    return _render_table(("Summary",), ((summary,),))


def _metadata_table(report: Report) -> str:
    """Render report metadata as a key/value table."""
    metadata = report.metadata
    rows = (
        ("Generated at", metadata.generated_at.isoformat()),
        ("Version", metadata.version),
        ("Project path", str(metadata.project_path)),
        ("Execution time", f"{metadata.execution_time:g}s"),
    )
    return _render_table(("Metadata", "Value"), rows)


def _section_block(section: ReportSection, *, colour: bool) -> str:
    """Render one report section with severity and items."""
    label = f"{section.title} [{section.severity.value.upper()}]"
    coloured_label = _colourise(
        label,
        _SEVERITY_COLOURS[section.severity],
        enabled=colour,
    )
    lines = [coloured_label, "-" * len(label)]
    if section.description:
        lines.append(section.description)
    lines.extend(f"- {item}" for item in section.items)
    return "\n".join(lines)


def _statistics_table(report: Report) -> str:
    """Render sorted report statistics as a key/value table."""
    rows = tuple((key, str(value)) for key, value in report.statistics.items())
    return _render_table(("Statistic", "Value"), rows)


def _recommendations_block(recommendations: tuple[str, ...]) -> str:
    """Render report recommendations as a plain-text list."""
    lines = ["Recommendations", "---------------"]
    lines.extend(f"- {recommendation}" for recommendation in recommendations)
    return "\n".join(lines)


def _render_table(
    headers: tuple[str, ...],
    rows: Sequence[tuple[str, ...]],
) -> str:
    """Render an ASCII table with deterministic column widths."""
    widths = tuple(
        max(len(headers[index]), *(len(row[index]) for row in rows))
        for index in range(len(headers))
    )
    border = _table_border(widths)
    lines = [border, _table_row(headers, widths), border]
    lines.extend(_table_row(row, widths) for row in rows)
    lines.append(border)
    return "\n".join(lines)


def _table_border(widths: tuple[int, ...]) -> str:
    """Render one ASCII table border."""
    return "+" + "+".join("-" * (width + 2) for width in widths) + "+"


def _table_row(values: tuple[str, ...], widths: tuple[int, ...]) -> str:
    """Render one padded ASCII table row."""
    cells = (f" {value:<{width}} " for value, width in zip(values, widths, strict=True))
    return "|" + "|".join(cells) + "|"


def _colourise(value: str, code: str, *, enabled: bool) -> str:
    """Wrap text in an ANSI code only when explicitly enabled."""
    if not enabled:
        return value
    return f"{code}{value}{_RESET}"
