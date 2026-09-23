"""Factories for immutable HA-DocGen models used by tests.

Builders hold configuration only until ``build()``. They are not production
components and must not be imported outside the test package.
"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

from tools.ha_docgen.automation import Automation
from tools.ha_docgen.graph import DependencyGraph, GraphEdge, GraphNode
from tools.ha_docgen.packages import Package
from tools.ha_docgen.registries import Entity, HomeAssistantModel
from tools.ha_docgen.relationships import (
    ObjectType,
    Relationship,
    RelationshipType,
)
from tools.ha_docgen.validation import (
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)
from tools.ha_docgen.yaml import YamlDocument, YamlRepository

_DEFAULT_PACKAGE_TEXT = "automation:\n  - id: sample_automation\n    alias: Sample automation\n"
_DEFAULT_AUTOMATION = MappingProxyType(
    {
        "id": "sample_automation",
        "alias": "Sample automation",
    }
)
_DEFAULT_PACKAGE_DATA = MappingProxyType({"automation": (_DEFAULT_AUTOMATION,)})


class EntityBuilder:
    """Build one ``Entity`` with a stable identity."""

    def __init__(self, entity_id: str = "light.sample") -> None:
        """Start from a deterministic entity id."""
        self._entity_id = entity_id
        self._registry_id = entity_id
        self._unique_id = entity_id
        self._name: str | None = "Sample"
        self._device_id: str | None = None

    def with_registry_id(self, registry_id: str) -> EntityBuilder:
        """Set the registry id."""
        self._registry_id = registry_id
        return self

    def with_unique_id(self, unique_id: str) -> EntityBuilder:
        """Set the unique id."""
        self._unique_id = unique_id
        return self

    def with_name(self, name: str | None) -> EntityBuilder:
        """Set the display name."""
        self._name = name
        return self

    def with_device_id(self, device_id: str | None) -> EntityBuilder:
        """Set the related device id."""
        self._device_id = device_id
        return self

    def build(self) -> Entity:
        """Return the configured entity."""
        return Entity(
            registry_id=self._registry_id,
            entity_id=self._entity_id,
            unique_id=self._unique_id,
            name=self._name,
            device_id=self._device_id,
        )


class HomeAssistantModelBuilder:
    """Build a ``HomeAssistantModel`` from already-built entities."""

    def __init__(self) -> None:
        """Start with an empty entity collection."""
        self._entities: list[Entity] = []

    def add_entity(self, entity: Entity) -> HomeAssistantModelBuilder:
        """Append one entity."""
        self._entities.append(entity)
        return self

    def build(self) -> HomeAssistantModel:
        """Return a model whose entities are sorted by entity id."""
        entities = tuple(sorted(self._entities, key=lambda entity: entity.entity_id))
        return HomeAssistantModel(entities=entities)


class PackageBuilder:
    """Build one ``Package`` and its ``YamlDocument``."""

    def __init__(self, name: str = "sample") -> None:
        """Start from a deterministic package name and document."""
        self._name = name
        self._path = Path("packages") / f"{name}.yaml"
        self._text = _DEFAULT_PACKAGE_TEXT
        self._data: object = _DEFAULT_PACKAGE_DATA

    def with_path(self, path: Path) -> PackageBuilder:
        """Set the package path stored on the document."""
        self._path = path
        return self

    def with_text(self, text: str) -> PackageBuilder:
        """Set the original YAML text."""
        self._text = text
        return self

    def with_data(self, data: object) -> PackageBuilder:
        """Set the already-parsed YAML data."""
        self._data = _freeze_mapping(data)
        return self

    def build(self) -> Package:
        """Return the configured package."""
        document = YamlDocument(path=self._path, text=self._text, data=self._data)
        return Package(name=self._name, path=self._path, document=document)


class AutomationBuilder:
    """Build one ``Automation`` bound to a package."""

    def __init__(self) -> None:
        """Start from the shared sample automation identity."""
        self._package: Package | None = None
        self._id: str | None = "sample_automation"
        self._alias: str | None = "Sample automation"
        self._description: str | None = None
        self._mode: str | None = None

    def with_package(self, package: Package) -> AutomationBuilder:
        """Use an existing package instead of the default sample package."""
        self._package = package
        return self

    def with_id(self, automation_id: str | None) -> AutomationBuilder:
        """Set the automation id."""
        self._id = automation_id
        return self

    def with_alias(self, alias: str | None) -> AutomationBuilder:
        """Set the automation alias."""
        self._alias = alias
        return self

    def with_description(self, description: str | None) -> AutomationBuilder:
        """Set the automation description."""
        self._description = description
        return self

    def with_mode(self, mode: str | None) -> AutomationBuilder:
        """Set the automation mode."""
        self._mode = mode
        return self

    def build(self) -> Automation:
        """Return the configured automation."""
        return Automation(
            package=self._package or PackageBuilder().build(),
            id=self._id,
            alias=self._alias,
            description=self._description,
            mode=self._mode,
        )


class YamlRepositoryBuilder:
    """Build a ``YamlRepository`` from packages and automations."""

    def __init__(self) -> None:
        """Start with empty collections."""
        self._packages: list[Package] = []
        self._automations: list[Automation] = []

    def add_package(self, package: Package) -> YamlRepositoryBuilder:
        """Append one package."""
        self._packages.append(package)
        return self

    def add_automation(self, automation: Automation) -> YamlRepositoryBuilder:
        """Append one automation."""
        self._automations.append(automation)
        return self

    def build(self) -> YamlRepository:
        """Return a repository with deterministically ordered collections."""
        return YamlRepository(
            packages=tuple(sorted(self._packages, key=_package_key)),
            automations=tuple(sorted(self._automations, key=_automation_key)),
        )


def build_sample_home_assistant_model() -> HomeAssistantModel:
    """Return a model containing the default sample entity."""
    return HomeAssistantModelBuilder().add_entity(EntityBuilder().build()).build()


def build_sample_yaml_repository() -> YamlRepository:
    """Return a repository containing the default sample package and automation."""
    package = PackageBuilder().build()
    automation = AutomationBuilder().with_package(package).build()
    return YamlRepositoryBuilder().add_package(package).add_automation(automation).build()


def build_sample_dependency_graph() -> DependencyGraph:
    """Return a graph with one automation referencing the sample entity."""
    automation = GraphNode(ObjectType.AUTOMATION, "sample_automation")
    entity = GraphNode(ObjectType.ENTITY, "light.sample")
    edge = GraphEdge(
        source=automation,
        target=entity,
        relationship_type=RelationshipType.REFERENCES,
    )
    nodes = tuple(sorted((automation, entity), key=_node_key))
    return DependencyGraph(nodes=nodes, edges=(edge,))


def build_relationship(
    source_type: ObjectType = ObjectType.AUTOMATION,
    source_id: str = "automation.evening",
    target_type: ObjectType = ObjectType.ENTITY,
    target_id: str = "light.living_room",
    relationship_type: RelationshipType = RelationshipType.REFERENCES,
) -> Relationship:
    """Return one relationship with deterministic defaults."""
    return Relationship(
        source_type=source_type,
        source_id=source_id,
        target_type=target_type,
        target_id=target_id,
        relationship_type=relationship_type,
    )


def build_validation_result(
    object_id: str = "light.kitchen",
    *,
    object_type: ObjectType = ObjectType.ENTITY,
    validation_type: ValidationType = ValidationType.INVALID_CONFIGURATION,
    severity: ValidationSeverity = ValidationSeverity.ERROR,
    message: str = "Entity ID is empty.",
) -> ValidationResult:
    """Return one validation result with deterministic defaults."""
    return ValidationResult(
        object_type=object_type,
        object_id=object_id,
        validation_type=validation_type,
        severity=severity,
        message=message,
    )


def _freeze_mapping(data: object) -> object:
    """Return a read-only copy. Nested containers are copied too."""
    return _freeze_value(data)


def _freeze_value(value: object) -> object:
    """Copy dicts, lists and tuples so the caller cannot mutate the result."""
    if isinstance(value, dict):
        frozen = {key: _freeze_value(item) for key, item in value.items()}
        return MappingProxyType(frozen)
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item) for item in value)
    return value


def _package_key(package: Package) -> tuple[str, str]:
    """Sort packages by name and path."""
    return (package.name, package.path.as_posix())


def _automation_key(automation: Automation) -> tuple[str, str]:
    """Sort automations by id and alias."""
    return (automation.id or "", automation.alias or "")


def _node_key(node: GraphNode) -> tuple[str, str]:
    """Sort graph nodes by type and id."""
    return (node.object_type.value, node.object_id)
