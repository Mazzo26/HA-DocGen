"""Unit tests for InventoryReportGenerator."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from tools.ha_docgen.packages import Package
from tools.ha_docgen.project import ProjectFile, ProjectFolder, ProjectTree
from tools.ha_docgen.registries import ConfigEntry, Entity, HomeAssistantModel
from tools.ha_docgen.reporting import (
    InventoryReportGenerator,
    Report,
    ReportMetadata,
    ReportSection,
    Severity,
)
from tools.ha_docgen.yaml import YamlDocument, YamlRepository


def _metadata() -> ReportMetadata:
    return ReportMetadata(
        generated_at=datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
        version="0.2.0",
        project_path=Path("/config"),
        execution_time=0.25,
    )


def _entity(entity_id: str) -> Entity:
    return Entity(registry_id=entity_id, entity_id=entity_id, unique_id=entity_id)


def _package(name: str) -> Package:
    path = Path(f"/config/packages/{name}.yaml")
    return Package(
        name=name,
        path=path,
        document=YamlDocument(path=path, text="", data={}),
    )


def _project_tree(*relative_paths: str) -> ProjectTree:
    root = Path("/config")
    folder = ProjectFolder(
        name="config",
        path=root,
        relative_path=Path("."),
    )
    folder.files = [
        ProjectFile(
            name=Path(relative_path).name,
            path=root / relative_path,
            relative_path=Path(relative_path),
            extension=Path(relative_path).suffix,
            size=10,
            modified=datetime(2026, 9, 21, tzinfo=UTC),
        )
        for relative_path in relative_paths
    ]
    return ProjectTree(root=root, folders=[folder])


def _section(report: Report, title: str) -> ReportSection:
    return next(section for section in report.sections if section.title == title)


def test_empty_inventory() -> None:
    report = InventoryReportGenerator().generate(
        HomeAssistantModel(),
        YamlRepository(),
        _project_tree(),
        _metadata(),
    )
    assert isinstance(report, Report)
    assert report.title == "Inventory Report"
    assert report.summary == "No inventory information is available."
    assert report.sections == ()
    assert report.recommendations == ()
    assert all(value == 0 for value in report.statistics.values())


def test_full_inventory_listing_and_statistics() -> None:
    model = HomeAssistantModel(
        entities=(_entity("light.kitchen"), _entity("sensor.temp")),
        config_entries=(
            ConfigEntry(registry_id="1", domain="mqtt", title="MQTT"),
            ConfigEntry(registry_id="2", domain="zwave_js", title="Z-Wave"),
            ConfigEntry(registry_id="3", domain="mqtt", title="MQTT Dup"),
        ),
    )
    repository = YamlRepository(packages=(_package("lighting"), _package("climate")))
    tree = _project_tree("packages/lighting.yaml", "configuration.yaml")
    report = InventoryReportGenerator().generate(model, repository, tree, _metadata())
    inventory = _section(report, "Inventory")
    assert inventory.items == (
        "Entity: light.kitchen",
        "Entity: sensor.temp",
        "Integration: mqtt",
        "Integration: zwave_js",
        "Domain: light",
        "Domain: sensor",
        "Package: climate",
        "Package: lighting",
        "File: configuration.yaml",
        "File: packages/lighting.yaml",
    )
    assert report.statistics == {
        "total_domains": 2,
        "total_entities": 2,
        "total_files": 2,
        "total_integrations": 2,
        "total_packages": 2,
    }
    assert report.summary == (
        "Inventory overview: 2 entities, 2 integration(s), "
        "2 domain(s), 2 package(s), and 2 file(s)."
    )
    summary = _section(report, "Summary")
    assert summary.severity is Severity.INFO
    assert summary.items == (
        "Entities: 2",
        "Integrations: 2",
        "Domains: 2",
        "Packages: 2",
        "Files: 2",
    )


def test_duplicate_files_are_deduplicated() -> None:
    tree = _project_tree("configuration.yaml")
    tree.folders.append(
        ProjectFolder(
            name="duplicate",
            path=Path("/config/duplicate"),
            relative_path=Path("duplicate"),
            files=[tree.folders[0].files[0]],
        )
    )
    report = InventoryReportGenerator().generate(
        HomeAssistantModel(),
        YamlRepository(),
        tree,
        _metadata(),
    )
    assert report.statistics["total_files"] == 1
    assert _section(report, "Inventory").items == ("File: configuration.yaml",)


def test_recommendations_from_inventory_gaps() -> None:
    report = InventoryReportGenerator().generate(
        HomeAssistantModel(entities=(_entity("light.kitchen"),)),
        YamlRepository(),
        _project_tree("configuration.yaml"),
        _metadata(),
    )
    assert report.recommendations == (
        "Analysed files are present without detected packages.",
        "Entities are present without detected config-entry integrations.",
    )


def test_generator_is_stateless_deterministic_and_preserves_metadata() -> None:
    generator = InventoryReportGenerator()
    model = HomeAssistantModel(entities=(_entity("light.b"), _entity("light.a")))
    repository = YamlRepository(packages=(_package("zeta"), _package("alpha")))
    tree = _project_tree("b.yaml", "a.yaml")
    metadata = _metadata()
    first = generator.generate(model, repository, tree, metadata)
    second = generator.generate(model, repository, tree, metadata)
    assert first == second
    assert first.metadata is metadata
    assert list(first.statistics.keys()) == sorted(first.statistics.keys())
