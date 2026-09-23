"""Thin test adapter around the production analysis pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ha_docgen import main as cli
from ha_docgen._pipeline import _build_project_analysis
from ha_docgen.config import ProjectConfig
from ha_docgen.document import DocumentRepository
from ha_docgen.graph import DependencyGraph
from ha_docgen.project import ProjectTree
from ha_docgen.registries import HomeAssistantModel
from ha_docgen.relationships import RelationshipRepository
from ha_docgen.reporting import Report, ReportMetadata
from ha_docgen.validation import ValidationReport, ValidationRepository
from ha_docgen.yaml import YamlRepository

_REPORT_COMMANDS = (
    "health",
    "config",
    "architecture",
    "inventory",
    "dependencies",
    "docs",
)


@dataclass(frozen=True, slots=True)
class IntegrationPipeline:
    """Immutable outputs from one complete integration workflow."""

    project_tree: ProjectTree
    model: HomeAssistantModel
    yaml_repository: YamlRepository
    relationships: RelationshipRepository
    graph: DependencyGraph
    validations: ValidationRepository
    validation_report: ValidationReport
    documents: DocumentRepository
    reports: tuple[Report, ...]


def build_integration_pipeline(config: ProjectConfig) -> IntegrationPipeline:
    """Adapt one real production analysis for deterministic test assertions."""
    analysis = _build_project_analysis(config)
    reports = tuple(
        cli._generate_report_from_analysis(
            command,
            analysis,
            stable_report_metadata(),
        )
        for command in _REPORT_COMMANDS
    )
    return IntegrationPipeline(
        analysis.project_tree,
        analysis.model,
        analysis.yaml_repository,
        analysis.relationships,
        analysis.graph,
        analysis.validations,
        ValidationReport(analysis.validations),
        analysis.documents,
        reports,
    )


def stable_report_metadata() -> ReportMetadata:
    """Return metadata without clock or machine-specific values."""
    return ReportMetadata(
        generated_at=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
        version="0.1.0",
        project_path=Path("project"),
        execution_time=0.25,
    )
