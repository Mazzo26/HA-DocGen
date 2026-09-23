"""Immutable reporting data models.

Pure report structure only — no Markdown, HTML, JSON, console
formatting, renderers, generators, CLI, filesystem writes or Home
Assistant domain coupling.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType

_EMPTY_STATISTICS: Mapping[str, int | float] = MappingProxyType({})


class Severity(StrEnum):
    """Severity level of one report section.

    Generic levels only — no Home Assistant-specific members.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ReportMetadata:
    """Immutable provenance for one generated report.

    Holds when, where and how long generation took. Contains no
    formatting or filesystem logic.
    """

    generated_at: datetime
    version: str
    project_path: Path
    execution_time: float


@dataclass(frozen=True, slots=True)
class ReportSection:
    """Immutable report section with ordered plain-text items.

    ``description`` is optional. ``items`` stay format-neutral strings;
    renderers belong in later modules.
    """

    title: str
    severity: Severity
    items: tuple[str, ...] = ()
    description: str | None = None

    def __post_init__(self) -> None:
        """Freeze ``items`` as an immutable tuple."""
        object.__setattr__(self, "items", tuple(self.items))


@dataclass(frozen=True, slots=True)
class Report:
    """Immutable output-independent report tree.

    Shared foundation for every future report type (health,
    configuration, architecture, inventory, dependency, performance,
    documentation index). Serialisation formats belong in later
    modules.
    """

    title: str
    metadata: ReportMetadata
    description: str = ""
    sections: tuple[ReportSection, ...] = ()
    statistics: Mapping[str, int | float] = field(default=_EMPTY_STATISTICS)
    recommendations: tuple[str, ...] = ()
    summary: str = ""

    def __post_init__(self) -> None:
        """Freeze collections; sort statistics keys for determinism."""
        object.__setattr__(self, "sections", tuple(self.sections))
        object.__setattr__(self, "recommendations", tuple(self.recommendations))
        object.__setattr__(
            self,
            "statistics",
            MappingProxyType(dict(sorted(self.statistics.items()))),
        )
