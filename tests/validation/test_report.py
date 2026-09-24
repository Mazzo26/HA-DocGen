"""Unit tests for ValidationReport."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import pytest

from ha_docgen.registries.models import Entity
from ha_docgen.relationships.models import ObjectType
from ha_docgen.relationships.repository import RelationshipRepository
from ha_docgen.validation import (
    EntityValidator,
    ValidationReport,
    ValidationRepository,
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)
from tests.support import build_validation_result


def _report(
    *results: ValidationResult,
) -> ValidationReport:
    return ValidationReport(ValidationRepository(results))


def test_empty_repository() -> None:
    repository = ValidationRepository()
    report = ValidationReport(repository)
    assert report.repository() is repository
    assert report.total_findings() == 0
    assert report.error_count() == 0
    assert report.warning_count() == 0
    assert report.info_count() == 0
    assert report.empty() is True
    assert report.severity_totals() == MappingProxyType(
        {severity: 0 for severity in ValidationSeverity}
    )
    assert report.validation_type_totals() == MappingProxyType(
        {validation_type: 0 for validation_type in ValidationType}
    )
    assert report.object_type_totals() == MappingProxyType(
        {object_type: 0 for object_type in ObjectType}
    )


def test_single_finding() -> None:
    result = build_validation_result()
    report = _report(result)
    assert report.total_findings() == 1
    assert report.error_count() == 1
    assert report.warning_count() == 0
    assert report.info_count() == 0
    assert report.empty() is False
    assert report.severity_totals()[ValidationSeverity.ERROR] == 1
    assert report.validation_type_totals()[ValidationType.INVALID_CONFIGURATION] == 1
    assert report.object_type_totals()[ObjectType.ENTITY] == 1


def test_multiple_findings() -> None:
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
    report = _report(info, error, warning)
    assert report.total_findings() == 3
    assert report.error_count() == 1
    assert report.warning_count() == 1
    assert report.info_count() == 1
    assert report.empty() is False


def test_severity_totals() -> None:
    report = _report(
        build_validation_result(object_id="light.error"),
        build_validation_result(
            object_id="light.warning",
            severity=ValidationSeverity.WARNING,
            message="Automation has no alias.",
        ),
        build_validation_result(
            object_id="light.info",
            severity=ValidationSeverity.INFO,
            validation_type=ValidationType.CUSTOM,
            message="Informational note.",
        ),
        build_validation_result(
            object_id="light.second-error",
            message="Duplicate entity ID.",
        ),
    )
    totals = report.severity_totals()
    assert totals[ValidationSeverity.ERROR] == 2
    assert totals[ValidationSeverity.WARNING] == 1
    assert totals[ValidationSeverity.INFO] == 1
    assert report.error_count() == 2
    assert report.warning_count() == 1
    assert report.info_count() == 1
    assert sum(totals.values()) == report.total_findings()


def test_validation_type_totals() -> None:
    report = _report(
        build_validation_result(),
        build_validation_result(
            object_id="light.other",
            validation_type=ValidationType.DUPLICATE,
            message="Duplicate entity ID.",
        ),
        build_validation_result(
            object_id="light.third",
            validation_type=ValidationType.DUPLICATE,
            message="Duplicate unique ID.",
        ),
    )
    totals = report.validation_type_totals()
    assert totals[ValidationType.INVALID_CONFIGURATION] == 1
    assert totals[ValidationType.DUPLICATE] == 2
    assert totals[ValidationType.UNREFERENCED_OBJECT] == 0
    assert totals[ValidationType.UNSUPPORTED] == 0
    assert totals[ValidationType.CUSTOM] == 0
    assert list(totals) == list(ValidationType)


def test_object_type_totals() -> None:
    report = _report(
        build_validation_result(),
        build_validation_result(
            object_type=ObjectType.AUTOMATION,
            object_id="morning",
            message="Automation ID is empty.",
        ),
        build_validation_result(
            object_type=ObjectType.SCRIPT,
            object_id="evening",
            message="Script ID is empty.",
        ),
        build_validation_result(
            object_type=ObjectType.AUTOMATION,
            object_id="night",
            message="Automation has no alias.",
        ),
    )
    totals = report.object_type_totals()
    assert totals[ObjectType.ENTITY] == 1
    assert totals[ObjectType.AUTOMATION] == 2
    assert totals[ObjectType.SCRIPT] == 1
    assert totals[ObjectType.DASHBOARD] == 0
    assert list(totals) == list(ObjectType)


def test_deterministic_ordering() -> None:
    report = _report(
        build_validation_result(object_type=ObjectType.SCRIPT, object_id="z"),
        build_validation_result(
            object_id="light.a",
            validation_type=ValidationType.DUPLICATE,
            message="Duplicate entity ID.",
        ),
        build_validation_result(object_id="light.z"),
    )
    assert list(report.severity_totals()) == list(ValidationSeverity)
    assert list(report.validation_type_totals()) == list(ValidationType)
    assert list(report.object_type_totals()) == list(ObjectType)
    second = _report(
        build_validation_result(object_id="light.z"),
        build_validation_result(object_type=ObjectType.SCRIPT, object_id="z"),
        build_validation_result(
            object_id="light.a",
            validation_type=ValidationType.DUPLICATE,
            message="Duplicate entity ID.",
        ),
    )
    assert report.severity_totals() == second.severity_totals()
    assert report.validation_type_totals() == second.validation_type_totals()
    assert report.object_type_totals() == second.object_type_totals()
    assert report.total_findings() == second.total_findings()


def test_immutable_report() -> None:
    report = _report(build_validation_result())
    with pytest.raises(FrozenInstanceError):
        report._repository = ValidationRepository()  # type: ignore[misc]
    with pytest.raises(TypeError):
        report.severity_totals()[ValidationSeverity.ERROR] = 99  # type: ignore[index]
    with pytest.raises(TypeError):
        report.validation_type_totals()[ValidationType.CUSTOM] = 1  # type: ignore[index]
    with pytest.raises(TypeError):
        report.object_type_totals()[ObjectType.ENTITY] = 0  # type: ignore[index]
    assert isinstance(report.severity_totals(), MappingProxyType)
    assert isinstance(report.validation_type_totals(), MappingProxyType)
    assert isinstance(report.object_type_totals(), MappingProxyType)


def test_empty() -> None:
    assert _report().empty() is True
    assert _report(build_validation_result()).empty() is False


def test_total_findings() -> None:
    assert _report().total_findings() == 0
    assert _report(build_validation_result()).total_findings() == 1
    populated = _report(
        build_validation_result(),
        build_validation_result(object_id="light.other"),
    )
    assert populated.total_findings() == 2
    assert populated.total_findings() == populated.repository().count()


def test_repository_identity() -> None:
    repository = ValidationRepository((build_validation_result(),))
    report = ValidationReport(repository=repository)
    assert report.repository() is repository
    assert report.repository() is report.repository()


def test_does_not_mutate_results() -> None:
    result = build_validation_result()
    original = (
        result.object_type,
        result.object_id,
        result.validation_type,
        result.severity,
        result.message,
    )
    report = _report(result)
    stored = report.repository().all()[0]
    assert (
        stored.object_type,
        stored.object_id,
        stored.validation_type,
        stored.severity,
        stored.message,
    ) == original
    assert stored is result


def test_integrates_with_entity_validator() -> None:
    entities = (
        Entity(registry_id="a", entity_id="light.one", unique_id="a"),
        Entity(registry_id="b", entity_id="light.one", unique_id="b"),
        Entity(registry_id="c", entity_id="", unique_id="c"),
    )
    findings = EntityValidator().validate(entities, RelationshipRepository())
    repository = ValidationRepository(findings)
    report = ValidationReport(repository)
    assert report.empty() is False
    assert report.total_findings() == repository.count()
    assert report.error_count() == len(repository.errors())
    assert report.object_type_totals()[ObjectType.ENTITY] == report.total_findings()
    assert report.validation_type_totals()[ValidationType.DUPLICATE] >= 1
