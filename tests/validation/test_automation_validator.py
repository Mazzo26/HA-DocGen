"""Unit tests for AutomationValidator."""

from __future__ import annotations

import pytest

from ha_docgen.relationships import (
    ObjectType,
    Relationship,
    RelationshipRepository,
    RelationshipType,
)
from tests.support.builders import (
    AutomationBuilder,
    build_relationship,
)
from ha_docgen.validation import (
    AutomationValidator,
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)


def test_valid_automation_without_relationships_has_no_findings() -> None:
    automation = AutomationBuilder().build()

    assert AutomationValidator().validate((automation,), RelationshipRepository()) == ()


@pytest.mark.parametrize("automation_id", (None, ""))
def test_missing_automation_id_is_reported(automation_id: str | None) -> None:
    automation = AutomationBuilder().with_id(automation_id).build()

    results = AutomationValidator().validate((automation,), RelationshipRepository())

    assert results == (
        ValidationResult(
            object_type=ObjectType.AUTOMATION,
            object_id="",
            validation_type=ValidationType.INVALID_CONFIGURATION,
            severity=ValidationSeverity.ERROR,
            message="Automation ID is empty.",
        ),
    )


@pytest.mark.parametrize("alias", (None, ""))
def test_missing_automation_alias_is_reported(alias: str | None) -> None:
    automation = AutomationBuilder().with_alias(alias).build()

    results = AutomationValidator().validate((automation,), RelationshipRepository())

    assert results == (
        ValidationResult(
            object_type=ObjectType.AUTOMATION,
            object_id="sample_automation",
            validation_type=ValidationType.INVALID_CONFIGURATION,
            severity=ValidationSeverity.WARNING,
            message="Automation has no alias.",
        ),
    )


def test_duplicate_automation_id_is_reported_once() -> None:
    automations = (
        AutomationBuilder().with_id("duplicate").with_alias("One").build(),
        AutomationBuilder().with_id("duplicate").with_alias("Two").build(),
    )

    results = AutomationValidator().validate(automations, RelationshipRepository())

    assert results == (
        ValidationResult(
            object_type=ObjectType.AUTOMATION,
            object_id="duplicate",
            validation_type=ValidationType.DUPLICATE,
            severity=ValidationSeverity.ERROR,
            message="Duplicate automation ID.",
        ),
    )


def test_relationship_with_empty_target_is_reported_and_deduplicated() -> None:
    automation = AutomationBuilder().build()
    repository = RelationshipRepository(
        (
            build_relationship(source_id="sample_automation", target_id=""),
            Relationship(
                source_type=ObjectType.AUTOMATION,
                source_id="sample_automation",
                target_type=ObjectType.SCRIPT,
                target_id="",
                relationship_type=RelationshipType.REFERENCES,
            ),
        )
    )

    results = AutomationValidator().validate((automation,), repository)

    assert len(results) == 1
    assert results[0].message == "Relationship has empty target."
    assert results[0].severity is ValidationSeverity.ERROR


def test_unrelated_relationship_is_ignored() -> None:
    automation = AutomationBuilder().build()
    repository = RelationshipRepository((build_relationship(source_id="other", target_id=""),))

    assert AutomationValidator().validate((automation,), repository) == ()


def test_results_are_deterministic_for_reversed_input() -> None:
    first = AutomationBuilder().with_id("z").with_alias(None).build()
    second = AutomationBuilder().with_id("a").with_alias(None).build()
    validator = AutomationValidator()
    repository = RelationshipRepository()

    assert validator.validate((first, second), repository) == validator.validate(
        (second, first), repository
    )
