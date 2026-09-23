"""Immutable aggregated validation report.

Consumes a ``ValidationRepository`` and exposes read-only statistics.
Performs no validation, mutation or Markdown formatting.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from ..relationships.models import ObjectType
from .models import ValidationSeverity, ValidationType
from .repository import ValidationRepository


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Immutable summary of findings stored in a ValidationRepository.

    Aggregates counts during construction. Never validates, never
    mutates ``ValidationResult`` objects, and never formats Markdown.
    """

    _repository: ValidationRepository = field(init=False, repr=False)
    _severity_totals: Mapping[ValidationSeverity, int] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _validation_type_totals: Mapping[ValidationType, int] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _object_type_totals: Mapping[ObjectType, int] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __init__(self, repository: ValidationRepository) -> None:
        """Aggregate totals from the public ValidationRepository API."""
        object.__setattr__(self, "_repository", repository)
        object.__setattr__(self, "_severity_totals", _severity_totals(repository))
        object.__setattr__(
            self,
            "_validation_type_totals",
            _validation_type_totals(repository),
        )
        object.__setattr__(
            self,
            "_object_type_totals",
            _object_type_totals(repository),
        )

    def repository(self) -> ValidationRepository:
        """Return the ValidationRepository used to build this report."""
        return self._repository

    def total_findings(self) -> int:
        """Return the number of stored findings."""
        return self._repository.count()

    def error_count(self) -> int:
        """Return the number of ERROR findings."""
        return self._severity_totals[ValidationSeverity.ERROR]

    def warning_count(self) -> int:
        """Return the number of WARNING findings."""
        return self._severity_totals[ValidationSeverity.WARNING]

    def info_count(self) -> int:
        """Return the number of INFO findings."""
        return self._severity_totals[ValidationSeverity.INFO]

    def severity_totals(self) -> Mapping[ValidationSeverity, int]:
        """Return an immutable mapping of severity to finding count."""
        return self._severity_totals

    def validation_type_totals(self) -> Mapping[ValidationType, int]:
        """Return an immutable mapping of validation type to finding count."""
        return self._validation_type_totals

    def object_type_totals(self) -> Mapping[ObjectType, int]:
        """Return an immutable mapping of object type to finding count."""
        return self._object_type_totals

    def empty(self) -> bool:
        """Return True when the source repository contains no findings."""
        return self._repository.empty()


def _severity_totals(
    repository: ValidationRepository,
) -> Mapping[ValidationSeverity, int]:
    """Count findings per ValidationSeverity in definition order."""
    return MappingProxyType(
        {
            severity: len(repository.by_severity(severity))
            for severity in ValidationSeverity
        }
    )


def _validation_type_totals(
    repository: ValidationRepository,
) -> Mapping[ValidationType, int]:
    """Count findings per ValidationType in definition order."""
    return MappingProxyType(
        {
            validation_type: len(repository.by_validation_type(validation_type))
            for validation_type in ValidationType
        }
    )


def _object_type_totals(
    repository: ValidationRepository,
) -> Mapping[ObjectType, int]:
    """Count findings per ObjectType in definition order."""
    return MappingProxyType(
        {
            object_type: len(repository.by_object_type(object_type))
            for object_type in ObjectType
        }
    )
