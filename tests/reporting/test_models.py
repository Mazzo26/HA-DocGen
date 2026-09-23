"""Unit tests for reporting domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

import pytest

from tools.ha_docgen.reporting import (
    Report,
    ReportMetadata,
    ReportSection,
    Severity,
)


def _metadata(
    *,
    generated_at: datetime | None = None,
    version: str = "0.2.0",
    project_path: Path | None = None,
    execution_time: float = 1.25,
) -> ReportMetadata:
    return ReportMetadata(
        generated_at=generated_at or datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
        version=version,
        project_path=project_path or Path("/config"),
        execution_time=execution_time,
    )


def _section(
    *,
    title: str = "Findings",
    severity: Severity = Severity.WARNING,
    items: tuple[str, ...] = ("item-a",),
    description: str | None = "Optional notes",
) -> ReportSection:
    return ReportSection(
        title=title,
        severity=severity,
        items=items,
        description=description,
    )


def _report(
    *,
    title: str = "Health Report",
    metadata: ReportMetadata | None = None,
    description: str = "Overall health",
    sections: tuple[ReportSection, ...] | None = None,
    statistics: dict[str, int | float] | None = None,
    recommendations: tuple[str, ...] = ("Review warnings.",),
    summary: str = "Mostly healthy.",
) -> Report:
    return Report(
        title=title,
        metadata=metadata or _metadata(),
        description=description,
        sections=sections if sections is not None else (_section(),),
        statistics=statistics if statistics is not None else {"errors": 0, "warnings": 1},
        recommendations=recommendations,
        summary=summary,
    )


# --- Severity -----------------------------------------------------------------


def test_severity_members() -> None:
    assert set(Severity) == {Severity.INFO, Severity.WARNING, Severity.ERROR}
    assert Severity.INFO.value == "info"
    assert Severity.WARNING.value == "warning"
    assert Severity.ERROR.value == "error"


def test_severity_is_str() -> None:
    assert isinstance(Severity.INFO, str)
    assert Severity.ERROR == "error"


def test_severity_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        Severity("critical")


# --- ReportMetadata -----------------------------------------------------------


def test_metadata_creation() -> None:
    generated_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    metadata = _metadata(
        generated_at=generated_at,
        version="1.0.0",
        project_path=Path("/ha"),
        execution_time=0.5,
    )
    assert metadata.generated_at == generated_at
    assert metadata.version == "1.0.0"
    assert metadata.project_path == Path("/ha")
    assert metadata.execution_time == 0.5


def test_metadata_immutable() -> None:
    metadata = _metadata()
    with pytest.raises(FrozenInstanceError):
        metadata.version = "9.9.9"  # type: ignore[misc]


def test_metadata_equality() -> None:
    left = _metadata()
    right = _metadata()
    other = _metadata(version="9.0.0")
    assert left == right
    assert left != other
    assert hash(left) == hash(right)


# --- ReportSection ------------------------------------------------------------


def test_section_creation_with_description() -> None:
    section = _section(
        title="Errors",
        severity=Severity.ERROR,
        items=("a", "b"),
        description="Critical",
    )
    assert section.title == "Errors"
    assert section.severity is Severity.ERROR
    assert section.items == ("a", "b")
    assert section.description == "Critical"


def test_section_default_values() -> None:
    section = ReportSection(title="Info", severity=Severity.INFO)
    assert section.items == ()
    assert section.description is None


def test_section_items_coerced_to_tuple() -> None:
    section = ReportSection(
        title="List",
        severity=Severity.INFO,
        items=["one", "two"],  # type: ignore[arg-type]
    )
    assert section.items == ("one", "two")
    assert isinstance(section.items, tuple)


def test_section_immutable() -> None:
    section = _section()
    with pytest.raises(FrozenInstanceError):
        section.title = "Changed"  # type: ignore[misc]
    assert isinstance(section.items, tuple)
    with pytest.raises(AttributeError):
        section.items.append("x")  # type: ignore[attr-defined]


def test_section_equality() -> None:
    left = _section()
    right = _section()
    other = _section(title="Other")
    assert left == right
    assert left != other


# --- Report -------------------------------------------------------------------


def test_report_creation() -> None:
    metadata = _metadata()
    section = _section()
    report = _report(metadata=metadata, sections=(section,))
    assert report.title == "Health Report"
    assert report.description == "Overall health"
    assert report.metadata is metadata
    assert report.sections == (section,)
    assert report.statistics == MappingProxyType({"errors": 0, "warnings": 1})
    assert report.recommendations == ("Review warnings.",)
    assert report.summary == "Mostly healthy."


def test_report_default_values() -> None:
    report = Report(title="Empty", metadata=_metadata())
    assert report.description == ""
    assert report.sections == ()
    assert report.statistics == MappingProxyType({})
    assert report.recommendations == ()
    assert report.summary == ""


def test_report_statistics_sorted_and_frozen() -> None:
    report = Report(
        title="Stats",
        metadata=_metadata(),
        statistics={"zeta": 3, "alpha": 1, "mu": 2.5},
    )
    assert list(report.statistics.keys()) == ["alpha", "mu", "zeta"]
    assert isinstance(report.statistics, MappingProxyType)
    with pytest.raises(TypeError):
        report.statistics["alpha"] = 99  # type: ignore[index]


def test_report_collections_coerced_to_tuple() -> None:
    section = _section()
    report = Report(
        title="Coerce",
        metadata=_metadata(),
        sections=[section],  # type: ignore[arg-type]
        recommendations=["Do A", "Do B"],  # type: ignore[arg-type]
    )
    assert report.sections == (section,)
    assert report.recommendations == ("Do A", "Do B")
    assert isinstance(report.sections, tuple)
    assert isinstance(report.recommendations, tuple)


def test_report_immutable() -> None:
    report = _report()
    with pytest.raises(FrozenInstanceError):
        report.title = "Changed"  # type: ignore[misc]
    assert isinstance(report.recommendations, tuple)
    with pytest.raises(AttributeError):
        report.recommendations.append("x")  # type: ignore[attr-defined]


def test_report_equality() -> None:
    left = _report()
    right = _report()
    other = _report(title="Other")
    assert left == right
    assert left != other
    assert left.metadata == right.metadata
    assert left.sections == right.sections
    assert dict(left.statistics) == dict(right.statistics)


def test_report_replace_preserves_immutability() -> None:
    original = _report()
    updated = replace(original, summary="Updated summary.")
    assert original.summary == "Mostly healthy."
    assert updated.summary == "Updated summary."
    assert updated.title == original.title


def test_report_supports_nested_reuse_for_future_types() -> None:
    """Same models can represent distinct report kinds via content only."""
    health = _report(title="Health Report", summary="OK")
    inventory = _report(
        title="Inventory Report",
        description="Entity inventory",
        sections=(
            ReportSection(
                title="Entities",
                severity=Severity.INFO,
                items=("light.kitchen", "sensor.temp"),
            ),
        ),
        statistics={"entities": 2},
        recommendations=(),
        summary="2 entities.",
    )
    assert health.title != inventory.title
    assert inventory.statistics["entities"] == 2
    assert inventory.sections[0].severity is Severity.INFO


def test_metadata_hashable_and_section_hashable() -> None:
    """Leaf models without MappingProxyType remain hashable."""
    metadata = _metadata()
    section = _section()
    assert hash(metadata) == hash(_metadata())
    assert hash(section) == hash(_section())
    assert {metadata, section}
