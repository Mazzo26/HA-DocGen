"""Unit tests for ArchitectureReportGenerator."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ha_docgen.graph import DependencyGraphBuilder
from ha_docgen.packages import Package, PackageStructure, Section
from ha_docgen.project import ProjectFile, ProjectFolder, ProjectTree
from ha_docgen.relationships import (
    ObjectType,
    Relationship,
    RelationshipRepository,
    RelationshipType,
)
from ha_docgen.reporting import (
    ArchitectureReportGenerator,
    Report,
    ReportMetadata,
    ReportSection,
    Severity,
)
from tests.support import build_relationship
from ha_docgen.yaml import YamlDocument, YamlRepository


def _metadata() -> ReportMetadata:
    return ReportMetadata(
        generated_at=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
        version="0.2.0",
        project_path=Path("/config"),
        execution_time=0.25,
    )


def _package(name: str) -> Package:
    path = Path(f"/config/packages/{name}.yaml")
    return Package(
        name=name,
        path=path,
        document=YamlDocument(path=path, text="", data={}),
    )


def _repository(
    *names: str,
    with_structures: bool = True,
) -> YamlRepository:
    packages = tuple(_package(name) for name in names)
    structures = ()
    if with_structures:
        structures = tuple(
            PackageStructure(
                package=package,
                sections=(
                    Section("script", {}),
                    Section("automation", []),
                ),
            )
            for package in packages
        )
    return YamlRepository(packages=packages, package_structures=structures)


def _project_tree(*relative_paths: str) -> ProjectTree:
    root = Path("/config")
    folder = ProjectFolder(
        name="config",
        path=root,
        relative_path=Path("."),
    )
    folder.files = [
        ProjectFile(
            name=Path(relative_path).name,
            path=root / relative_path,
            relative_path=Path(relative_path),
            extension=Path(relative_path).suffix,
            size=10,
            modified=datetime(2026, 9, 21, tzinfo=UTC),
        )
        for relative_path in relative_paths
    ]
    return ProjectTree(root=root, folders=[folder])


def _generate(
    repository: YamlRepository | None = None,
    relationships: tuple[Relationship, ...] = (),
    project_tree: ProjectTree | None = None,
    layer_violations: tuple[str, ...] = (),
) -> Report:
    graph = DependencyGraphBuilder().build(RelationshipRepository(relationships))
    return ArchitectureReportGenerator().generate(
        project_tree or _project_tree(),
        repository or YamlRepository(),
        graph,
        _metadata(),
        layer_violations,
    )


def _section(report: Report, title: str) -> ReportSection:
    return next(section for section in report.sections if section.title == title)


def test_empty_architecture() -> None:
    report = _generate()
    assert isinstance(report, Report)
    assert report.title == "Architecture Report"
    assert report.description == ("Project architecture derived from existing DocGen analysis.")
    assert report.summary == "No architecture information is available."
    assert report.sections == ()
    assert report.recommendations == ()
    assert all(value == 0 for value in report.statistics.values())


def test_single_module_architecture_and_package_organisation() -> None:
    report = _generate(
        _repository("lighting"),
        project_tree=_project_tree("packages/lighting.yaml"),
    )
    architecture = _section(report, "Architecture")
    assert "Module: lighting" in architecture.items
    assert "Layer: package (1 component(s))" in architecture.items
    assert "Package: lighting (automation, script)" in architecture.items
    assert "Component: package:lighting" in architecture.items
    assert report.statistics["total_modules"] == 1
    assert report.statistics["total_packages"] == 1


def test_multiple_modules_are_deduplicated_and_sorted() -> None:
    repository = _repository("zeta", "alpha")
    report = _generate(repository)
    architecture = _section(report, "Architecture")
    modules = tuple(item for item in architecture.items if item.startswith("Module:"))
    assert modules == ("Module: alpha", "Module: zeta")
    assert report.statistics["total_modules"] == 2


def test_internal_and_external_dependency_relationships() -> None:
    relationships = (
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
    report = _generate(relationships=relationships)
    dependencies = _section(report, "Dependencies")
    assert dependencies.items == (
        "Internal: automation:morning references entity:light.kitchen",
        "External: automation:publish publishes mqtt_topic:home/status",
        "External: mqtt_topic:home/command uses entity:switch.pump",
    )
    assert report.statistics["total_dependency_relationships"] == 3
    assert report.statistics["total_internal_dependencies"] == 1
    assert report.statistics["total_external_dependencies"] == 2


def test_layer_violations_are_sorted_deduplicated_and_recommended() -> None:
    report = _generate(
        layer_violations=(
            "YAML depends on Scanner",
            "Repository depends on Generator",
            "YAML depends on Scanner",
        )
    )
    validation = _section(report, "Architecture Validation")
    assert validation.severity is Severity.ERROR
    assert validation.items == (
        "Layer violation: Repository depends on Generator",
        "Layer violation: YAML depends on Scanner",
    )
    assert report.statistics["total_layer_violations"] == 2
    assert report.recommendations == ("Resolve detected architecture layer violations.",)


def test_invalid_dependencies_are_reported() -> None:
    relationships = (
        build_relationship(
            ObjectType.AUTOMATION,
            "",
            ObjectType.ENTITY,
            "light.kitchen",
        ),
        build_relationship(
            ObjectType.SCRIPT,
            "notify",
            ObjectType.ENTITY,
            " ",
        ),
    )
    report = _generate(relationships=relationships)
    validation = _section(report, "Architecture Validation")
    assert validation.severity is Severity.ERROR
    assert len(validation.items) == 2
    assert all(item.startswith("Invalid dependency:") for item in validation.items)
    assert report.statistics["total_invalid_dependencies"] == 2
    assert report.recommendations == ("Correct invalid dependency relationships.",)


def test_statistics_and_summary_match_analysed_data() -> None:
    report = _generate(
        _repository("core"),
        relationships=(
            build_relationship(
                ObjectType.PACKAGE,
                "core",
                ObjectType.AUTOMATION,
                "startup",
                RelationshipType.CONTAINS,
            ),
        ),
        project_tree=_project_tree(
            "packages/core.yaml",
            "automations.yaml",
        ),
    )
    assert report.summary == (
        "Architecture overview: 1 module(s), 2 layer(s), "
        "2 analysed file(s), and 1 dependency relationship(s)."
    )
    assert report.statistics["total_architecture_components"] == 2
    assert report.statistics["total_architecture_layers"] == 2
    statistics = _section(report, "Statistics")
    assert statistics.items == tuple(sorted(statistics.items))
    summary = _section(report, "Summary")
    assert summary.items == (
        "Modules: 1",
        "Architectural layers: 2",
        "Analysed files: 2",
    )


def test_missing_package_structure_produces_warning_and_recommendation() -> None:
    report = _generate(_repository("lighting", with_structures=False))
    validation = _section(report, "Architecture Validation")
    assert validation.severity is Severity.WARNING
    assert validation.items == (
        "Missing information: Package structure missing for module: lighting",
    )
    assert report.recommendations == (
        "Complete missing architectural information for detected modules.",
    )


def test_orphan_structure_is_reported_as_missing_registration() -> None:
    orphan = _package("orphan")
    repository = YamlRepository(package_structures=(PackageStructure(package=orphan, sections=()),))
    report = _generate(repository)
    architecture = _section(report, "Architecture")
    assert "Package: orphan ()" in architecture.items
    validation = _section(report, "Architecture Validation")
    assert validation.items == (
        "Missing information: Package registration missing for module: orphan",
    )
    assert report.statistics["total_modules"] == 1
    assert report.statistics["total_packages"] == 0


def test_file_only_data_omits_empty_architecture_sections() -> None:
    tree = _project_tree("configuration.yaml")
    tree.folders.append(
        ProjectFolder(
            name="duplicate",
            path=Path("/config/duplicate"),
            relative_path=Path("duplicate"),
            files=[tree.folders[0].files[0]],
        )
    )
    report = _generate(project_tree=tree)
    assert tuple(section.title for section in report.sections) == (
        "Summary",
        "Statistics",
    )
    assert report.statistics["total_analyzed_files"] == 1
    assert report.recommendations == ()


def test_generator_is_stateless_deterministic_and_preserves_metadata() -> None:
    generator = ArchitectureReportGenerator()
    repository = _repository("core")
    graph = DependencyGraphBuilder().build(RelationshipRepository())
    metadata = _metadata()
    first = generator.generate(_project_tree(), repository, graph, metadata)
    second = generator.generate(_project_tree(), repository, graph, metadata)
    assert first == second
    assert first.metadata is metadata
