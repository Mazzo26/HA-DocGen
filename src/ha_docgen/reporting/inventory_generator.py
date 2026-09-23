"""Build an Inventory Report from existing project analysis.

Aggregates ``HomeAssistantModel``, ``YamlRepository`` and ``ProjectTree``
into immutable report models. Performs no scanning, parsing, rendering
or filesystem writes.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..project import ProjectTree
from ..registries.home_assistant_model import HomeAssistantModel
from ..registries.models import ConfigEntry, Entity
from ..yaml.repository import YamlRepository
from .models import Report, ReportMetadata, ReportSection, Severity

_TITLE = "Inventory Report"
_DESCRIPTION = "Project inventory derived from existing DocGen analysis."


class InventoryReportGenerator:
    """Generate an Inventory Report from already-analysed project data."""

    def generate(
        self,
        model: HomeAssistantModel,
        yaml_repository: YamlRepository,
        project_tree: ProjectTree,
        metadata: ReportMetadata,
    ) -> Report:
        """Return an output-independent Inventory Report."""
        entities = _entity_ids(model.entities)
        integrations = _integration_names(model.config_entries)
        domains = _domain_names(model.entities)
        packages = _package_names(yaml_repository)
        files = _file_paths(project_tree)
        statistics = _statistics(entities, integrations, domains, packages, files)
        return Report(
            title=_TITLE,
            metadata=metadata,
            description=_DESCRIPTION,
            sections=_sections(entities, integrations, domains, packages, files, statistics),
            statistics=statistics,
            recommendations=_recommendations(statistics),
            summary=_summary(statistics),
        )


def _entity_ids(entities: tuple[Entity, ...]) -> tuple[str, ...]:
    """Return sorted unique entity identifiers."""
    return tuple(sorted({entity.entity_id for entity in entities if entity.entity_id}))


def _integration_names(entries: tuple[ConfigEntry, ...]) -> tuple[str, ...]:
    """Return sorted unique integration domains from config entries."""
    return tuple(sorted({entry.domain for entry in entries if entry.domain}))


def _domain_names(entities: tuple[Entity, ...]) -> tuple[str, ...]:
    """Return sorted unique entity domains."""
    return tuple(sorted({entity.domain for entity in entities if entity.domain}))


def _package_names(repository: YamlRepository) -> tuple[str, ...]:
    """Return sorted unique package names."""
    return tuple(sorted({package.name for package in repository.packages}))


def _file_paths(project_tree: ProjectTree) -> tuple[str, ...]:
    """Return sorted unique relative file paths from ProjectTree."""
    paths = {
        project_file.relative_path.as_posix()
        for folder in project_tree.folders
        for project_file in folder.files
    }
    return tuple(sorted(paths))


def _statistics(
    entities: tuple[str, ...],
    integrations: tuple[str, ...],
    domains: tuple[str, ...],
    packages: tuple[str, ...],
    files: tuple[str, ...],
) -> dict[str, int | float]:
    """Build inventory totals from collected identifiers."""
    return {
        "total_domains": len(domains),
        "total_entities": len(entities),
        "total_files": len(files),
        "total_integrations": len(integrations),
        "total_packages": len(packages),
    }


def _summary(statistics: Mapping[str, int | float]) -> str:
    """Build the overall inventory summary."""
    if all(value == 0 for value in statistics.values()):
        return "No inventory information is available."
    return (
        f"Inventory overview: {statistics['total_entities']} entities, "
        f"{statistics['total_integrations']} integration(s), "
        f"{statistics['total_domains']} domain(s), "
        f"{statistics['total_packages']} package(s), and "
        f"{statistics['total_files']} file(s)."
    )


def _sections(
    entities: tuple[str, ...],
    integrations: tuple[str, ...],
    domains: tuple[str, ...],
    packages: tuple[str, ...],
    files: tuple[str, ...],
    statistics: Mapping[str, int | float],
) -> tuple[ReportSection, ...]:
    """Build summary, inventory and statistics sections."""
    if all(value == 0 for value in statistics.values()):
        return ()
    return (
        _summary_section(statistics),
        _inventory_section(entities, integrations, domains, packages, files),
        _statistics_section(statistics),
    )


def _summary_section(statistics: Mapping[str, int | float]) -> ReportSection:
    """Build the inventory count overview section."""
    return ReportSection(
        title="Summary",
        severity=Severity.INFO,
        items=(
            f"Entities: {statistics['total_entities']}",
            f"Integrations: {statistics['total_integrations']}",
            f"Domains: {statistics['total_domains']}",
            f"Packages: {statistics['total_packages']}",
            f"Files: {statistics['total_files']}",
        ),
    )


def _inventory_section(
    entities: tuple[str, ...],
    integrations: tuple[str, ...],
    domains: tuple[str, ...],
    packages: tuple[str, ...],
    files: tuple[str, ...],
) -> ReportSection:
    """Build the inventory listing from existing analysed identifiers."""
    items = tuple(f"Entity: {entity_id}" for entity_id in entities)
    items += tuple(f"Integration: {name}" for name in integrations)
    items += tuple(f"Domain: {name}" for name in domains)
    items += tuple(f"Package: {name}" for name in packages)
    items += tuple(f"File: {path}" for path in files)
    return ReportSection(
        title="Inventory",
        severity=Severity.INFO,
        description="Entities, integrations, domains, packages and files.",
        items=items,
    )


def _statistics_section(statistics: Mapping[str, int | float]) -> ReportSection:
    """Build a plain-text statistics section."""
    return ReportSection(
        title="Statistics",
        severity=Severity.INFO,
        items=tuple(f"{key}: {value}" for key, value in sorted(statistics.items())),
    )


def _recommendations(statistics: Mapping[str, int | float]) -> tuple[str, ...]:
    """Derive recommendations only when directly supported by inventory data."""
    recommendations: list[str] = []
    if statistics["total_files"] > 0 and statistics["total_packages"] == 0:
        recommendations.append("Analysed files are present without detected packages.")
    if statistics["total_entities"] > 0 and statistics["total_integrations"] == 0:
        recommendations.append("Entities are present without detected config-entry integrations.")
    return tuple(recommendations)
