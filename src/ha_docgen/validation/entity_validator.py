"""Validate Home Assistant entities against explicit rules.

Produces immutable ``ValidationResult`` tuples only — no repository,
engine, reports, Markdown, filesystem or graph coupling.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from ..registries.models import Entity
from ..relationships.models import ObjectType
from ..relationships.repository import RelationshipRepository
from .models import (
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)


class EntityValidator:
    """Stateless validator for explicit entity integrity checks.

    Accepts already-loaded entities and a read-only relationship
    repository. Emits findings only; does not mutate inputs.
    """

    def validate(
        self,
        entities: tuple[Entity, ...],
        relationship_repository: RelationshipRepository,
    ) -> tuple[ValidationResult, ...]:
        """Return sorted validation findings for *entities*."""
        results: list[ValidationResult] = []
        results.extend(_validate_duplicates(entities))
        for entity in entities:
            results.extend(_validate_identity(entity))
            results.extend(
                _validate_relationships(entity, relationship_repository),
            )
        return _sort_results(results)


def _validate_identity(entity: Entity) -> tuple[ValidationResult, ...]:
    """Flag an empty entity ID."""
    if entity.entity_id != "":
        return ()
    return (
        ValidationResult(
            object_type=ObjectType.ENTITY,
            object_id=entity.entity_id,
            validation_type=ValidationType.INVALID_CONFIGURATION,
            severity=ValidationSeverity.ERROR,
            message="Entity ID is empty.",
        ),
    )


def _validate_duplicates(
    entities: tuple[Entity, ...],
) -> tuple[ValidationResult, ...]:
    """Flag entity IDs that appear more than once in *entities*."""
    counts = Counter(entity.entity_id for entity in entities)
    return tuple(
        ValidationResult(
            object_type=ObjectType.ENTITY,
            object_id=entity_id,
            validation_type=ValidationType.DUPLICATE,
            severity=ValidationSeverity.ERROR,
            message="Duplicate entity ID.",
        )
        for entity_id, count in counts.items()
        if count > 1
    )


def _validate_relationships(
    entity: Entity,
    relationship_repository: RelationshipRepository,
) -> tuple[ValidationResult, ...]:
    """Flag missing relationships and empty relationship targets."""
    relationships = relationship_repository.by_source(
        ObjectType.ENTITY,
        entity.entity_id,
    )
    results: list[ValidationResult] = []
    if not relationships:
        results.append(
            ValidationResult(
                object_type=ObjectType.ENTITY,
                object_id=entity.entity_id,
                validation_type=ValidationType.UNREFERENCED_OBJECT,
                severity=ValidationSeverity.INFO,
                message="Entity is not referenced.",
            ),
        )
    for relationship in relationships:
        if relationship.target_id == "":
            results.append(
                ValidationResult(
                    object_type=ObjectType.ENTITY,
                    object_id=entity.entity_id,
                    validation_type=ValidationType.INVALID_CONFIGURATION,
                    severity=ValidationSeverity.ERROR,
                    message="Relationship has empty target.",
                ),
            )
    return tuple(results)


def _result_sort_key(
    result: ValidationResult,
) -> tuple[
    ObjectType,
    str,
    ValidationType,
    ValidationSeverity,
    str,
]:
    """Deterministic sort key matching validation model ordering."""
    return (
        result.object_type,
        result.object_id,
        result.validation_type,
        result.severity,
        result.message,
    )


def _sort_results(
    results: Iterable[ValidationResult],
) -> tuple[ValidationResult, ...]:
    """Deduplicate and return a deterministically sorted immutable tuple."""
    return tuple(sorted(set(results), key=_result_sort_key))
