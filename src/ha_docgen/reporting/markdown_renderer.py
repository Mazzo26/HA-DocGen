"""Stateless GitHub Markdown rendering for reporting models.

Converts an immutable ``Report`` into deterministic Markdown. The
renderer performs no generation, logging, CLI handling or filesystem I/O.
"""

from __future__ import annotations

from collections.abc import Sequence

from .models import Report, ReportSection


class MarkdownRenderer:
    """Render a ``Report`` as GitHub-compatible Markdown."""

    def render(self, report: Report) -> str:
        """Return deterministic Markdown for ``report``."""
        if not isinstance(report, Report):
            raise TypeError("report must be a Report")

        introduction = [f"# {report.title}"]
        if report.description:
            introduction.extend(("", report.description))
        blocks = ["\n".join(introduction)]
        if report.summary:
            blocks.append(_subsection("Summary", report.summary))
        blocks.append(_metadata_block(report))
        blocks.extend(_section_block(section) for section in report.sections)
        if report.statistics:
            blocks.append(_statistics_block(report))
        if report.recommendations:
            blocks.append(_recommendations_block(report.recommendations))
        return "\n\n---\n\n".join(blocks) + "\n"


def _subsection(title: str, content: str) -> str:
    """Render a level-two heading followed by paragraph content."""
    return f"## {title}\n\n{content}"


def _metadata_block(report: Report) -> str:
    """Render report metadata in a stable key/value table."""
    metadata = report.metadata
    rows = (
        ("Generated at", metadata.generated_at.isoformat()),
        ("Version", metadata.version),
        ("Project path", str(metadata.project_path)),
        ("Execution time", f"{metadata.execution_time:g}s"),
    )
    return f"## Metadata\n\n{_table(('Field', 'Value'), rows)}"


def _statistics_block(report: Report) -> str:
    """Render sorted report statistics as a key/value table."""
    rows = tuple((key, str(value)) for key, value in sorted(report.statistics.items()))
    return f"## Statistics\n\n{_table(('Statistic', 'Value'), rows)}"


def _section_block(section: ReportSection) -> str:
    """Render one report section with severity, description and items."""
    lines = [
        f"## {section.title}",
        "",
        f"### Severity: {section.severity.value.title()}",
    ]
    if section.description:
        lines.extend(("", section.description))
    if section.items:
        lines.extend(("", _items(section.items)))
    return "\n".join(lines)


def _items(items: tuple[str, ...]) -> str:
    """Render text items as bullets while preserving fenced code blocks."""
    blocks: list[str] = []
    for item in items:
        if _is_fenced_code(item):
            blocks.append(item)
        else:
            blocks.append(_bullet(item))
    return "\n".join(blocks)


def _is_fenced_code(value: str) -> bool:
    """Return whether an item is a complete fenced Markdown code block."""
    stripped = value.strip()
    return stripped.startswith("```") and stripped.endswith("```")


def _bullet(value: str) -> str:
    """Render one possibly multiline bullet item."""
    lines = value.splitlines() or [""]
    return "\n  ".join((f"- {lines[0]}", *lines[1:]))


def _recommendations_block(recommendations: tuple[str, ...]) -> str:
    """Render recommendations as a numbered list."""
    lines = ["## Recommendations", ""]
    lines.extend(
        f"{index}. {recommendation}"
        for index, recommendation in enumerate(recommendations, start=1)
    )
    return "\n".join(lines)


def _table(
    headers: tuple[str, ...],
    rows: Sequence[tuple[str, ...]],
) -> str:
    """Render a GitHub Markdown table with escaped cells."""
    header = "| " + " | ".join(_table_cell(value) for value in headers) + " |"
    separator = "| " + " | ".join("---" for _ in headers) + " |"
    body = tuple("| " + " | ".join(_table_cell(value) for value in row) + " |" for row in rows)
    return "\n".join((header, separator, *body))


def _table_cell(value: object | None) -> str:
    """Return one escaped table cell; empty values become empty strings."""
    if value is None:
        return ""
    escaped = str(value).replace("|", r"\|")
    return escaped.replace("\r\n", "<br>").replace("\n", "<br>")
