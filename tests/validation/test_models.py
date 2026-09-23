"""Unit tests for immutable validation models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from tools.ha_docgen.relationships import ObjectType
from tools.ha_docgen.tests.support import build_validation_result
from tools.ha_docgen.validation import (
    ValidationCollection,
    ValidationSeverity,
    ValidationType,
)


def test_validation_result_is_hashable_and_frozen() -> None:
    result = build_validation_result(
        "light.kitchen",
        message="Invalid configuration.",
    )

    assert {result} == {result}
    with pytest.raises(FrozenInstanceError):
        result.message = "Changed"  # type: ignore[misc]


def test_collection_deduplicates_and_sorts_results() -> None:
    warning = build_validation_result(
        "light.z",
        severity=ValidationSeverity.WARNING,
        message="Warning.",
    )
    duplicate = build_validation_result(
        "light.a",
        validation_type=ValidationType.DUPLICATE,
        message="Duplicate.",
    )

    collection = ValidationCollection((warning, duplicate, warning))

    assert collection.results == (duplicate, warning)


def test_collection_indexes_results_by_all_public_keys() -> None:
    error = build_validation_result(
        "light.kitchen",
        message="Invalid configuration.",
    )
    warning = build_validation_result(
        "light.kitchen",
        severity=ValidationSeverity.WARNING,
        validation_type=ValidationType.CUSTOM,
        message="Warning.",
    )
    collection = ValidationCollection((warning, error))

    assert collection.by_object(ObjectType.ENTITY, "light.kitchen") == (warning, error)
    assert collection.by_severity(ValidationSeverity.ERROR) == (error,)
    assert collection.by_type(ValidationType.CUSTOM) == (warning,)


def test_collection_returns_empty_tuples_for_missing_keys() -> None:
    collection = ValidationCollection()

    assert collection.by_object(ObjectType.SCRIPT, "missing") == ()
    assert collection.by_severity(ValidationSeverity.INFO) == ()
    assert collection.by_type(ValidationType.UNSUPPORTED) == ()


def test_collection_and_lookup_results_are_immutable() -> None:
    result = build_validation_result(
        "light.kitchen",
        message="Invalid configuration.",
    )
    collection = ValidationCollection((result,))

    with pytest.raises(FrozenInstanceError):
        collection.results = ()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        collection.by_object(ObjectType.ENTITY, "light.kitchen").append(result)  # type: ignore[attr-defined]


def test_validation_enums_expose_stable_string_values() -> None:
    assert str(ValidationSeverity.WARNING) == "warning"
    assert str(ValidationType.DUPLICATE) == "duplicate"
