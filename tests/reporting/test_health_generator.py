"""Unit tests for HealthReportGenerator."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ha_docgen.relationships.models import ObjectType
from ha_docgen.reporting import (
    HealthReportGenerator,
    Report,
    ReportMetadata,
    Severity,
)
from tests.support import build_validation_result
from ha_docgen.validation import (
    ValidationRepository,
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)


def _metadata(
    *,
    generated_at: datetime | None = None,
    version: str = "0.2.0",
    project_path: Path | None = None,
    execution_time: float = 0.5,
) -> ReportMetadata:
    return ReportMetadata(
        generated_at=generated_at or datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
        version=version,
        project_path=project_path or Path("/config"),
        execution_time=execution_time,
    )


def _generate(*results: ValidationResult) -> Report:
    return HealthReportGenerator().generate(
        ValidationRepository(results),
        _metadata(),
    )


# --- Empty -------------------------------------------------------------------


def test_empty_validation_result() -> None:
    report = _generate()
    assert report.title == "Health Report"
    assert report.description == ("Configuration health derived from validation findings.")
    assert report.summary == "Healthy: no validation findings."
    assert report.recommendations == ("No action required; validation found no issues.",)
    assert report.statistics["total_findings"] == 0
    assert report.statistics["errors"] == 0
    assert report.statistics["warnings"] == 0
    assert report.statistics["info"] == 0
    assert report.sections[0].title == "Validation Summary"
    assert report.sections[0].items == (
        "Total findings: 0",
        "Errors: 0",
        "Warnings: 0",
        "Informational: 0",
    )
    assert report.sections[1].title == "Errors"
    assert report.sections[1].items == ()
    assert report.sections[2].title == "Warnings"
    assert report.sections[2].items == ()
    assert report.sections[3].title == "Informational"
    assert report.sections[3].items == ()


def test_empty_preserves_metadata() -> None:
    metadata = _metadata(version="9.9.9", execution_time=1.5)
    report = HealthReportGenerator().generate(ValidationRepository(), metadata)
    assert report.metadata is metadata
    assert report.metadata.version == "9.9.9"
    assert report.metadata.execution_time == 1.5


# --- Errors only -------------------------------------------------------------


def test_errors_only() -> None:
    report = _generate(
        build_validation_result(object_id="light.one"),
        build_validation_result(
            object_id="light.two",
            validation_type=ValidationType.DUPLICATE,
            message="Duplicate entity ID.",
        ),
    )
    assert report.summary.startswith("Unhealthy:")
    assert "2 error(s)" in report.summary
    assert "0 warning(s)" in report.summary
    assert report.statistics["errors"] == 2
    assert report.statistics["warnings"] == 0
    assert report.statistics["info"] == 0
    assert report.sections[1].severity is Severity.ERROR
    assert len(report.sections[1].items) == 2
    assert report.sections[2].items == ()
    assert report.sections[3].items == ()
    assert (
        "Resolve all validation errors before relying on generated documentation."
    ) in report.recommendations
    assert "Remove or rename duplicate identifiers." in report.recommendations
    assert "Correct invalid configuration findings." in report.recommendations


# --- Warnings only -----------------------------------------------------------


def test_warnings_only() -> None:
    report = _generate(
        build_validation_result(
            object_id="automation.one",
            object_type=ObjectType.AUTOMATION,
            severity=ValidationSeverity.WARNING,
            message="Automation has no alias.",
        ),
    )
    assert report.summary.startswith("Degraded:")
    assert "0 errors" in report.summary
    assert "1 warning(s)" in report.summary
    assert report.statistics["errors"] == 0
    assert report.statistics["warnings"] == 1
    assert report.sections[1].items == ()
    assert report.sections[2].severity is Severity.WARNING
    assert len(report.sections[2].items) == 1
    assert "Review validation warnings to improve configuration quality." in report.recommendations
    assert not any("errors" in item.lower() for item in report.recommendations)


# --- Mixed severities --------------------------------------------------------


def test_mixed_severities() -> None:
    report = _generate(
        build_validation_result(object_id="light.error"),
        build_validation_result(
            object_id="light.warning",
            severity=ValidationSeverity.WARNING,
            validation_type=ValidationType.UNREFERENCED_OBJECT,
            message="No relationships found.",
        ),
        build_validation_result(
            object_id="light.info",
            severity=ValidationSeverity.INFO,
            validation_type=ValidationType.CUSTOM,
            message="Informational note.",
        ),
    )
    assert report.summary.startswith("Unhealthy:")
    assert report.statistics["total_findings"] == 3
    assert report.statistics["errors"] == 1
    assert report.statistics["warnings"] == 1
    assert report.statistics["info"] == 1
    assert len(report.sections[1].items) == 1
    assert len(report.sections[2].items) == 1
    assert len(report.sections[3].items) == 1
    assert report.sections[3].severity is Severity.INFO


def test_info_only_is_healthy_with_notes() -> None:
    report = _generate(
        build_validation_result(
            object_id="script.note",
            object_type=ObjectType.SCRIPT,
            severity=ValidationSeverity.INFO,
            validation_type=ValidationType.CUSTOM,
            message="Informational note.",
        ),
    )
    assert report.summary.startswith("Healthy with informational findings:")
    assert report.statistics["errors"] == 0
    assert report.statistics["warnings"] == 0
    assert report.statistics["info"] == 1
    assert "Review informational validation messages." in report.recommendations
    assert "Review custom validation findings." in report.recommendations


# --- Statistics --------------------------------------------------------------


def test_statistics_include_validation_type_totals() -> None:
    report = _generate(
        build_validation_result(validation_type=ValidationType.INVALID_CONFIGURATION),
        build_validation_result(
            object_id="light.dup",
            validation_type=ValidationType.DUPLICATE,
            message="Duplicate entity ID.",
        ),
        build_validation_result(
            object_id="light.warn",
            severity=ValidationSeverity.WARNING,
            validation_type=ValidationType.UNREFERENCED_OBJECT,
            message="No relationships found.",
        ),
    )
    assert report.statistics["validation_type_invalid_configuration"] == 1
    assert report.statistics["validation_type_duplicate"] == 1
    assert report.statistics["validation_type_unreferenced_object"] == 1
    assert report.statistics["validation_type_unsupported"] == 0
    assert report.statistics["validation_type_custom"] == 0


def test_statistics_include_non_zero_object_type_totals() -> None:
    report = _generate(
        build_validation_result(object_type=ObjectType.ENTITY, object_id="light.a"),
        build_validation_result(
            object_type=ObjectType.AUTOMATION,
            object_id="auto.a",
            message="Automation ID is empty.",
        ),
    )
    assert report.statistics["object_type_entity"] == 1
    assert report.statistics["object_type_automation"] == 1
    assert "object_type_script" not in report.statistics


def test_statistics_keys_are_sorted() -> None:
    report = _generate(build_validation_result())
    keys = list(report.statistics.keys())
    assert keys == sorted(keys)


# --- Summary -----------------------------------------------------------------


def test_summary_counts_match_statistics() -> None:
    report = _generate(
        build_validation_result(object_id="e1"),
        build_validation_result(object_id="e2"),
        build_validation_result(
            object_id="w1",
            severity=ValidationSeverity.WARNING,
            message="Automation has no alias.",
        ),
        build_validation_result(
            object_id="i1",
            severity=ValidationSeverity.INFO,
            validation_type=ValidationType.CUSTOM,
            message="Note.",
        ),
    )
    assert "2 error(s)" in report.summary
    assert "1 warning(s)" in report.summary
    assert "1 informational message(s)" in report.summary
    assert report.statistics["errors"] == 2
    assert report.statistics["warnings"] == 1
    assert report.statistics["info"] == 1


# --- Recommendations ---------------------------------------------------------


def test_recommendations_for_unsupported_findings() -> None:
    report = _generate(
        build_validation_result(
            object_id="script.x",
            object_type=ObjectType.SCRIPT,
            validation_type=ValidationType.UNSUPPORTED,
            message="Unsupported configuration.",
        ),
    )
    assert "Address unsupported configuration findings." in report.recommendations


def test_recommendations_order_is_deterministic() -> None:
    report = _generate(
        build_validation_result(object_id="e1"),
        build_validation_result(
            object_id="w1",
            severity=ValidationSeverity.WARNING,
            validation_type=ValidationType.UNREFERENCED_OBJECT,
            message="No relationships found.",
        ),
        build_validation_result(
            object_id="i1",
            severity=ValidationSeverity.INFO,
            validation_type=ValidationType.CUSTOM,
            message="Note.",
        ),
        build_validation_result(
            object_id="e2",
            validation_type=ValidationType.DUPLICATE,
            message="Duplicate entity ID.",
        ),
    )
    assert report.recommendations == (
        "Resolve all validation errors before relying on generated documentation.",
        "Review validation warnings to improve configuration quality.",
        "Review informational validation messages.",
        "Remove or rename duplicate identifiers.",
        "Correct invalid configuration findings.",
        "Investigate unreferenced objects reported by validation.",
        "Review custom validation findings.",
    )


# --- Finding formatting / sections -------------------------------------------


def test_finding_item_format() -> None:
    report = _generate(
        build_validation_result(
            object_type=ObjectType.AUTOMATION,
            object_id="auto.morning",
            validation_type=ValidationType.DUPLICATE,
            message="Duplicate automation ID.",
        ),
    )
    assert report.sections[1].items == (
        "automation:auto.morning [duplicate] Duplicate automation ID.",
    )


def test_section_descriptions() -> None:
    report = _generate()
    assert report.sections[0].description == ("Overall validation counts by severity.")
    assert report.sections[1].description == ("Validation findings with severity ERROR.")
    assert report.sections[2].description == ("Validation findings with severity WARNING.")
    assert report.sections[3].description == ("Validation findings with severity INFO.")


def test_generator_is_stateless_and_deterministic() -> None:
    generator = HealthReportGenerator()
    repository = ValidationRepository(
        (
            build_validation_result(object_id="light.b"),
            build_validation_result(object_id="light.a"),
        )
    )
    metadata = _metadata()
    first = generator.generate(repository, metadata)
    second = generator.generate(repository, metadata)
    assert first == second
    assert first.sections[1].items == second.sections[1].items
    assert list(first.statistics.keys()) == list(second.statistics.keys())


def test_returns_report_instance_not_strings() -> None:
    report = _generate(build_validation_result())
    assert isinstance(report, Report)
    assert not isinstance(report.summary, bytes)
    assert all(isinstance(item, str) for item in report.sections[1].items)


# --- Edge cases --------------------------------------------------------------


def test_duplicate_identical_findings_are_deduplicated_by_repository() -> None:
    finding = build_validation_result()
    report = _generate(finding, finding)
    assert report.statistics["total_findings"] == 1
    assert len(report.sections[1].items) == 1


def test_empty_object_id_still_formats() -> None:
    report = _generate(build_validation_result(object_id="", message="Entity ID is empty."))
    assert report.sections[1].items == ("entity: [invalid_configuration] Entity ID is empty.",)


def test_warnings_do_not_override_errors_in_summary() -> None:
    report = _generate(
        build_validation_result(object_id="e1"),
        build_validation_result(
            object_id="w1",
            severity=ValidationSeverity.WARNING,
            message="Automation has no alias.",
        ),
    )
    assert report.summary.startswith("Unhealthy:")
    assert not report.summary.startswith("Degraded:")
