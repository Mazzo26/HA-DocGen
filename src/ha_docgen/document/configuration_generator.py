"""Build a Document overview of the full Home Assistant configuration.

Transforms already-built immutable aggregates into one ``Document`` tree.
Produces document models only — no Markdown, filesystem, parsing,
analysis, graph traversal or repository mutation.
"""

from __future__ import annotations

from ..registries.home_assistant_model import HomeAssistantModel
from ..relationships.models import RelationshipType
from ..relationships.repository import RelationshipRepository
from ..yaml.repository import YamlRepository
from .models import BulletList, Document, Paragraph, Section, Table

_OVERVIEW_TEXT = (
    "Overview of the Home Assistant configuration covering "
    "registry objects, YAML domain objects and relationships."
)


class ConfigurationDocumentGenerator:
    """Generate a Document summarising the full configuration.

    Fully stateless: no instance state, no caching, no filesystem and
    no side effects. Callers supply already-built immutable aggregates.
    """

    def generate(
        self,
        model: HomeAssistantModel,
        yaml_repository: YamlRepository,
        relationship_repository: RelationshipRepository,
    ) -> Document:
        """Return a Document overview from the given aggregates."""
        return Document(
            title="Home Assistant Configuration",
            sections=(
                _build_overview(),
                _build_registry_section(model),
                _build_yaml_section(yaml_repository),
                _build_relationship_section(relationship_repository),
                _build_statistics(
                    model,
                    yaml_repository,
                    relationship_repository,
                ),
            ),
        )


def _build_overview() -> Section:
    """Build Overview as a short descriptive paragraph."""
    return Section(heading="Overview", content=(Paragraph(_OVERVIEW_TEXT),))


def _build_registry_section(model: HomeAssistantModel) -> Section:
    """Build Registries as a Type / Count table from HomeAssistantModel."""
    rows = (
        ("Entities", str(len(model.entities))),
        ("Devices", str(len(model.devices))),
        ("Areas", str(len(model.areas))),
        ("Floors", str(len(model.floors))),
        ("Labels", str(len(model.labels))),
        ("Config Entries", str(len(model.config_entries))),
    )
    return Section(
        heading="Registries",
        content=(Table(headers=("Type", "Aantal"), rows=rows),),
    )


def _build_yaml_section(yaml_repository: YamlRepository) -> Section:
    """Build YAML as a Type / Count table from YamlRepository."""
    rows = (
        ("Packages", str(len(yaml_repository.packages))),
        ("Automations", str(len(yaml_repository.automations))),
        ("Scripts", str(len(yaml_repository.scripts))),
        ("Scenes", str(len(yaml_repository.scenes))),
        ("Helpers", str(len(yaml_repository.helpers))),
        ("Dashboards", str(len(yaml_repository.dashboards))),
        ("Blueprints", str(len(yaml_repository.blueprints))),
        ("Templates", str(len(yaml_repository.templates))),
    )
    return Section(
        heading="YAML",
        content=(Table(headers=("Type", "Aantal"), rows=rows),),
    )


def _build_relationship_section(
    relationship_repository: RelationshipRepository,
) -> Section:
    """Build Relationships as counts per RelationshipType."""
    rows = tuple(
        (
            relationship_type.value,
            str(len(relationship_repository.by_relationship(relationship_type))),
        )
        for relationship_type in RelationshipType
    )
    return Section(
        heading="Relationships",
        content=(
            Table(headers=("Relationship type", "Aantal"), rows=rows),
        ),
    )


def _build_statistics(
    model: HomeAssistantModel,
    yaml_repository: YamlRepository,
    relationship_repository: RelationshipRepository,
) -> Section:
    """Build Statistics as simple aggregate totals."""
    registry_total = (
        len(model.entities)
        + len(model.devices)
        + len(model.areas)
        + len(model.floors)
        + len(model.labels)
        + len(model.config_entries)
    )
    yaml_total = (
        len(yaml_repository.packages)
        + len(yaml_repository.automations)
        + len(yaml_repository.scripts)
        + len(yaml_repository.scenes)
        + len(yaml_repository.helpers)
        + len(yaml_repository.dashboards)
        + len(yaml_repository.blueprints)
        + len(yaml_repository.templates)
    )
    items = (
        f"Total registry objects: {registry_total}",
        f"Total YAML objects: {yaml_total}",
        f"Total relationships: {len(relationship_repository.relationships)}",
    )
    return Section(heading="Statistics", content=(BulletList(items),))
