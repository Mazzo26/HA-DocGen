"""Unit tests for DocumentationIndexReportGenerator."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from tools.ha_docgen.automation import Automation
from tools.ha_docgen.document import Document, DocumentRepository
from tools.ha_docgen.helper import Helper
from tools.ha_docgen.packages import Package
from tools.ha_docgen.registries import ConfigEntry, Entity, HomeAssistantModel
from tools.ha_docgen.relationships import (
    ObjectType,
    Relationship,
    RelationshipRepository,
    RelationshipType,
)
from tools.ha_docgen.reporting import (
    DocumentationIndexReportGenerator,
    Report,
    ReportMetadata,
    ReportSection,
    Severity,
)
from tools.ha_docgen.script import Script
from tools.ha_docgen.yaml import YamlDocument, YamlRepository


def _metadata() -> ReportMetadata:
    return ReportMetadata(
        generated_at=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
        version="0.2.0",
        project_path=Path("/config"),
        execution_time=0.25,
    )


def _package(name: str) -> Package:
    path = Path(f"/config/packages/{name}.yaml")
    return Package(
        name=name,
        path=path,
        document=YamlDocument(path=path, text="", data={}),
    )


def _entity(entity_id: str) -> Entity:
    return Entity(registry_id=entity_id, entity_id=entity_id, unique_id=entity_id)


def _section(report: Report, title: str) -> ReportSection:
    return next(section for section in report.sections if section.title == title)


def _generate(
    model: HomeAssistantModel | None = None,
    yaml_repository: YamlRepository | None = None,
    document_repository: DocumentRepository | None = None,
    relationship_repository: RelationshipRepository | None = None,
) -> Report:
    return DocumentationIndexReportGenerator().generate(
        model or HomeAssistantModel(),
        yaml_repository or YamlRepository(),
        document_repository or DocumentRepository(),
        relationship_repository or RelationshipRepository(),
        _metadata(),
    )


def _entity_coverage_report(*document_titles: str) -> Report:
    return _generate(
        model=HomeAssistantModel(entities=(_entity("light.kitchen"),)),
        document_repository=DocumentRepository(
            tuple(Document(title, ()) for title in document_titles)
        ),
    )


def test_empty_documentation() -> None:
    report = _generate()
    assert isinstance(report, Report)
    assert report.title == "Documentation Index Report"
    assert report.summary == "No documentation information is available."
    assert report.sections == ()
    assert report.recommendations == ()
    assert all(value == 0 for value in report.statistics.values())


def test_exact_document_title_matches() -> None:
    report = _entity_coverage_report("Entity: light.kitchen")
    assert report.statistics["total_documented_entities"] == 1


def test_document_title_matching_is_case_insensitive() -> None:
    report = _entity_coverage_report("eNtItY: LIGHT.KITCHEN")
    assert report.statistics["total_documented_entities"] == 1


def test_document_title_matching_ignores_surrounding_whitespace() -> None:
    report = _entity_coverage_report("  Entity: light.kitchen \t")
    assert report.statistics["total_documented_entities"] == 1


def test_missing_document_title_does_not_match() -> None:
    report = _entity_coverage_report("Entity: light.other")
    assert report.statistics["total_documented_entities"] == 0


def test_duplicate_normalised_titles_are_deterministic() -> None:
    titles = (" Entity: light.kitchen", "entity: LIGHT.KITCHEN ")
    first = _entity_coverage_report(*titles)
    second = _entity_coverage_report(*reversed(titles))
    assert first == second
    assert first.statistics["total_generated_documents"] == 2
    assert first.statistics["total_documented_entities"] == 1


def test_minimal_project_summary_statistics_and_recommendations() -> None:
    package = _package("core")
    report = _generate(
        model=HomeAssistantModel(entities=(_entity("light.kitchen"),)),
        yaml_repository=YamlRepository(
            packages=(package,),
            automations=(Automation(package=package, id="welcome"),),
        ),
    )
    assert report.summary == (
        "Documentation overview: 3 known object(s), 0 generated document(s), "
        "and 0 index entries."
    )
    assert report.statistics["total_documentation_objects"] == 3
    assert report.statistics["total_generated_documents"] == 0
    assert report.statistics["total_documented_entities"] == 0
    assert report.statistics["total_documented_automations"] == 0
    assert report.recommendations == (
        "Generate documentation for 1 undocumented package.",
        "Generate documentation for 1 undocumented entity.",
        "Generate documentation for 1 undocumented automation.",
    )
    assert _section(report, "Summary").severity is Severity.INFO


def test_multiple_documentation_objects_and_generated_index_entries() -> None:
    alpha = _package("alpha")
    beta = _package("beta")
    model = HomeAssistantModel(
        entities=(_entity("sensor.zeta"), _entity("light.alpha")),
        config_entries=(
            ConfigEntry(registry_id="1", domain="mqtt", title="MQTT"),
            ConfigEntry(registry_id="2", domain="mqtt", title="MQTT duplicate"),
            ConfigEntry(registry_id="3", domain="zha", title="ZHA"),
        ),
    )
    repository = YamlRepository(
        packages=(beta, alpha),
        automations=(
            Automation(package=alpha, id="morning", alias="Morning"),
            Automation(package=beta, id="night"),
            Automation(package=beta),
        ),
        scripts=(
            Script(package=alpha, id="notify"),
            Script(package=alpha, alias="Alias only"),
            Script(package=beta),
        ),
        helpers=(Helper(package=alpha, type="input_boolean", id="guest"),),
    )
    documents = DocumentRepository(
        (
            Document("Entity: light.alpha", ()),
            Document("Automation: Morning", ()),
            Document("Package: alpha", ()),
            Document("General Guide", ()),
        )
    )
    report = _generate(model, repository, documents)
    inventory = _section(report, "Documentation Inventory")
    assert inventory.items == tuple(sorted(inventory.items))
    assert "Integration: mqtt" in inventory.items
    assert "Integration: zha" in inventory.items
    assert inventory.items.count("Integration: mqtt") == 1
    assert "Automation: (unnamed)" in inventory.items
    assert "Script: Alias only" in inventory.items
    assert "Script: (unnamed)" in inventory.items
    assert "Generated documentation: General Guide" in inventory.items
    assert "Index entry: General Guide" in inventory.items
    assert not any(section.title == "Generated Files" for section in report.sections)
    assert report.statistics["total_documentation_objects"] == 13
    assert report.statistics["total_generated_documents"] == 4
    assert report.statistics["total_index_entries"] == 4
    assert report.statistics["total_documented_packages"] == 1
    assert report.statistics["total_documented_entities"] == 1
    assert report.statistics["total_documented_automations"] == 1


def test_cross_references_reuse_existing_relationships() -> None:
    relationships = RelationshipRepository(
        (
            Relationship(
                source_type=ObjectType.AUTOMATION,
                source_id="morning",
                target_type=ObjectType.ENTITY,
                target_id="light.kitchen",
                relationship_type=RelationshipType.REFERENCES,
            ),
        )
    )
    report = _generate(relationship_repository=relationships)
    cross_references = _section(report, "Cross References")
    assert cross_references.items == ("automation:morning references entity:light.kitchen",)
    assert report.statistics["total_cross_references"] == 1
    assert report.recommendations == ()
    assert _section(report, "Statistics").items == tuple(
        f"{key}: {value}" for key, value in sorted(report.statistics.items())
    )


def test_complete_documentation_has_no_recommendations() -> None:
    package = _package("core")
    model = HomeAssistantModel(entities=(_entity("light.kitchen"),))
    repository = YamlRepository(
        packages=(package,),
        automations=(
            Automation(package=package, id="welcome", alias="Welcome"),
            Automation(package=package, id="night"),
        ),
    )
    documents = DocumentRepository(
        (
            Document("Package: core", ()),
            Document("Entity: light.kitchen", ()),
            Document("Automation: Welcome", ()),
            Document("Automation: night", ()),
        )
    )
    report = _generate(model, repository, documents)
    assert report.recommendations == ()
    assert report.statistics["total_documented_automations"] == 2


def test_generated_document_without_source_objects_is_reported() -> None:
    report = _generate(document_repository=DocumentRepository((Document("General Guide", ()),)))
    assert report.summary.endswith("and 1 index entry.")
    assert report.statistics["total_documentation_objects"] == 0
    assert report.statistics["total_generated_documents"] == 1
    assert _section(report, "Documentation Inventory").items == (
        "Generated documentation: General Guide",
        "Index entry: General Guide",
    )


def test_generator_is_stateless_deterministic_and_preserves_metadata() -> None:
    package = _package("core")
    model = HomeAssistantModel(entities=(_entity("light.b"), _entity("light.a")))
    repository = YamlRepository(packages=(package,))
    documents = DocumentRepository(
        (Document("Entity: light.b", ()), Document("Entity: light.a", ()))
    )
    metadata = _metadata()
    generator = DocumentationIndexReportGenerator()
    first = generator.generate(
        model,
        repository,
        documents,
        RelationshipRepository(),
        metadata,
    )
    second = generator.generate(
        model,
        repository,
        documents,
        RelationshipRepository(),
        metadata,
    )
    assert first == second
    assert first.metadata is metadata
    assert list(first.statistics) == sorted(first.statistics)
