"""Central read-only validation result repository.

Holds already-produced ``ValidationResult`` objects and provides
O(1) lookups. Performs no validation, formatting or reporting.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TypeVar

from ..relationships.models import ObjectType
from .models import (
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)

_IndexKey = TypeVar("_IndexKey")


@dataclass(frozen=True, slots=True)
class ValidationRepository:
    """Immutable store of validation findings with read-only lookups.

    Accepts an iterable of already-produced ``ValidationResult``
    objects. Deduplicates and sorts deterministically during
    construction. Validator-agnostic: callers merge validator outputs
    before construction.
    """

    results: tuple[ValidationResult, ...] = ()

    _by_severity: Mapping[
        ValidationSeverity,
        tuple[ValidationResult, ...],
    ] = field(init=False, repr=False, compare=False)
    _by_validation_type: Mapping[
        ValidationType,
        tuple[ValidationResult, ...],
    ] = field(init=False, repr=False, compare=False)
    _by_object_type: Mapping[
        ObjectType,
        tuple[ValidationResult, ...],
    ] = field(init=False, repr=False, compare=False)
    _by_object_id: Mapping[str, tuple[ValidationResult, ...]] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """Deduplicate, sort and build immutable lookup indexes."""
        object.__setattr__(
            self,
            "results",
            _deduplicate_and_sort(self.results),
        )
        self._build_indexes()

    def _build_indexes(self) -> None:
        """Populate MappingProxyType indexes for identity lookups."""
        indexes = _empty_indexes()
        for result in self.results:
            _index_result(result, *indexes)
        names = (
            "_by_severity",
            "_by_validation_type",
            "_by_object_type",
            "_by_object_id",
        )
        for name, bucket in zip(names, indexes, strict=True):
            object.__setattr__(self, name, _freeze_index(bucket))

    def all(self) -> tuple[ValidationResult, ...]:
        """Return every stored validation finding."""
        return self.results

    def errors(self) -> tuple[ValidationResult, ...]:
        """Return findings with ``ValidationSeverity.ERROR``."""
        return self.by_severity(ValidationSeverity.ERROR)

    def warnings(self) -> tuple[ValidationResult, ...]:
        """Return findings with ``ValidationSeverity.WARNING``."""
        return self.by_severity(ValidationSeverity.WARNING)

    def info(self) -> tuple[ValidationResult, ...]:
        """Return findings with ``ValidationSeverity.INFO``."""
        return self.by_severity(ValidationSeverity.INFO)

    def by_severity(
        self,
        severity: ValidationSeverity,
    ) -> tuple[ValidationResult, ...]:
        """Return findings with the given severity."""
        return self._by_severity.get(severity, ())

    def by_validation_type(
        self,
        validation_type: ValidationType,
    ) -> tuple[ValidationResult, ...]:
        """Return findings of the given validation type."""
        return self._by_validation_type.get(validation_type, ())

    def by_object_type(
        self,
        object_type: ObjectType,
    ) -> tuple[ValidationResult, ...]:
        """Return findings for the given object type."""
        return self._by_object_type.get(object_type, ())

    def by_object_id(self, object_id: str) -> tuple[ValidationResult, ...]:
        """Return findings for the given object id."""
        return self._by_object_id.get(object_id, ())

    def count(self) -> int:
        """Return the number of stored findings."""
        return len(self.results)

    def empty(self) -> bool:
        """Return True when the repository contains no findings."""
        return self.results == ()


def _empty_indexes() -> tuple[
    dict[ValidationSeverity, list[ValidationResult]],
    dict[ValidationType, list[ValidationResult]],
    dict[ObjectType, list[ValidationResult]],
    dict[str, list[ValidationResult]],
]:
    """Create empty mutable buckets for all lookup indexes."""
    return (
        defaultdict(list),
        defaultdict(list),
        defaultdict(list),
        defaultdict(list),
    )


def _index_result(
    result: ValidationResult,
    by_severity: dict[ValidationSeverity, list[ValidationResult]],
    by_validation_type: dict[ValidationType, list[ValidationResult]],
    by_object_type: dict[ObjectType, list[ValidationResult]],
    by_object_id: dict[str, list[ValidationResult]],
) -> None:
    """Append *result* to every mutable lookup bucket."""
    by_severity[result.severity].append(result)
    by_validation_type[result.validation_type].append(result)
    by_object_type[result.object_type].append(result)
    by_object_id[result.object_id].append(result)


def _result_sort_key(
    result: ValidationResult,
) -> tuple[
    ObjectType,
    str,
    ValidationType,
    ValidationSeverity,
    str,
]:
    """Deterministic sort key for reproducible repository contents."""
    return (
        result.object_type,
        result.object_id,
        result.validation_type,
        result.severity,
        result.message,
    )


def _deduplicate_and_sort(
    results: Iterable[ValidationResult],
) -> tuple[ValidationResult, ...]:
    """Remove duplicate results and return a sorted immutable tuple."""
    return tuple(sorted(set(results), key=_result_sort_key))


def _freeze_index(  # noqa: UP047
    index: dict[_IndexKey, list[ValidationResult]],
) -> Mapping[_IndexKey, tuple[ValidationResult, ...]]:
    """Convert a mutable list index into a read-only MappingProxyType."""
    return MappingProxyType({key: tuple(items) for key, items in index.items()})
