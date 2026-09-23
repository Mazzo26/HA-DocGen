"""Build a Dependency Report from an existing DependencyGraph.

Aggregates already-built graph edges into immutable report models.
Performs no dependency analysis, cycle detection, scanning, parsing,
rendering or filesystem writes.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..graph import DependencyGraph, GraphEdge
from ..relationships import ObjectType
from .models import Report, ReportMetadata, ReportSection, Severity

_TITLE = "Dependency Report"
_DESCRIPTION = "Dependency overview derived from the existing DependencyGraph."


class DependencyReportGenerator:
    """Generate a Dependency Report from an already-built DependencyGraph."""

    def generate(
        self,
        dependency_graph: DependencyGraph,
        metadata: ReportMetadata,
        circular_dependencies: tuple[str, ...] = (),
    ) -> Report:
        """Return an output-independent Dependency Report."""
        circular = tuple(sorted(set(circular_dependencies)))
        internal, external = _dependencies(dependency_graph)
        statistics = _statistics(internal, external, circular)
        return Report(
            title=_TITLE,
            metadata=metadata,
            description=_DESCRIPTION,
            sections=_sections(internal, external, circular, statistics),
            statistics=statistics,
            recommendations=_recommendations(statistics, circular),
            summary=_summary(statistics),
        )


def _dependencies(
    graph: DependencyGraph,
) -> tuple[tuple[GraphEdge, ...], tuple[GraphEdge, ...]]:
    """Split graph edges into internal and external dependencies."""
    external = tuple(edge for edge in graph.edges if _external(edge))
    internal = tuple(edge for edge in graph.edges if not _external(edge))
    return internal, external


def _external(edge: GraphEdge) -> bool:
    """Return whether an edge reaches an external MQTT topic surface."""
    return (
        edge.source.object_type is ObjectType.MQTT_TOPIC
        or edge.target.object_type is ObjectType.MQTT_TOPIC
    )


def _statistics(
    internal: tuple[GraphEdge, ...],
    external: tuple[GraphEdge, ...],
    circular: tuple[str, ...],
) -> dict[str, int | float]:
    """Build dependency counts from existing graph edges."""
    return {
        "total_circular_dependencies": len(circular),
        "total_dependency_relations": len(internal) + len(external),
        "total_external_dependencies": len(external),
        "total_internal_dependencies": len(internal),
    }


def _summary(statistics: Mapping[str, int | float]) -> str:
    """Build the overall dependency summary."""
    if statistics["total_dependency_relations"] == 0 and (
        statistics["total_circular_dependencies"] == 0
    ):
        return "No dependency information is available."
    return (
        f"Dependency overview: {statistics['total_dependency_relations']} "
        f"relation(s) "
        f"({statistics['total_internal_dependencies']} internal, "
        f"{statistics['total_external_dependencies']} external), "
        f"{statistics['total_circular_dependencies']} circular."
    )


def _sections(
    internal: tuple[GraphEdge, ...],
    external: tuple[GraphEdge, ...],
    circular: tuple[str, ...],
    statistics: Mapping[str, int | float],
) -> tuple[ReportSection, ...]:
    """Build summary, dependencies and statistics sections."""
    if all(value == 0 for value in statistics.values()):
        return ()
    sections = [_summary_section(statistics)]
    if internal or external or circular:
        sections.append(_dependencies_section(internal, external, circular))
    sections.append(_statistics_section(statistics))
    return tuple(sections)


def _summary_section(statistics: Mapping[str, int | float]) -> ReportSection:
    """Build the dependency count overview section."""
    return ReportSection(
        title="Summary",
        severity=Severity.INFO,
        items=(
            f"Dependency relations: {statistics['total_dependency_relations']}",
            f"Internal dependencies: {statistics['total_internal_dependencies']}",
            f"External dependencies: {statistics['total_external_dependencies']}",
            f"Circular dependencies: {statistics['total_circular_dependencies']}",
        ),
    )


def _dependencies_section(
    internal: tuple[GraphEdge, ...],
    external: tuple[GraphEdge, ...],
    circular: tuple[str, ...],
) -> ReportSection:
    """Build internal, external and already-detected circular dependencies."""
    items = tuple(f"Internal: {_format_edge(edge)}" for edge in internal)
    items += tuple(f"External: {_format_edge(edge)}" for edge in external)
    items += tuple(f"Circular: {item}" for item in circular)
    return ReportSection(
        title="Dependencies",
        severity=Severity.WARNING if circular else Severity.INFO,
        description="Internal, external and circular dependency relations.",
        items=items,
    )


def _format_edge(edge: GraphEdge) -> str:
    """Format one existing dependency relationship."""
    return (
        f"{edge.source.object_type.value}:{edge.source.object_id} "
        f"{edge.relationship_type.value} "
        f"{edge.target.object_type.value}:{edge.target.object_id}"
    )


def _statistics_section(statistics: Mapping[str, int | float]) -> ReportSection:
    """Build a plain-text statistics section."""
    return ReportSection(
        title="Statistics",
        severity=Severity.INFO,
        items=tuple(f"{key}: {value}" for key, value in sorted(statistics.items())),
    )


def _recommendations(
    statistics: Mapping[str, int | float],
    circular: tuple[str, ...],
) -> tuple[str, ...]:
    """Derive recommendations only from analysed dependency information."""
    recommendations: list[str] = []
    if circular:
        recommendations.append("Resolve detected circular dependencies.")
    if statistics["total_external_dependencies"] > 0:
        recommendations.append("Review external MQTT topic dependencies for operational impact.")
    return tuple(recommendations)
