"""Build a Documentation Index Report from existing project data.

Aggregates immutable domain and documentation repositories into report
models. Performs no scanning, parsing, document generation, rendering
or filesystem access.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..automation import Automation
from ..document import DocumentRepository
from ..registries import HomeAssistantModel
from ..relationships import Relationship, RelationshipRepository
from ..yaml import YamlRepository
from .models import Report, ReportMetadata, ReportSection, Severity

_TITLE = "Documentation Index Report"
_DESCRIPTION = "Documentation overview derived from existing DocGen repositories."


class DocumentationIndexReportGenerator:
    """Generate a documentation index from already-analysed project data."""

    def generate(
        self,
        model: HomeAssistantModel,
        yaml_repository: YamlRepository,
        document_repository: DocumentRepository,
        relationship_repository: RelationshipRepository,
        metadata: ReportMetadata,
    ) -> Report:
        """Return an output-independent Documentation Index Report."""
        statistics = _statistics(
            model,
            yaml_repository,
            document_repository,
            relationship_repository,
        )
        return Report(
            title=_TITLE,
            metadata=metadata,
            description=_DESCRIPTION,
            sections=_sections(
                model,
                yaml_repository,
                document_repository,
                relationship_repository,
                statistics,
            ),
            statistics=statistics,
            recommendations=_recommendations(statistics),
            summary=_summary(statistics),
        )


def _statistics(
    model: HomeAssistantModel,
    yaml_repository: YamlRepository,
    document_repository: DocumentRepository,
    relationship_repository: RelationshipRepository,
) -> dict[str, int | float]:
    """Build documentation statistics from existing repository contents."""
    titles = {_normalise_title(document.title) for document in document_repository.documents}
    source_counts = _source_counts(model, yaml_repository)
    statistics: dict[str, int | float] = {
        **source_counts,
        "total_documentation_objects": sum(source_counts.values()),
        "total_cross_references": len(relationship_repository.relationships),
        "total_generated_documents": len(document_repository.documents),
        "total_index_entries": len(document_repository.documents),
        "total_documented_automations": _documented_automations(
            yaml_repository.automations, titles
        ),
        "total_documented_entities": sum(
            _normalise_title(f"Entity: {entity.entity_id}") in titles for entity in model.entities
        ),
        "total_documented_packages": sum(
            _normalise_title(f"Package: {package.name}") in titles
            for package in yaml_repository.packages
        ),
    }
    return statistics


def _source_counts(
    model: HomeAssistantModel,
    repository: YamlRepository,
) -> dict[str, int]:
    """Count documentation source objects already known by DocGen."""
    integrations = {entry.domain for entry in model.config_entries if entry.domain}
    return {
        "total_automations": len(repository.automations),
        "total_entities": len(model.entities),
        "total_helpers": len(repository.helpers),
        "total_integrations": len(integrations),
        "total_packages": len(repository.packages),
        "total_scripts": len(repository.scripts),
    }


def _documented_automations(
    automations: tuple[Automation, ...],
    titles: set[str],
) -> int:
    """Count automations with a matching generated document title."""
    return sum(
        _normalise_title(_automation_title(automation)) in titles for automation in automations
    )


def _normalise_title(title: str) -> str:
    """Return a case-insensitive title without surrounding whitespace."""
    return title.strip().casefold()


def _automation_title(automation: Automation) -> str:
    """Return the title used by the existing automation document generator."""
    label = automation.alias if automation.alias is not None else automation.id
    return f"Automation: {label}"


def _summary(statistics: Mapping[str, int | float]) -> str:
    """Build the overall documentation summary."""
    if (
        statistics["total_documentation_objects"] == 0
        and statistics["total_generated_documents"] == 0
    ):
        return "No documentation information is available."
    index_entries = int(statistics["total_index_entries"])
    index_label = "entry" if index_entries == 1 else "entries"
    return (
        f"Documentation overview: {statistics['total_documentation_objects']} "
        f"known object(s), {statistics['total_generated_documents']} generated "
        f"document(s), and {index_entries} index {index_label}."
    )


def _sections(
    model: HomeAssistantModel,
    yaml_repository: YamlRepository,
    document_repository: DocumentRepository,
    relationship_repository: RelationshipRepository,
    statistics: Mapping[str, int | float],
) -> tuple[ReportSection, ...]:
    """Build only sections backed by available documentation data."""
    if not any(statistics.values()) and not relationship_repository.relationships:
        return ()
    sections = [_summary_section(statistics)]
    inventory = _inventory_items(model, yaml_repository, document_repository)
    if inventory:
        sections.append(_inventory_section(inventory))
    if relationship_repository.relationships:
        sections.append(_cross_reference_section(relationship_repository.relationships))
    sections.append(_statistics_section(statistics))
    return tuple(sections)


def _summary_section(statistics: Mapping[str, int | float]) -> ReportSection:
    """Build the documentation count overview section."""
    return ReportSection(
        title="Summary",
        severity=Severity.INFO,
        description="Documentation overview from existing DocGen information.",
        items=(
            f"Documentation objects: {statistics['total_documentation_objects']}",
            f"Generated documents: {statistics['total_generated_documents']}",
            f"Index entries: {statistics['total_index_entries']}",
        ),
    )


def _inventory_items(
    model: HomeAssistantModel,
    repository: YamlRepository,
    document_repository: DocumentRepository,
) -> tuple[str, ...]:
    """List known documentation sources, generated documents and index entries."""
    items = [f"Package: {package.name}" for package in repository.packages]
    items.extend(f"Entity: {entity.entity_id}" for entity in model.entities)
    items.extend(
        f"Automation: {_automation_label(automation)}" for automation in repository.automations
    )
    items.extend(
        f"Script: {script.id or script.alias or '(unnamed)'}" for script in repository.scripts
    )
    items.extend(f"Helper: {helper.type}.{helper.id}" for helper in repository.helpers)
    items.extend(
        f"Integration: {domain}"
        for domain in sorted({entry.domain for entry in model.config_entries if entry.domain})
    )
    for document in document_repository.documents:
        items.extend(
            (f"Generated documentation: {document.title}", f"Index entry: {document.title}")
        )
    return tuple(sorted(items))


def _automation_label(automation: Automation) -> str:
    """Return a stable automation inventory label."""
    return automation.id or automation.alias or "(unnamed)"


def _inventory_section(items: tuple[str, ...]) -> ReportSection:
    """Build the documentation inventory section."""
    return ReportSection(
        title="Documentation Inventory",
        severity=Severity.INFO,
        description="Documentation sources and generated index entries.",
        items=items,
    )


def _cross_reference_section(
    relationships: tuple[Relationship, ...],
) -> ReportSection:
    """Build cross references from already-analysed relationships."""
    return ReportSection(
        title="Cross References",
        severity=Severity.INFO,
        items=tuple(_format_relationship(relationship) for relationship in relationships),
    )


def _format_relationship(relationship: Relationship) -> str:
    """Format one existing relationship as a documentation cross reference."""
    return (
        f"{relationship.source_type.value}:{relationship.source_id} "
        f"{relationship.relationship_type.value} "
        f"{relationship.target_type.value}:{relationship.target_id}"
    )


def _statistics_section(
    statistics: Mapping[str, int | float],
) -> ReportSection:
    """Build a plain-text statistics section."""
    return ReportSection(
        title="Statistics",
        severity=Severity.INFO,
        items=tuple(f"{key}: {value}" for key, value in sorted(statistics.items())),
    )


def _recommendations(statistics: Mapping[str, int | float]) -> tuple[str, ...]:
    """Recommend documentation only for demonstrably undocumented objects."""
    recommendations: list[str] = []
    _append_gap_recommendation(recommendations, statistics, "packages")
    _append_gap_recommendation(recommendations, statistics, "entities")
    _append_gap_recommendation(recommendations, statistics, "automations")
    return tuple(recommendations)


def _append_gap_recommendation(
    recommendations: list[str],
    statistics: Mapping[str, int | float],
    object_name: str,
) -> None:
    """Append a recommendation when source and documented counts differ."""
    total = int(statistics[f"total_{object_name}"])
    documented = int(statistics[f"total_documented_{object_name}"])
    missing = total - documented
    if missing > 0:
        label = {
            "automations": "automation",
            "entities": "entity",
            "packages": "package",
        }.get(object_name, object_name)
        if missing != 1:
            label = object_name
        recommendations.append(f"Generate documentation for {missing} undocumented {label}.")
