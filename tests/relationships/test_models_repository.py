"""Unit tests for relationship models and repository lookups."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from tools.ha_docgen.relationships import (
    ObjectType,
    RelationshipCollection,
    RelationshipRepository,
    RelationshipType,
)
from tools.ha_docgen.tests.support import build_relationship


def test_relationship_enums_are_strings_with_expected_values() -> None:
    assert ObjectType.ENTITY == "entity"
    assert ObjectType.MQTT_TOPIC == "mqtt_topic"
    assert RelationshipType.BELONGS_TO == "belongs_to"
    assert RelationshipType.SUBSCRIBES == "subscribes"


def test_relationship_is_hashable_and_immutable() -> None:
    relationship = build_relationship()

    assert {build_relationship(), relationship} == {relationship}
    with pytest.raises(FrozenInstanceError):
        relationship.target_id = "light.changed"  # type: ignore[misc]


def test_relationship_collection_coerces_input_and_indexes_identities() -> None:
    first = build_relationship()
    second = build_relationship(
        source_id="script.arrive",
        target_id="light.living_room",
        source_type=ObjectType.SCRIPT,
    )
    collection = RelationshipCollection([first, second])  # type: ignore[arg-type]

    assert collection.relationships == (first, second)
    assert collection.by_source(ObjectType.AUTOMATION, "automation.evening") == (first,)
    assert collection.by_target(ObjectType.ENTITY, "light.living_room") == (
        first,
        second,
    )
    assert collection.by_source(ObjectType.ENTITY, "missing") == ()


def test_relationship_collection_is_immutable() -> None:
    collection = RelationshipCollection((build_relationship(),))

    with pytest.raises(FrozenInstanceError):
        collection.relationships = ()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        collection.relationships.append(build_relationship())  # type: ignore[attr-defined]


def test_repository_deduplicates_and_sorts_deterministically() -> None:
    entity = build_relationship(target_id="sensor.temperature")
    area = build_relationship(
        target_id="living_room",
        target_type=ObjectType.AREA,
        relationship_type=RelationshipType.USES,
    )

    repository = RelationshipRepository((entity, area, entity))

    assert repository.relationships == (entity, area)
    assert isinstance(repository.relationships, tuple)


def test_repository_supports_all_lookup_variants() -> None:
    reference = build_relationship()
    belongs_to = build_relationship(
        source_id="light.living_room",
        target_id="device-1",
        source_type=ObjectType.ENTITY,
        target_type=ObjectType.DEVICE,
        relationship_type=RelationshipType.BELONGS_TO,
    )
    repository = RelationshipRepository((belongs_to, reference))

    assert repository.by_source(ObjectType.ENTITY, "light.living_room") == (belongs_to,)
    assert repository.by_target(ObjectType.DEVICE, "device-1") == (belongs_to,)
    assert repository.by_relationship(RelationshipType.REFERENCES) == (reference,)
    assert repository.between(
        ObjectType.AUTOMATION,
        "automation.evening",
        ObjectType.ENTITY,
    ) == (reference,)


def test_repository_empty_and_unknown_lookups_return_empty_tuples() -> None:
    repository = RelationshipRepository()

    assert repository.relationships == ()
    assert repository.by_source(ObjectType.ENTITY, "missing") == ()
    assert repository.by_target(ObjectType.DEVICE, "missing") == ()
    assert repository.by_relationship(RelationshipType.CONTAINS) == ()
    assert repository.between(ObjectType.PACKAGE, "missing", ObjectType.ENTITY) == ()


def test_repository_does_not_mutate_caller_collection() -> None:
    relationship = build_relationship()
    supplied = [relationship, relationship]

    repository = RelationshipRepository(supplied)  # type: ignore[arg-type]

    assert supplied == [relationship, relationship]
    assert repository.relationships == (relationship,)
