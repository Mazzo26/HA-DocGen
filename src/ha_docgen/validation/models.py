"""Immutable validation data models.

Pure result identity only — no validators, analysis, repositories,
reports, Markdown, filesystem or Home Assistant domain coupling.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TypeVar

from ..relationships.models import ObjectType

_IndexKey = TypeVar("_IndexKey")


class ValidationSeverity(StrEnum):
    """Severity level of one validation finding."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ValidationType(StrEnum):
    """Generic validation finding kinds.

    Extensible for later modules; no Home Assistant-specific members.
    """

    UNREFERENCED_OBJECT = "unreferenced_object"
    DUPLICATE = "duplicate"
    INVALID_CONFIGURATION = "invalid_configuration"
    UNSUPPORTED = "unsupported"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Immutable identity of one validation finding.

    Holds object identity, finding kind, severity and message.
    Contains no validator logic and no domain object references.
    """

    object_type: ObjectType
    object_id: str
    validation_type: ValidationType
    severity: ValidationSeverity
    message: str


@dataclass(frozen=True, slots=True)
class ValidationCollection:
    """Immutable collection of validation results with O(1) lookups.

    Deduplicates and sorts deterministically in ``__post_init__``.
    Builds read-only indexes; provides no filtering or analysis.
    """

    results: tuple[ValidationResult, ...] = ()
    _by_object: Mapping[
        tuple[ObjectType, str],
        tuple[ValidationResult, ...],
    ] = field(init=False, repr=False, compare=False)
    _by_severity: Mapping[
        ValidationSeverity,
        tuple[ValidationResult, ...],
    ] = field(init=False, repr=False, compare=False)
    _by_type: Mapping[
        ValidationType,
        tuple[ValidationResult, ...],
    ] = field(init=False, repr=False, compare=False)

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
        by_object, by_severity, by_type = _empty_indexes()
        for result in self.results:
            _index_result(result, by_object, by_severity, by_type)
        object.__setattr__(self, "_by_object", _freeze_index(by_object))
        object.__setattr__(self, "_by_severity", _freeze_index(by_severity))
        object.__setattr__(self, "_by_type", _freeze_index(by_type))

    def by_object(
        self,
        object_type: ObjectType,
        object_id: str,
    ) -> tuple[ValidationResult, ...]:
        """Return findings for the given object identity."""
        return self._by_object.get((object_type, object_id), ())

    def by_severity(
        self,
        severity: ValidationSeverity,
    ) -> tuple[ValidationResult, ...]:
        """Return findings with the given severity."""
        return self._by_severity.get(severity, ())

    def by_type(
        self,
        validation_type: ValidationType,
    ) -> tuple[ValidationResult, ...]:
        """Return findings of the given validation type."""
        return self._by_type.get(validation_type, ())


def _empty_indexes() -> tuple[
    dict[tuple[ObjectType, str], list[ValidationResult]],
    dict[ValidationSeverity, list[ValidationResult]],
    dict[ValidationType, list[ValidationResult]],
]:
    """Create empty mutable buckets for all lookup indexes."""
    return defaultdict(list), defaultdict(list), defaultdict(list)


def _index_result(
    result: ValidationResult,
    by_object: dict[tuple[ObjectType, str], list[ValidationResult]],
    by_severity: dict[ValidationSeverity, list[ValidationResult]],
    by_type: dict[ValidationType, list[ValidationResult]],
) -> None:
    """Append *result* to every mutable lookup bucket."""
    by_object[(result.object_type, result.object_id)].append(result)
    by_severity[result.severity].append(result)
    by_type[result.validation_type].append(result)


def _result_sort_key(
    result: ValidationResult,
) -> tuple[
    ObjectType,
    str,
    ValidationType,
    ValidationSeverity,
    str,
]:
    """Deterministic sort key for reproducible collection contents."""
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
