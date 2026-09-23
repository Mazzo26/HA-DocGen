"""Build an Architecture Report from existing project analysis.

Aggregates ``ProjectTree``, ``YamlRepository`` and ``DependencyGraph``
data into immutable report models. Performs no scanning, parsing,
rendering, filesystem writes or architecture validation.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..graph import DependencyGraph, GraphEdge
from ..project import ProjectTree
from ..relationships import ObjectType
from ..yaml import YamlRepository
from .models import Report, ReportMetadata, ReportSection, Severity

_TITLE = "Architecture Report"
_DESCRIPTION = "Project architecture derived from existing DocGen analysis."
_ArchitectureData = tuple[
    tuple[str, ...],
    tuple[tuple[ObjectType, str], ...],
    tuple[ObjectType, ...],
    tuple[GraphEdge, ...],
    tuple[GraphEdge, ...],
    tuple[str, ...],
    tuple[GraphEdge, ...],
    tuple[str, ...],
]


class ArchitectureReportGenerator:
    """Generate an Architecture Report from already-analysed project data."""

    def generate(
        self,
        project_tree: ProjectTree,
        yaml_repository: YamlRepository,
        dependency_graph: DependencyGraph,
        metadata: ReportMetadata,
        layer_violations: tuple[str, ...] = (),
    ) -> Report:
        """Return an output-independent Architecture Report."""
        data = _architecture_data(
            yaml_repository,
            dependency_graph,
            layer_violations,
        )
        statistics = _statistics(
            project_tree,
            yaml_repository,
            *data,
        )
        return _create_report(yaml_repository, metadata, data, statistics)


def _architecture_data(
    repository: YamlRepository,
    graph: DependencyGraph,
    layer_violations: tuple[str, ...],
) -> _ArchitectureData:
    """Collect derived architecture data without scanning or parsing."""
    modules = _module_names(repository)
    components = _components(modules, graph)
    internal, external = _dependencies(graph)
    return (
        modules,
        components,
        _layers(components),
        internal,
        external,
        tuple(sorted(set(layer_violations))),
        tuple(edge for edge in graph.edges if _invalid(edge)),
        _missing_information(repository),
    )


def _create_report(
    repository: YamlRepository,
    metadata: ReportMetadata,
    data: _ArchitectureData,
    statistics: Mapping[str, int | float],
) -> Report:
    """Create the Report from concrete architecture aggregation results."""
    modules, components, layers, internal, external, violations, invalid, missing = data
    return Report(
        title=_TITLE,
        metadata=metadata,
        description=_DESCRIPTION,
        sections=_sections(
            repository,
            modules,
            components,
            layers,
            internal,
            external,
            violations,
            invalid,
            missing,
            statistics,
        ),
        statistics=statistics,
        recommendations=_recommendations(violations, invalid, missing),
        summary=_summary(statistics),
    )


def _module_names(repository: YamlRepository) -> tuple[str, ...]:
    """Return sorted package names representing detected modules."""
    names = {package.name for package in repository.packages}
    names.update(structure.package.name for structure in repository.package_structures)
    return tuple(sorted(names))


def _components(
    modules: tuple[str, ...],
    graph: DependencyGraph,
) -> tuple[tuple[ObjectType, str], ...]:
    """Return deduplicated architectural component identities."""
    components = {(node.object_type, node.object_id) for node in graph.nodes}
    components.update((ObjectType.PACKAGE, name) for name in modules)
    return tuple(sorted(components, key=lambda item: (item[0].value, item[1])))


def _layers(
    components: tuple[tuple[ObjectType, str], ...],
) -> tuple[ObjectType, ...]:
    """Return object types represented by the architecture components."""
    return tuple(sorted({item[0] for item in components}, key=lambda item: item.value))


def _missing_information(repository: YamlRepository) -> tuple[str, ...]:
    """Identify incomplete package-to-structure architecture information."""
    packages = {package.name for package in repository.packages}
    structures = {structure.package.name for structure in repository.package_structures}
    missing = {f"Package structure missing for module: {name}" for name in packages - structures}
    missing.update(
        f"Package registration missing for module: {name}" for name in structures - packages
    )
    return tuple(sorted(missing))


def _dependencies(
    graph: DependencyGraph,
) -> tuple[tuple[GraphEdge, ...], tuple[GraphEdge, ...]]:
    """Split graph edges into internal and available external dependencies."""
    external = tuple(edge for edge in graph.edges if _external(edge))
    internal = tuple(edge for edge in graph.edges if not _external(edge))
    return internal, external


def _external(edge: GraphEdge) -> bool:
    """Return whether an edge reaches an external integration surface."""
    return (
        edge.source.object_type is ObjectType.MQTT_TOPIC
        or edge.target.object_type is ObjectType.MQTT_TOPIC
    )


def _invalid(edge: GraphEdge) -> bool:
    """Return whether an existing dependency has an empty identity."""
    return not edge.source.object_id.strip() or not edge.target.object_id.strip()


def _analysed_file_count(project_tree: ProjectTree) -> int:
    """Count unique files already present in the supplied ProjectTree."""
    return len(
        {
            project_file.relative_path
            for folder in project_tree.folders
            for project_file in folder.files
        }
    )


def _statistics(
    project_tree: ProjectTree,
    repository: YamlRepository,
    modules: tuple[str, ...],
    components: tuple[tuple[ObjectType, str], ...],
    layers: tuple[ObjectType, ...],
    internal: tuple[GraphEdge, ...],
    external: tuple[GraphEdge, ...],
    violations: tuple[str, ...],
    invalid: tuple[GraphEdge, ...],
    missing: tuple[str, ...],
) -> dict[str, int | float]:
    """Build deterministic architecture statistics."""
    return {
        "total_analyzed_files": _analysed_file_count(project_tree),
        "total_architecture_components": len(components),
        "total_architecture_layers": len(layers),
        "total_dependency_relationships": len(internal) + len(external),
        "total_external_dependencies": len(external),
        "total_internal_dependencies": len(internal),
        "total_invalid_dependencies": len(invalid),
        "total_layer_violations": len(violations),
        "total_missing_architecture_information": len(missing),
        "total_modules": len(modules),
        "total_packages": len(repository.packages),
    }


def _summary(statistics: Mapping[str, int | float]) -> str:
    """Build the overall architecture summary."""
    if not any(statistics.values()):
        return "No architecture information is available."
    return (
        f"Architecture overview: {statistics['total_modules']} module(s), "
        f"{statistics['total_architecture_layers']} layer(s), "
        f"{statistics['total_analyzed_files']} analysed file(s), and "
        f"{statistics['total_dependency_relationships']} dependency "
        "relationship(s)."
    )


def _sections(
    repository: YamlRepository,
    modules: tuple[str, ...],
    components: tuple[tuple[ObjectType, str], ...],
    layers: tuple[ObjectType, ...],
    internal: tuple[GraphEdge, ...],
    external: tuple[GraphEdge, ...],
    violations: tuple[str, ...],
    invalid: tuple[GraphEdge, ...],
    missing: tuple[str, ...],
    statistics: Mapping[str, int | float],
) -> tuple[ReportSection, ...]:
    """Build only report sections backed by available analysed data."""
    if not any(statistics.values()):
        return ()
    sections = [_summary_section(statistics)]
    architecture = _architecture_section(repository, modules, components, layers)
    if architecture.items:
        sections.append(architecture)
    if internal or external:
        sections.append(_dependency_section(internal, external))
    if violations or invalid or missing:
        sections.append(_validation_section(violations, invalid, missing))
    sections.append(_statistics_section(statistics))
    return tuple(sections)


def _summary_section(
    statistics: Mapping[str, int | float],
) -> ReportSection:
    """Build the architecture count overview section."""
    return ReportSection(
        title="Summary",
        severity=Severity.INFO,
        items=(
            f"Modules: {statistics['total_modules']}",
            f"Architectural layers: {statistics['total_architecture_layers']}",
            f"Analysed files: {statistics['total_analyzed_files']}",
        ),
    )


def _architecture_section(
    repository: YamlRepository,
    modules: tuple[str, ...],
    components: tuple[tuple[ObjectType, str], ...],
    layers: tuple[ObjectType, ...],
) -> ReportSection:
    """Build modules, layers, package organisation and components."""
    items = [f"Module: {name}" for name in modules]
    items.extend(_layer_items(layers, components))
    items.extend(_package_items(repository))
    items.extend(
        f"Component: {object_type.value}:{object_id}" for object_type, object_id in components
    )
    return ReportSection(
        title="Architecture",
        severity=Severity.INFO,
        items=tuple(items),
    )


def _layer_items(
    layers: tuple[ObjectType, ...],
    components: tuple[tuple[ObjectType, str], ...],
) -> tuple[str, ...]:
    """Describe each available layer with its component count."""
    return tuple(
        f"Layer: {layer.value} " f"({sum(item[0] is layer for item in components)} component(s))"
        for layer in layers
    )


def _package_items(repository: YamlRepository) -> tuple[str, ...]:
    """Describe available package organisation from parsed structures."""
    structures = sorted(
        repository.package_structures,
        key=lambda item: item.package.name,
    )
    return tuple(
        f"Package: {structure.package.name} "
        f"({', '.join(sorted(section.name for section in structure.sections))})"
        for structure in structures
    )


def _dependency_section(
    internal: tuple[GraphEdge, ...],
    external: tuple[GraphEdge, ...],
) -> ReportSection:
    """Build internal and available external dependency items."""
    items = tuple(f"Internal: {_format_edge(edge)}" for edge in internal) + tuple(
        f"External: {_format_edge(edge)}" for edge in external
    )
    return ReportSection(
        title="Dependencies",
        severity=Severity.INFO,
        items=items,
    )


def _format_edge(edge: GraphEdge) -> str:
    """Format one existing dependency relationship."""
    return (
        f"{edge.source.object_type.value}:{edge.source.object_id} "
        f"{edge.relationship_type.value} "
        f"{edge.target.object_type.value}:{edge.target.object_id}"
    )


def _validation_section(
    violations: tuple[str, ...],
    invalid: tuple[GraphEdge, ...],
    missing: tuple[str, ...],
) -> ReportSection:
    """Build architecture validation findings from available data."""
    items = tuple(f"Layer violation: {item}" for item in violations)
    items += tuple(f"Invalid dependency: {_format_edge(edge)}" for edge in invalid)
    items += tuple(f"Missing information: {item}" for item in missing)
    severity = Severity.ERROR if violations or invalid else Severity.WARNING
    return ReportSection(
        title="Architecture Validation",
        severity=severity,
        items=items,
    )


def _statistics_section(
    statistics: Mapping[str, int | float],
) -> ReportSection:
    """Build a plain-text statistics section."""
    items = tuple(f"{key}: {value}" for key, value in sorted(statistics.items()))
    return ReportSection(
        title="Statistics",
        severity=Severity.INFO,
        items=items,
    )


def _recommendations(
    violations: tuple[str, ...],
    invalid: tuple[GraphEdge, ...],
    missing: tuple[str, ...],
) -> tuple[str, ...]:
    """Derive recommendations only from present architecture findings."""
    recommendations: list[str] = []
    if violations:
        recommendations.append("Resolve detected architecture layer violations.")
    if invalid:
        recommendations.append("Correct invalid dependency relationships.")
    if missing:
        recommendations.append("Complete missing architectural information for detected modules.")
    return tuple(recommendations)
