"""Unit tests for ConfigurationReportGenerator."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

from ha_docgen.automation.models import Automation
from ha_docgen.helper.models import Helper
from ha_docgen.packages import Package
from ha_docgen.registries import ConfigEntry, Entity, HomeAssistantModel
from ha_docgen.reporting import (
    ConfigurationReportGenerator,
    Report,
    ReportMetadata,
    ReportSection,
    Severity,
)
from ha_docgen.script.models import Script
from ha_docgen.yaml import YamlDocument, YamlRepository


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


def _entity(
    entity_id: str,
    *,
    platform: str | None = None,
) -> Entity:
    extra = MappingProxyType({"platform": platform} if platform else {})
    return Entity(
        registry_id=entity_id,
        entity_id=entity_id,
        unique_id=entity_id,
        extra=extra,
    )


def _section(report: Report, title: str) -> ReportSection:
    return next(section for section in report.sections if section.title == title)


def test_empty_configuration() -> None:
    report = ConfigurationReportGenerator().generate(
        HomeAssistantModel(),
        YamlRepository(),
        _metadata(),
    )
    assert isinstance(report, Report)
    assert report.title == "Configuration Report"
    assert report.summary == "No configuration information is available."
    assert report.sections == ()
    assert report.recommendations == ()
    assert all(value == 0 for value in report.statistics.values())


def test_packages_automations_scripts_helpers_inventory() -> None:
    package = _package("lighting")
    repository = YamlRepository(
        packages=(package,),
        automations=(
            Automation(package=package, id="morning", alias="Morning"),
            Automation(package=package, alias="Only Alias"),
            Automation(package=package),
        ),
        scripts=(
            Script(package=package, id="notify", alias="Notify"),
            Script(package=package, alias="Alias Only"),
            Script(package=package),
        ),
        helpers=(Helper(package=package, type="input_boolean", id="guest_mode"),),
    )
    report = ConfigurationReportGenerator().generate(
        HomeAssistantModel(),
        repository,
        _metadata(),
    )
    inventory = _section(report, "Configuration Inventory")
    assert "Package: lighting" in inventory.items
    assert "Automation: morning" in inventory.items
    assert "Automation: Only Alias" in inventory.items
    assert "Automation: (unnamed)" in inventory.items
    assert "Script: notify" in inventory.items
    assert "Script: Alias Only" in inventory.items
    assert "Script: (unnamed)" in inventory.items
    assert "Helper: input_boolean.guest_mode" in inventory.items
    assert report.statistics["total_packages"] == 1
    assert report.statistics["total_automations"] == 3
    assert report.statistics["total_scripts"] == 3
    assert report.statistics["total_helpers"] == 1


def test_named_domains_mqtt_template_and_other_entities() -> None:
    model = HomeAssistantModel(
        entities=(
            _entity("sensor.temp"),
            _entity("binary_sensor.door"),
            _entity("switch.pump"),
            _entity("light.kitchen"),
            _entity("cover.garage"),
            _entity("climate.living"),
            _entity("camera.front"),
            _entity("sensor.mqtt_temp", platform="mqtt"),
            _entity("sensor.template_temp", platform="template"),
            _entity("fan.ceiling"),
            _entity("mqtt.legacy"),
        ),
        config_entries=(ConfigEntry(registry_id="1", domain="mqtt", title="MQTT"),),
    )
    report = ConfigurationReportGenerator().generate(
        model,
        YamlRepository(),
        _metadata(),
    )
    inventory = _section(report, "Configuration Inventory")
    assert "Sensor: sensor.temp" in inventory.items
    assert "Binary Sensor: binary_sensor.door" in inventory.items
    assert "Switch: switch.pump" in inventory.items
    assert "Light: light.kitchen" in inventory.items
    assert "Cover: cover.garage" in inventory.items
    assert "Climate: climate.living" in inventory.items
    assert "Camera: camera.front" in inventory.items
    assert "MQTT entity: sensor.mqtt_temp" in inventory.items
    assert "MQTT entity: mqtt.legacy" in inventory.items
    assert "Template entity: sensor.template_temp" in inventory.items
    assert "Other (fan): fan.ceiling" in inventory.items
    assert report.statistics["total_entities"] == 11
    assert report.statistics["total_sensors"] == 3
    assert report.statistics["total_mqtt_entities"] == 2
    assert report.statistics["total_template_entities"] == 1
    assert report.statistics["total_domains"] == 9


def test_summary_statistics_and_recommendations() -> None:
    model = HomeAssistantModel(entities=(_entity("light.kitchen"),))
    report = ConfigurationReportGenerator().generate(
        model,
        YamlRepository(),
        _metadata(),
    )
    assert report.summary.startswith("Configuration overview:")
    assert "0 package(s)" in report.summary
    assert "1 entities" in report.summary
    summary = _section(report, "Summary")
    assert summary.severity is Severity.INFO
    assert "Entities: 1" in summary.items
    statistics = _section(report, "Statistics")
    assert statistics.items == tuple(sorted(statistics.items))
    assert report.recommendations == (
        "Consider organising configuration into packages for maintainability.",
    )


def test_package_without_automations_recommendation() -> None:
    report = ConfigurationReportGenerator().generate(
        HomeAssistantModel(),
        YamlRepository(packages=(_package("core"),)),
        _metadata(),
    )
    assert report.recommendations == ("No automations were found in analysed packages.",)


def test_automations_without_helpers_recommendation() -> None:
    package = _package("core")
    report = ConfigurationReportGenerator().generate(
        HomeAssistantModel(),
        YamlRepository(
            packages=(package,),
            automations=(Automation(package=package, id="boot"),),
        ),
        _metadata(),
    )
    assert "No helpers were found alongside analysed automations." in report.recommendations


def test_generator_is_stateless_deterministic_and_preserves_metadata() -> None:
    generator = ConfigurationReportGenerator()
    model = HomeAssistantModel(entities=(_entity("light.b"), _entity("light.a")))
    repository = YamlRepository(packages=(_package("zeta"), _package("alpha")))
    metadata = _metadata()
    first = generator.generate(model, repository, metadata)
    second = generator.generate(model, repository, metadata)
    assert first == second
    assert first.metadata is metadata
    inventory = _section(first, "Configuration Inventory")
    packages = tuple(item for item in inventory.items if item.startswith("Package:"))
    assert packages == ("Package: alpha", "Package: zeta")
