"""Unit tests for EntityValidator."""

from __future__ import annotations

from ha_docgen.relationships import (
    ObjectType,
    RelationshipRepository,
    RelationshipType,
)
from ha_docgen.validation import (
    EntityValidator,
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)
from tests.support.builders import EntityBuilder, build_relationship


def test_valid_entity_with_relationship_has_no_findings() -> None:
    entity = EntityBuilder("light.kitchen").build()
    repository = RelationshipRepository(
        (
            build_relationship(
                source_type=ObjectType.ENTITY,
                source_id=entity.entity_id,
                target_type=ObjectType.DEVICE,
                target_id="device.kitchen",
                relationship_type=RelationshipType.BELONGS_TO,
            ),
        )
    )

    assert EntityValidator().validate((entity,), repository) == ()


def test_entity_without_relationship_is_reported_as_informational() -> None:
    entity = EntityBuilder("light.kitchen").build()

    results = EntityValidator().validate((entity,), RelationshipRepository())

    assert results == (
        ValidationResult(
            object_type=ObjectType.ENTITY,
            object_id="light.kitchen",
            validation_type=ValidationType.UNREFERENCED_OBJECT,
            severity=ValidationSeverity.INFO,
            message="Entity is not referenced.",
        ),
    )


def test_empty_entity_id_reports_identity_and_reference_findings() -> None:
    entity = EntityBuilder("").build()

    results = EntityValidator().validate((entity,), RelationshipRepository())

    assert {result.message for result in results} == {
        "Entity ID is empty.",
        "Entity is not referenced.",
    }
    assert next(
        result for result in results if result.message == "Entity ID is empty."
    ).severity is (ValidationSeverity.ERROR)


def test_duplicate_entity_id_is_reported_once() -> None:
    entities = (
        EntityBuilder("light.duplicate").with_unique_id("one").build(),
        EntityBuilder("light.duplicate").with_unique_id("two").build(),
    )
    repository = RelationshipRepository(
        (
            build_relationship(
                source_type=ObjectType.ENTITY,
                source_id="light.duplicate",
                target_type=ObjectType.DEVICE,
                target_id="device.kitchen",
                relationship_type=RelationshipType.BELONGS_TO,
            ),
        )
    )

    results = EntityValidator().validate(entities, repository)

    assert results == (
        ValidationResult(
            object_type=ObjectType.ENTITY,
            object_id="light.duplicate",
            validation_type=ValidationType.DUPLICATE,
            severity=ValidationSeverity.ERROR,
            message="Duplicate entity ID.",
        ),
    )


def test_duplicate_empty_relationship_findings_are_deduplicated() -> None:
    entity = EntityBuilder("light.kitchen").build()
    empty_target = build_relationship(
        source_type=ObjectType.ENTITY,
        source_id=entity.entity_id,
        target_type=ObjectType.DEVICE,
        target_id="",
        relationship_type=RelationshipType.BELONGS_TO,
    )
    repository = RelationshipRepository(
        (
            empty_target,
            build_relationship(
                source_type=ObjectType.ENTITY,
                source_id=entity.entity_id,
                target_type=ObjectType.AREA,
                target_id="",
                relationship_type=RelationshipType.BELONGS_TO,
            ),
        )
    )

    results = EntityValidator().validate((entity,), repository)

    assert len(results) == 1
    assert results[0].message == "Relationship has empty target."
    assert results[0].severity is ValidationSeverity.ERROR


def test_results_are_deterministic_for_reversed_input() -> None:
    first = EntityBuilder("light.z").build()
    second = EntityBuilder("light.a").build()
    validator = EntityValidator()
    repository = RelationshipRepository()

    assert validator.validate((first, second), repository) == validator.validate(
        (second, first), repository
    )
