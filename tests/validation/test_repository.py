"""Unit tests for ValidationRepository."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from tools.ha_docgen.registries.models import Entity
from tools.ha_docgen.relationships.models import ObjectType
from tools.ha_docgen.relationships.repository import RelationshipRepository
from tools.ha_docgen.tests.support import build_validation_result
from tools.ha_docgen.validation import (
    EntityValidator,
    ValidationRepository,
    ValidationSeverity,
    ValidationType,
)


def test_empty_repository() -> None:
    repository = ValidationRepository()
    assert repository.all() == ()
    assert repository.errors() == ()
    assert repository.warnings() == ()
    assert repository.info() == ()
    assert repository.count() == 0
    assert repository.empty() is True


def test_single_result() -> None:
    result = build_validation_result()
    repository = ValidationRepository((result,))
    assert repository.all() == (result,)
    assert repository.count() == 1
    assert repository.empty() is False
    assert repository.errors() == (result,)


def test_multiple_results() -> None:
    error = build_validation_result(object_id="light.one")
    warning = build_validation_result(
        object_id="light.two",
        severity=ValidationSeverity.WARNING,
        validation_type=ValidationType.UNREFERENCED_OBJECT,
        message="No relationships found.",
    )
    info = build_validation_result(
        object_id="light.three",
        severity=ValidationSeverity.INFO,
        validation_type=ValidationType.CUSTOM,
        message="Informational note.",
    )
    repository = ValidationRepository((info, error, warning))
    assert repository.count() == 3
    assert repository.empty() is False
    assert error in repository.all()
    assert warning in repository.all()
    assert info in repository.all()


def test_constructor_accepts_any_iterable() -> None:
    result = build_validation_result()
    from_list = ValidationRepository([result])
    from_iterator = ValidationRepository(iter((result,)))
    assert from_list.all() == (result,)
    assert from_iterator.all() == (result,)


def test_deterministic_ordering() -> None:
    first = build_validation_result(
        object_id="automation.a",
        object_type=ObjectType.AUTOMATION,
    )
    second = build_validation_result(object_id="light.z")
    third = build_validation_result(
        object_id="light.a",
        validation_type=ValidationType.DUPLICATE,
        message="Duplicate entity ID.",
    )
    unordered = (second, third, first)
    expected = tuple(
        sorted(
            unordered,
            key=lambda item: (
                item.object_type,
                item.object_id,
                item.validation_type,
                item.severity,
                item.message,
            ),
        )
    )
    assert ValidationRepository(unordered).all() == expected
    assert ValidationRepository(reversed(expected)).all() == expected


def test_duplicate_removal() -> None:
    result = build_validation_result()
    duplicate = build_validation_result()
    repository = ValidationRepository((result, duplicate, result))
    assert repository.all() == (result,)
    assert repository.count() == 1


def test_errors_warnings_and_info() -> None:
    error = build_validation_result(object_id="light.error")
    warning = build_validation_result(
        object_id="light.warning",
        severity=ValidationSeverity.WARNING,
        message="Automation has no alias.",
    )
    info = build_validation_result(
        object_id="light.info",
        severity=ValidationSeverity.INFO,
        validation_type=ValidationType.CUSTOM,
        message="Informational note.",
    )
    repository = ValidationRepository((error, warning, info))
    assert repository.errors() == (error,)
    assert repository.warnings() == (warning,)
    assert repository.info() == (info,)
    assert repository.errors() == repository.by_severity(ValidationSeverity.ERROR)
    assert repository.warnings() == repository.by_severity(ValidationSeverity.WARNING)
    assert repository.info() == repository.by_severity(ValidationSeverity.INFO)


def test_by_severity() -> None:
    error = build_validation_result(object_id="one")
    warning = build_validation_result(
        object_id="two",
        severity=ValidationSeverity.WARNING,
        message="Warning.",
    )
    repository = ValidationRepository((error, warning))
    assert repository.by_severity(ValidationSeverity.ERROR) == (error,)
    assert repository.by_severity(ValidationSeverity.WARNING) == (warning,)


def test_by_validation_type() -> None:
    invalid = build_validation_result()
    duplicate = build_validation_result(
        object_id="light.other",
        validation_type=ValidationType.DUPLICATE,
        message="Duplicate entity ID.",
    )
    repository = ValidationRepository((invalid, duplicate))
    assert repository.by_validation_type(ValidationType.INVALID_CONFIGURATION) == (invalid,)
    assert repository.by_validation_type(ValidationType.DUPLICATE) == (duplicate,)


def test_by_object_type() -> None:
    entity = build_validation_result()
    automation = build_validation_result(
        object_type=ObjectType.AUTOMATION,
        object_id="morning",
        message="Automation ID is empty.",
    )
    repository = ValidationRepository((entity, automation))
    assert repository.by_object_type(ObjectType.ENTITY) == (entity,)
    assert repository.by_object_type(ObjectType.AUTOMATION) == (automation,)


def test_by_object_id() -> None:
    kitchen = build_validation_result(object_id="light.kitchen")
    other_type = build_validation_result(
        object_type=ObjectType.SCRIPT,
        object_id="light.kitchen",
        message="Script ID is empty.",
    )
    lounge = build_validation_result(object_id="light.lounge")
    repository = ValidationRepository((lounge, other_type, kitchen))
    matched = repository.by_object_id("light.kitchen")
    assert kitchen in matched
    assert other_type in matched
    assert lounge not in matched
    assert len(matched) == 2


def test_empty_lookup_results() -> None:
    repository = ValidationRepository((build_validation_result(),))
    assert repository.warnings() == ()
    assert repository.info() == ()
    assert repository.by_severity(ValidationSeverity.INFO) == ()
    assert repository.by_validation_type(ValidationType.UNSUPPORTED) == ()
    assert repository.by_object_type(ObjectType.DASHBOARD) == ()
    assert repository.by_object_id("missing") == ()
    empty = ValidationRepository()
    assert empty.errors() == ()
    assert empty.by_validation_type(ValidationType.DUPLICATE) == ()
    assert empty.by_object_type(ObjectType.ENTITY) == ()
    assert empty.by_object_id("light.kitchen") == ()


def test_returned_collections_are_immutable_tuples() -> None:
    result = build_validation_result()
    repository = ValidationRepository((result,))
    lookups = (
        repository.all(),
        repository.errors(),
        repository.warnings(),
        repository.info(),
        repository.by_severity(ValidationSeverity.ERROR),
        repository.by_validation_type(ValidationType.INVALID_CONFIGURATION),
        repository.by_object_type(ObjectType.ENTITY),
        repository.by_object_id("light.kitchen"),
    )
    for collection in lookups:
        assert isinstance(collection, tuple)
        with pytest.raises(AttributeError):
            collection.append(result)  # type: ignore[attr-defined]


def test_repository_instance_is_frozen() -> None:
    repository = ValidationRepository((build_validation_result(),))
    with pytest.raises(FrozenInstanceError):
        repository.results = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        repository.errors = lambda: ()  # type: ignore[method-assign]


def test_count_and_empty() -> None:
    empty = ValidationRepository()
    assert empty.count() == 0
    assert empty.empty() is True
    populated = ValidationRepository(
        (
            build_validation_result(),
            build_validation_result(object_id="light.other"),
        )
    )
    assert populated.count() == 2
    assert populated.empty() is False


def test_integrates_with_entity_validator() -> None:
    entities = (
        Entity(registry_id="a", entity_id="light.one", unique_id="a"),
        Entity(registry_id="b", entity_id="light.one", unique_id="b"),
        Entity(registry_id="c", entity_id="", unique_id="c"),
    )
    findings = EntityValidator().validate(entities, RelationshipRepository())
    repository = ValidationRepository(findings)
    assert repository.empty() is False
    assert repository.count() == len(findings)
    assert repository.all() == findings
    assert repository.by_validation_type(ValidationType.DUPLICATE) != ()
    assert repository.by_object_type(ObjectType.ENTITY) == repository.all()
    assert all(item.severity == ValidationSeverity.ERROR for item in repository.errors())
