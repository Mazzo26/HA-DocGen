"""Unit tests for DependencyReportGenerator."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ha_docgen.graph import DependencyGraphBuilder
from ha_docgen.relationships import (
    ObjectType,
    Relationship,
    RelationshipRepository,
    RelationshipType,
)
from ha_docgen.reporting import (
    DependencyReportGenerator,
    Report,
    ReportMetadata,
    ReportSection,
    Severity,
)
from tests.support import build_relationship


def _metadata() -> ReportMetadata:
    return ReportMetadata(
        generated_at=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
        version="0.2.0",
        project_path=Path("/config"),
        execution_time=0.25,
    )


def _generate(
    relationships: tuple[Relationship, ...] = (),
    circular_dependencies: tuple[str, ...] = (),
) -> Report:
    graph = DependencyGraphBuilder().build(RelationshipRepository(relationships))
    return DependencyReportGenerator().generate(
        graph,
        _metadata(),
        circular_dependencies,
    )


def _section(report: Report, title: str) -> ReportSection:
    return next(section for section in report.sections if section.title == title)


def test_empty_dependencies() -> None:
    report = _generate()
    assert isinstance(report, Report)
    assert report.title == "Dependency Report"
    assert report.summary == "No dependency information is available."
    assert report.sections == ()
    assert report.recommendations == ()
    assert all(value == 0 for value in report.statistics.values())


def test_internal_and_external_dependencies() -> None:
    report = _generate(
        (
            build_relationship(
                ObjectType.AUTOMATION,
                "morning",
                ObjectType.ENTITY,
                "light.kitchen",
            ),
            build_relationship(
                ObjectType.AUTOMATION,
                "publish",
                ObjectType.MQTT_TOPIC,
                "home/status",
                RelationshipType.PUBLISHES,
            ),
            build_relationship(
                ObjectType.MQTT_TOPIC,
                "home/command",
                ObjectType.ENTITY,
                "switch.pump",
                RelationshipType.USES,
            ),
        )
    )
    dependencies = _section(report, "Dependencies")
    assert dependencies.severity is Severity.INFO
    assert dependencies.items == (
        "Internal: automation:morning references entity:light.kitchen",
        "External: automation:publish publishes mqtt_topic:home/status",
        "External: mqtt_topic:home/command uses entity:switch.pump",
    )
    assert report.statistics["total_dependency_relations"] == 3
    assert report.statistics["total_internal_dependencies"] == 1
    assert report.statistics["total_external_dependencies"] == 2
    assert report.recommendations == (
        "Review external MQTT topic dependencies for operational impact.",
    )
    assert report.summary == (
        "Dependency overview: 3 relation(s) (1 internal, 2 external), 0 circular."
    )


def test_circular_dependencies_only_when_supplied() -> None:
    report = _generate(
        circular_dependencies=(
            "script.a → script.b → script.a",
            "script.a → script.b → script.a",
            "automation.loop",
        )
    )
    dependencies = _section(report, "Dependencies")
    assert dependencies.severity is Severity.WARNING
    assert dependencies.items == (
        "Circular: automation.loop",
        "Circular: script.a → script.b → script.a",
    )
    assert report.statistics["total_circular_dependencies"] == 2
    assert report.recommendations == ("Resolve detected circular dependencies.",)


def test_statistics_section_is_sorted() -> None:
    report = _generate(
        (
            build_relationship(
                ObjectType.SCRIPT,
                "notify",
                ObjectType.ENTITY,
                "notify.mobile",
            ),
        )
    )
    statistics = _section(report, "Statistics")
    assert statistics.items == tuple(sorted(statistics.items))
    summary = _section(report, "Summary")
    assert "Dependency relations: 1" in summary.items


def test_generator_is_stateless_deterministic_and_preserves_metadata() -> None:
    generator = DependencyReportGenerator()
    graph = DependencyGraphBuilder().build(
        RelationshipRepository(
            (
                build_relationship(
                    ObjectType.AUTOMATION,
                    "b",
                    ObjectType.ENTITY,
                    "light.b",
                ),
                build_relationship(
                    ObjectType.AUTOMATION,
                    "a",
                    ObjectType.ENTITY,
                    "light.a",
                ),
            )
        )
    )
    metadata = _metadata()
    first = generator.generate(graph, metadata)
    second = generator.generate(graph, metadata)
    assert first == second
    assert first.metadata is metadata
