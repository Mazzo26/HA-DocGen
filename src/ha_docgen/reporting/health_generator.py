"""Build a Health Report from validation findings.

Transforms a ``ValidationRepository`` into one immutable ``Report``.
Produces report models only — no Markdown, JSON, console output,
filesystem writes or CLI coupling.
"""

from __future__ import annotations

from ..validation.models import ValidationResult, ValidationType
from ..validation.report import ValidationReport
from ..validation.repository import ValidationRepository
from .models import Report, ReportMetadata, ReportSection, Severity

_TITLE = "Health Report"
_DESCRIPTION = (
    "Configuration health derived from validation findings."
)


class HealthReportGenerator:
    """Generate a Health Report from a ValidationRepository.

    Fully stateless: no instance state, no caching, no filesystem and
    no side effects. Callers supply an already-built repository and
    report metadata.
    """

    def generate(
        self,
        repository: ValidationRepository,
        metadata: ReportMetadata,
    ) -> Report:
        """Return a Health Report aggregating the given validation findings."""
        validation = ValidationReport(repository)
        return Report(
            title=_TITLE,
            metadata=metadata,
            description=_DESCRIPTION,
            sections=_build_sections(repository, validation),
            statistics=_build_statistics(validation),
            recommendations=_build_recommendations(validation),
            summary=_build_summary(validation),
        )


def _build_summary(validation: ValidationReport) -> str:
    """Derive overall health status from severity totals."""
    errors = validation.error_count()
    warnings = validation.warning_count()
    info = validation.info_count()
    if errors > 0:
        return (
            f"Unhealthy: {errors} error(s), {warnings} warning(s), "
            f"{info} informational message(s)."
        )
    if warnings > 0:
        return (
            f"Degraded: 0 errors, {warnings} warning(s), "
            f"{info} informational message(s)."
        )
    if info > 0:
        return (
            f"Healthy with informational findings: "
            f"{info} informational message(s)."
        )
    return "Healthy: no validation findings."


def _build_statistics(validation: ValidationReport) -> dict[str, int | float]:
    """Aggregate validation and severity totals into report statistics."""
    statistics: dict[str, int | float] = {
        "total_findings": validation.total_findings(),
        "errors": validation.error_count(),
        "warnings": validation.warning_count(),
        "info": validation.info_count(),
    }
    for validation_type, count in validation.validation_type_totals().items():
        statistics[f"validation_type_{validation_type.value}"] = count
    for object_type, count in validation.object_type_totals().items():
        if count > 0:
            statistics[f"object_type_{object_type.value}"] = count
    return statistics


def _build_sections(
    repository: ValidationRepository,
    validation: ValidationReport,
) -> tuple[ReportSection, ...]:
    """Build Validation Summary, Errors, Warnings and Informational sections."""
    return (
        _validation_summary_section(validation),
        _findings_section(
            title="Errors",
            severity=Severity.ERROR,
            findings=repository.errors(),
            description="Validation findings with severity ERROR.",
        ),
        _findings_section(
            title="Warnings",
            severity=Severity.WARNING,
            findings=repository.warnings(),
            description="Validation findings with severity WARNING.",
        ),
        _findings_section(
            title="Informational",
            severity=Severity.INFO,
            findings=repository.info(),
            description="Validation findings with severity INFO.",
        ),
    )


def _validation_summary_section(validation: ValidationReport) -> ReportSection:
    """Build the Validation Summary section from severity totals."""
    return ReportSection(
        title="Validation Summary",
        severity=Severity.INFO,
        description="Overall validation counts by severity.",
        items=(
            f"Total findings: {validation.total_findings()}",
            f"Errors: {validation.error_count()}",
            f"Warnings: {validation.warning_count()}",
            f"Informational: {validation.info_count()}",
        ),
    )


def _findings_section(
    *,
    title: str,
    severity: Severity,
    findings: tuple[ValidationResult, ...],
    description: str,
) -> ReportSection:
    """Build one severity section with formatted finding items."""
    return ReportSection(
        title=title,
        severity=severity,
        description=description,
        items=tuple(_format_finding(finding) for finding in findings),
    )


def _format_finding(finding: ValidationResult) -> str:
    """Format one ValidationResult as a plain-text report item."""
    return (
        f"{finding.object_type.value}:{finding.object_id} "
        f"[{finding.validation_type.value}] {finding.message}"
    )


def _build_recommendations(validation: ValidationReport) -> tuple[str, ...]:
    """Derive simple recommendations from validation outcome totals."""
    if validation.empty():
        return ("No action required; validation found no issues.",)

    recommendations: list[str] = []
    if validation.error_count() > 0:
        recommendations.append(
            "Resolve all validation errors before relying on generated "
            "documentation."
        )
    if validation.warning_count() > 0:
        recommendations.append(
            "Review validation warnings to improve configuration quality."
        )
    if validation.info_count() > 0:
        recommendations.append("Review informational validation messages.")
    recommendations.extend(_type_recommendations(validation))
    return tuple(recommendations)


def _type_recommendations(validation: ValidationReport) -> tuple[str, ...]:
    """Recommend actions for validation types that have findings."""
    totals = validation.validation_type_totals()
    recommendations: list[str] = []
    if totals[ValidationType.DUPLICATE] > 0:
        recommendations.append("Remove or rename duplicate identifiers.")
    if totals[ValidationType.INVALID_CONFIGURATION] > 0:
        recommendations.append("Correct invalid configuration findings.")
    if totals[ValidationType.UNREFERENCED_OBJECT] > 0:
        recommendations.append(
            "Investigate unreferenced objects reported by validation."
        )
    if totals[ValidationType.UNSUPPORTED] > 0:
        recommendations.append("Address unsupported configuration findings.")
    if totals[ValidationType.CUSTOM] > 0:
        recommendations.append("Review custom validation findings.")
    return tuple(recommendations)
