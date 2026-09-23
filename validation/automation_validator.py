"""Validate Home Assistant automations against explicit rules.

Produces immutable ``ValidationResult`` tuples only — no repository,
engine, reports, Markdown, filesystem or graph coupling.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from ..automation.models import Automation
from ..relationships.models import ObjectType
from ..relationships.repository import RelationshipRepository
from .models import (
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)


class AutomationValidator:
    """Stateless validator for explicit automation integrity checks.

    Accepts already-loaded automations and a read-only relationship
    repository. Emits findings only; does not mutate inputs.
    """

    def validate(
        self,
        automations: tuple[Automation, ...],
        relationship_repository: RelationshipRepository,
    ) -> tuple[ValidationResult, ...]:
        """Return sorted validation findings for *automations*."""
        results: list[ValidationResult] = []
        results.extend(_validate_duplicates(automations))
        for automation in automations:
            results.extend(_validate_identity(automation))
            results.extend(_validate_alias(automation))
            results.extend(
                _validate_relationships(automation, relationship_repository),
            )
        return _sort_results(results)


def _object_id(automation: Automation) -> str:
    """Return the automation identity string used in findings."""
    return automation.id if automation.id is not None else ""


def _validate_identity(automation: Automation) -> tuple[ValidationResult, ...]:
    """Flag an empty automation ID."""
    if _object_id(automation) != "":
        return ()
    return (
        ValidationResult(
            object_type=ObjectType.AUTOMATION,
            object_id=_object_id(automation),
            validation_type=ValidationType.INVALID_CONFIGURATION,
            severity=ValidationSeverity.ERROR,
            message="Automation ID is empty.",
        ),
    )


def _validate_alias(automation: Automation) -> tuple[ValidationResult, ...]:
    """Flag a missing automation alias."""
    if automation.alias is not None and automation.alias != "":
        return ()
    return (
        ValidationResult(
            object_type=ObjectType.AUTOMATION,
            object_id=_object_id(automation),
            validation_type=ValidationType.INVALID_CONFIGURATION,
            severity=ValidationSeverity.WARNING,
            message="Automation has no alias.",
        ),
    )


def _validate_duplicates(
    automations: tuple[Automation, ...],
) -> tuple[ValidationResult, ...]:
    """Flag automation IDs that appear more than once in *automations*."""
    counts = Counter(_object_id(automation) for automation in automations)
    return tuple(
        ValidationResult(
            object_type=ObjectType.AUTOMATION,
            object_id=automation_id,
            validation_type=ValidationType.DUPLICATE,
            severity=ValidationSeverity.ERROR,
            message="Duplicate automation ID.",
        )
        for automation_id, count in counts.items()
        if count > 1
    )


def _validate_relationships(
    automation: Automation,
    relationship_repository: RelationshipRepository,
) -> tuple[ValidationResult, ...]:
    """Flag relationships with an empty target identity."""
    object_id = _object_id(automation)
    relationships = relationship_repository.by_source(
        ObjectType.AUTOMATION,
        object_id,
    )
    return tuple(
        ValidationResult(
            object_type=ObjectType.AUTOMATION,
            object_id=object_id,
            validation_type=ValidationType.INVALID_CONFIGURATION,
            severity=ValidationSeverity.ERROR,
            message="Relationship has empty target.",
        )
        for relationship in relationships
        if relationship.target_id == ""
    )


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
