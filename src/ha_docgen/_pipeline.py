"""Internal production orchestration for complete project analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol, cast

from .automation import AutomationParser
from .config import ProjectConfig
from .constants import YAML_EXTENSIONS
from .dashboard import Dashboard, DashboardParser
from .document import (
    AutomationDocumentGenerator,
    ConfigurationDocumentGenerator,
    DashboardDocumentGenerator,
    Document,
    DocumentRepository,
    EntityDocumentGenerator,
    PackageDocumentGenerator,
)
from .graph import DependencyGraph, DependencyGraphBuilder
from .helper import HelperParser
from .packages import Package, PackageParser, PackageStructure
from .policy import ScanPolicy
from .project import (
    ProjectFile,
    ProjectTree,
    discover_project,
    project_files,
    root_yaml_files,
)
from .registries import (
    AreaRegistryParser,
    ConfigEntryRegistryParser,
    DeviceRegistryParser,
    EntityRegistryParser,
    FloorRegistryParser,
    HomeAssistantModel,
)
from .relationships import (
    AutomationRelationshipAnalyzer,
    DashboardRelationshipAnalyzer,
    DeviceRelationshipAnalyzer,
    EntityRelationshipAnalyzer,
    MQTTRelationshipAnalyzer,
    ObjectType,
    RelationshipRepository,
    ScriptRelationshipAnalyzer,
)
from .scanners import ScannerDiagnostics, scanner_diagnostics
from .scene import SceneParser
from .script import ScriptParser
from .storage import StorageInventory, StorageScanner
from .template import TemplateParser
from .validation import (
    AutomationValidator,
    EntityValidator,
    MQTTValidator,
    PackageValidator,
    ScriptValidator,
    ValidationRepository,
)
from .yaml import IncludeReference, YamlDocument, YamlLoader, YamlRepository, resolve_includes


class _RegistryParser[Result](Protocol):
    """Structural type for one registry parser."""

    def parse(self, path: Path) -> tuple[Result, ...]:
        """Parse one registry file."""


class _PackageDomainParser[Result](Protocol):
    """Structural type for one package-domain parser."""

    def parse(self, structure: PackageStructure) -> tuple[Result, ...]:
        """Parse one package structure."""


@dataclass(frozen=True, slots=True)
class _ProjectAnalysis:
    """Immutable outputs from one production project-analysis run."""

    project_tree: ProjectTree
    model: HomeAssistantModel
    yaml_repository: YamlRepository
    relationships: RelationshipRepository
    graph: DependencyGraph
    validations: ValidationRepository
    documents: DocumentRepository
    root_yaml: tuple[ProjectFile, ...]
    includes: tuple[IncludeReference, ...]
    diagnostics: ScannerDiagnostics


@dataclass(frozen=True, slots=True)
class _ConfiguredYaml:
    """YAML already loaded from one project tree, plus its scanner facts."""

    packages: tuple[Package, ...]
    dashboards: tuple[Dashboard, ...]
    includes: tuple[IncludeReference, ...]
    claimed: tuple[ProjectFile, ...]


def _build_project_analysis(config: ProjectConfig) -> _ProjectAnalysis:
    """Run the complete production analysis pipeline once."""
    tree = _discover_project(config)
    model = _build_registry_model(config, tree)
    loaded = _load_configured_yaml(config, tree)
    yaml_repository = _repository_from_yaml(loaded)
    relationships = _build_relationships(model, yaml_repository)
    graph = DependencyGraphBuilder().build(relationships)
    validations = _build_validations(model, yaml_repository, relationships)
    documents = _build_documents(model, yaml_repository, relationships)
    return _project_analysis(
        tree,
        model,
        yaml_repository,
        relationships,
        graph,
        validations,
        documents,
        loaded,
    )


def _project_analysis(
    tree: ProjectTree,
    model: HomeAssistantModel,
    repository: YamlRepository,
    relationships: RelationshipRepository,
    graph: DependencyGraph,
    validations: ValidationRepository,
    documents: DocumentRepository,
    loaded: _ConfiguredYaml,
) -> _ProjectAnalysis:
    """Assemble analysis from the existing tree and unchanged scanner outputs."""
    return _ProjectAnalysis(
        tree,
        model,
        repository,
        relationships,
        graph,
        validations,
        documents,
        root_yaml_files(tree),
        loaded.includes,
        scanner_diagnostics(tree, loaded.claimed),
    )


def _discover_project(config: ProjectConfig) -> ProjectTree:
    """Walk once, apply scan policy and build the central project tree."""
    return discover_project(config.root, ScanPolicy())


def _build_registry_model(
    config: ProjectConfig,
    tree: ProjectTree,
) -> HomeAssistantModel:
    """Parse configured registry files discovered in the project tree."""
    inventory = StorageScanner(config.storage).scan_from_tree(tree)
    return HomeAssistantModel(
        entities=_parse_registry(EntityRegistryParser(), inventory, config.entity_registry),
        devices=_parse_registry(DeviceRegistryParser(), inventory, config.device_registry),
        areas=_parse_registry(AreaRegistryParser(), inventory, config.area_registry),
        floors=_parse_registry(FloorRegistryParser(), inventory, config.floor_registry),
        config_entries=_parse_registry(
            ConfigEntryRegistryParser(),
            inventory,
            config.config_entries,
        ),
    )


def _parse_registry[Result](
    parser: _RegistryParser[Result],
    inventory: StorageInventory,
    configured_path: Path,
) -> tuple[Result, ...]:
    """Parse a configured registry only when discovery found that exact file."""
    discovered = inventory.get(configured_path.name)
    if discovered is None or discovered.path != configured_path:
        return ()
    return parser.parse(discovered.path)


def _load_configured_yaml(config: ProjectConfig, tree: ProjectTree) -> _ConfiguredYaml:
    """Load configured YAML once and keep the scanner facts from that load."""
    packages, package_includes, package_files = _load_packages(config, tree)
    dashboards, dashboard_includes, dashboard_files = _load_dashboards(config, tree)
    return _ConfiguredYaml(
        packages,
        dashboards,
        package_includes + dashboard_includes,
        package_files + dashboard_files,
    )


def _build_yaml_repository(config: ProjectConfig, tree: ProjectTree) -> YamlRepository:
    """Load and parse configured package and dashboard YAML from the tree."""
    return _repository_from_yaml(_load_configured_yaml(config, tree))


def _repository_from_yaml(loaded: _ConfiguredYaml) -> YamlRepository:
    """Parse package and dashboard YAML that was already loaded from the tree."""
    structures = tuple(PackageParser().parse(package) for package in loaded.packages)
    return YamlRepository(
        packages=loaded.packages,
        package_structures=structures,
        automations=_parse_structures(AutomationParser(), structures),
        scripts=_parse_structures(ScriptParser(), structures),
        scenes=_parse_structures(SceneParser(), structures),
        helpers=_parse_structures(HelperParser(), structures),
        dashboards=loaded.dashboards,
        templates=_parse_structures(TemplateParser(), structures),
    )


def _load_packages(
    config: ProjectConfig,
    tree: ProjectTree,
) -> tuple[tuple[Package, ...], tuple[IncludeReference, ...], tuple[ProjectFile, ...]]:
    """Load packages selected from the existing project tree."""
    loader = YamlLoader()
    files = _yaml_files(tree, config.packages)
    loaded = tuple(_load_package(config.root, tree, loader, item) for item in files)
    packages = tuple(package for package, _includes in loaded)
    includes = tuple(include for _package, batch in loaded for include in batch)
    return packages, includes, files


def _load_package(
    root: Path,
    tree: ProjectTree,
    loader: YamlLoader,
    project_file: ProjectFile,
) -> tuple[Package, tuple[IncludeReference, ...]]:
    """Load one package and resolve its includes against the same tree."""
    document = loader.load(project_file.path)
    return _package(root, document), resolve_includes(tree, document)


def _package(root: Path, document: YamlDocument) -> Package:
    """Create a package with deterministic project-relative provenance."""
    stable = _stable_document(root, document)
    return Package(name=document.path.stem, path=stable.path, document=stable)


def _load_dashboards(
    config: ProjectConfig,
    tree: ProjectTree,
) -> tuple[tuple[Dashboard, ...], tuple[IncludeReference, ...], tuple[ProjectFile, ...]]:
    """Load dashboards selected from the existing project tree."""
    loader = YamlLoader()
    parser = DashboardParser()
    files = _yaml_files(tree, config.dashboards)
    loaded = tuple(
        _load_dashboard(config.root, tree, loader, parser, item) for item in files
    )
    dashboards = tuple(dashboard for dashboard, _includes in loaded)
    includes = tuple(include for _dashboard, batch in loaded for include in batch)
    return dashboards, includes, files


def _load_dashboard(
    root: Path,
    tree: ProjectTree,
    loader: YamlLoader,
    parser: DashboardParser,
    project_file: ProjectFile,
) -> tuple[Dashboard, tuple[IncludeReference, ...]]:
    """Load one dashboard and resolve its includes against the same tree."""
    document = loader.load(project_file.path)
    stable = _stable_document(root, document)
    return parser.parse(stable), resolve_includes(tree, document)


def _stable_document(root: Path, document: YamlDocument) -> YamlDocument:
    """Replace an absolute source path with deterministic POSIX provenance."""
    relative = document.path.relative_to(root).as_posix()
    stable_path = cast(Path, PurePosixPath(relative))
    return YamlDocument(stable_path, document.text, document.data)


def _yaml_files(tree: ProjectTree, directory: Path) -> tuple[ProjectFile, ...]:
    """Return YAML files under one configured directory from the existing tree."""
    selected = (
        item
        for item in project_files(tree)
        if item.path.is_relative_to(directory) and item.extension in YAML_EXTENSIONS
    )
    return tuple(sorted(selected, key=lambda item: item.path.as_posix()))


def _parse_structures[Result](
    parser: _PackageDomainParser[Result],
    structures: tuple[PackageStructure, ...],
) -> tuple[Result, ...]:
    """Run one production parser over every package structure."""
    return tuple(
        item
        for structure in structures
        for item in parser.parse(structure)
    )


def _build_relationships(
    model: HomeAssistantModel,
    repository: YamlRepository,
) -> RelationshipRepository:
    """Run every production relationship analyzer and merge its output."""
    relationships = (
        *EntityRelationshipAnalyzer().analyze(model),
        *DeviceRelationshipAnalyzer().analyze(model),
        *AutomationRelationshipAnalyzer().analyze(repository.automations),
        *ScriptRelationshipAnalyzer().analyze(repository.scripts),
        *DashboardRelationshipAnalyzer().analyze(repository.dashboards),
        *MQTTRelationshipAnalyzer().analyze(
            repository.automations,
            repository.scripts,
            repository.helpers,
            repository.package_structures,
        ),
    )
    return RelationshipRepository(relationships)


def _build_validations(
    model: HomeAssistantModel,
    repository: YamlRepository,
    relationships: RelationshipRepository,
) -> ValidationRepository:
    """Run every production validator over analysed data."""
    results = (
        *EntityValidator().validate(model.entities, relationships),
        *AutomationValidator().validate(repository.automations, relationships),
        *ScriptValidator().validate(
            repository.scripts,
            relationships,
            model.entities,
        ),
        *PackageValidator().validate(repository),
        *MQTTValidator().validate(repository),
    )
    return ValidationRepository(results)


def _build_documents(
    model: HomeAssistantModel,
    repository: YamlRepository,
    relationships: RelationshipRepository,
) -> DocumentRepository:
    """Generate all documents from production analysis repositories."""
    documents = (
        *_package_documents(repository),
        *_entity_documents(model, relationships),
        *_automation_documents(repository, relationships),
        *_dashboard_documents(repository, relationships),
        ConfigurationDocumentGenerator().generate(
            model,
            repository,
            relationships,
        ),
    )
    return DocumentRepository(documents)


def _package_documents(repository: YamlRepository) -> tuple[Document, ...]:
    """Generate one document for each parsed package."""
    documents: list[Document] = []
    for package in repository.packages:
        structure = repository.get_package_structure(package.name)
        if structure is None:
            continue
        documents.append(
            PackageDocumentGenerator().generate(
                package,
                structure,
                repository.automations,
                repository.scripts,
                repository.scenes,
                repository.helpers,
                repository.templates,
            )
        )
    return tuple(documents)


def _entity_documents(
    model: HomeAssistantModel,
    relationships: RelationshipRepository,
) -> tuple[Document, ...]:
    """Generate one document for each registry entity."""
    return tuple(
        EntityDocumentGenerator().generate(
            entity,
            relationships.by_source(ObjectType.ENTITY, entity.entity_id),
        )
        for entity in model.entities
    )


def _automation_documents(
    repository: YamlRepository,
    relationships: RelationshipRepository,
) -> tuple[Document, ...]:
    """Generate one document for each parsed automation."""
    return tuple(
        AutomationDocumentGenerator().generate(
            automation,
            relationships.by_source(ObjectType.AUTOMATION, automation.id or ""),
        )
        for automation in repository.automations
    )


def _dashboard_documents(
    repository: YamlRepository,
    relationships: RelationshipRepository,
) -> tuple[Document, ...]:
    """Generate one document for each parsed dashboard."""
    return tuple(
        DashboardDocumentGenerator().generate(
            dashboard,
            relationships.by_source(ObjectType.DASHBOARD, dashboard.id or ""),
        )
        for dashboard in repository.dashboards
    )
