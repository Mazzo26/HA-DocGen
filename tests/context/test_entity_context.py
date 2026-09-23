"""Unit tests for entity context projection."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, asdict

import pytest

from tools.ha_docgen.analysis import AnalysisModel
from tools.ha_docgen.context import ContextGenerator, EntityContext
from tools.ha_docgen.packages import Package
from tools.ha_docgen.registries.home_assistant_model import HomeAssistantModel
from tools.ha_docgen.registries.models import Entity
from tools.ha_docgen.relationships import (
    ObjectType,
    Relationship,
    RelationshipRepository,
    RelationshipType,
)
from tools.ha_docgen.tests.support import PackageBuilder, build_relationship
from tools.ha_docgen.yaml import YamlRepository


def _entity(entity_id: str, **overrides: object) -> Entity:
    values: dict[str, object] = {
        "registry_id": entity_id,
        "entity_id": entity_id,
        "unique_id": entity_id,
    }
    values.update(overrides)
    return Entity(**values)  # type: ignore[arg-type]


def _package(name: str) -> Package:
    return PackageBuilder(name).build()


def _generate(
    *,
    entities: tuple[Entity, ...] = (),
    packages: tuple[Package, ...] = (),
    relationships: tuple[Relationship, ...] = (),
) -> tuple[EntityContext, ...]:
    context = ContextGenerator().generate(
        AnalysisModel(
            home_assistant_model=HomeAssistantModel(entities=entities),
            yaml_repository=YamlRepository(packages=packages),
            relationship_repository=RelationshipRepository(relationships),
        )
    )
    return context.entity_contexts


def test_empty_registry_has_no_entity_contexts() -> None:
    assert _generate() == ()


def test_populated_registry_keeps_the_original_entity() -> None:
    entity = _entity(
        "light.kitchen",
        name="Kitchen",
        unique_id="unique-kitchen",
        device_id="device-1",
        area_id="kitchen",
        config_entry_id="entry-1",
        labels=("night", "warm"),
        disabled_by="user",
        hidden_by="integration",
        created_at="2026-01-01T00:00:00+00:00",
        modified_at="2026-02-01T00:00:00+00:00",
        orphaned_timestamp=123.0,
    )
    projected = _generate(entities=(entity,))
    assert len(projected) == 1
    assert projected[0].entity is entity
    assert projected[0].entity.entity_id == "light.kitchen"
    assert projected[0].entity.domain == "light"
    assert projected[0].entity.name == "Kitchen"
    assert projected[0].entity.unique_id == "unique-kitchen"
    assert projected[0].entity.device_id == "device-1"
    assert projected[0].entity.area_id == "kitchen"
    assert projected[0].entity.config_entry_id == "entry-1"
    assert projected[0].entity.labels == ("night", "warm")
    assert projected[0].entity.disabled_by == "user"
    assert projected[0].entity.hidden_by == "integration"
    assert projected[0].entity.created_at == "2026-01-01T00:00:00+00:00"
    assert projected[0].entity.modified_at == "2026-02-01T00:00:00+00:00"
    assert projected[0].entity.orphaned_timestamp == 123.0
    assert projected[0].relationships == ()
    assert projected[0].packages == ()


def test_relationship_mapping_keeps_existing_edges() -> None:
    entity = _entity("light.kitchen")
    outgoing = build_relationship(
        ObjectType.ENTITY,
        "light.kitchen",
        ObjectType.DEVICE,
        "device-1",
        RelationshipType.BELONGS_TO,
    )
    incoming = build_relationship(
        ObjectType.AUTOMATION,
        "evening",
        ObjectType.ENTITY,
        "light.kitchen",
        RelationshipType.REFERENCES,
    )
    unrelated = build_relationship(
        ObjectType.ENTITY,
        "light.porch",
        ObjectType.DEVICE,
        "device-2",
        RelationshipType.BELONGS_TO,
    )
    projected = _generate(
        entities=(entity,),
        relationships=(incoming, unrelated, outgoing),
    )
    assert projected[0].relationships == (incoming, outgoing)
    assert projected[0].entity is entity


def test_package_membership_uses_only_existing_packages() -> None:
    entity = _entity("light.kitchen")
    climate = _package("climate")
    lighting = _package("lighting")
    present = build_relationship(
        ObjectType.ENTITY,
        "light.kitchen",
        ObjectType.PACKAGE,
        "lighting",
        RelationshipType.BELONGS_TO,
    )
    duplicate = build_relationship(
        ObjectType.PACKAGE,
        "lighting",
        ObjectType.ENTITY,
        "light.kitchen",
        RelationshipType.CONTAINS,
    )
    missing = build_relationship(
        ObjectType.ENTITY,
        "light.kitchen",
        ObjectType.PACKAGE,
        "absent",
        RelationshipType.BELONGS_TO,
    )
    projected = _generate(
        entities=(entity,),
        packages=(climate, lighting),
        relationships=(missing, duplicate, present),
    )
    assert projected[0].packages == (lighting,)
    assert projected[0].packages[0] is lighting
    assert missing in projected[0].relationships


def test_package_membership_is_not_inferred_from_other_objects() -> None:
    entity = _entity("light.kitchen")
    climate = _package("climate")
    reference = build_relationship(
        ObjectType.AUTOMATION,
        "evening",
        ObjectType.ENTITY,
        "light.kitchen",
        RelationshipType.REFERENCES,
    )
    projected = _generate(
        entities=(entity,),
        packages=(climate,),
        relationships=(reference,),
    )
    assert projected[0].packages == ()
    assert projected[0].relationships == (reference,)


def test_entity_contexts_are_ordered_by_identity() -> None:
    porch = _entity("light.porch", registry_id="porch", unique_id="porch")
    kitchen = _entity("light.kitchen", registry_id="kitchen", unique_id="kitchen")
    projected = _generate(entities=(porch, kitchen))
    assert [item.entity.entity_id for item in projected] == ["light.kitchen", "light.porch"]
    assert projected[0].entity is kitchen
    assert projected[1].entity is porch


def test_entity_context_is_immutable_and_relationships_are_serializable() -> None:
    entity = _entity("light.kitchen", name="Kitchen")
    relationship = build_relationship(
        ObjectType.ENTITY,
        "light.kitchen",
        ObjectType.AREA,
        "kitchen",
        RelationshipType.BELONGS_TO,
    )
    context = EntityContext(entity=entity, relationships=(relationship,))
    with pytest.raises(FrozenInstanceError):
        context.packages = ()  # type: ignore[misc]
    encoded = json.dumps(asdict(relationship))
    assert context.entity is entity
    assert context.relationships[0] is relationship
    assert "light.kitchen" in encoded
    assert "kitchen" in encoded
