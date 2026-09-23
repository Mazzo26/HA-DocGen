"""Unit tests for all document generators."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import MappingProxyType

from ha_docgen.dashboard import Dashboard
from ha_docgen.document import (
    AutomationDocumentGenerator,
    BulletList,
    ConfigurationDocumentGenerator,
    DashboardDocumentGenerator,
    Document,
    EntityDocumentGenerator,
    PackageDocumentGenerator,
    Paragraph,
    Table,
)
from ha_docgen.document import Section as DocumentSection
from ha_docgen.helper import Helper
from ha_docgen.packages import PackageStructure, Section
from ha_docgen.registries import HomeAssistantModel
from ha_docgen.relationships import (
    ObjectType,
    RelationshipRepository,
)
from ha_docgen.scene import Scene
from ha_docgen.script import Script
from ha_docgen.template import Template
from tests.support.builders import (
    AutomationBuilder,
    EntityBuilder,
    PackageBuilder,
    build_relationship,
    build_sample_home_assistant_model,
    build_sample_yaml_repository,
)
from ha_docgen.yaml import YamlRepository


def test_package_generator_builds_all_sections_and_filters_by_package() -> None:
    package = PackageBuilder("lighting").build()
    other = PackageBuilder("other").build()
    structure = PackageStructure(
        package=package,
        sections=(Section("automation", {}), Section("script", {})),
    )
    automations = (
        AutomationBuilder().with_package(package).with_alias("Lights on").build(),
        AutomationBuilder().with_package(other).with_alias("Ignored").build(),
    )
    scripts = (
        Script(package=package, id="notify", alias=None),
        Script(package=other, id="ignored"),
    )
    scenes = (Scene(package=package, id="relax", name="Relax"),)
    helpers = (Helper(package=package, type="input_boolean", id="guest_mode"),)
    templates = (Template(package=package, kind="state", source="{{ value }}"),)

    document = PackageDocumentGenerator().generate(
        package,
        structure,
        automations,
        scripts,
        scenes,
        helpers,
        templates,
    )

    assert document == Document(
        title="Package: lighting",
        sections=(
            DocumentSection(
                "Overview",
                (Paragraph(f"Name: lighting\nPath: {package.path}"),),
            ),
            DocumentSection("Sections", (BulletList(("automation", "script")),)),
            DocumentSection("Helpers", (BulletList(("guest_mode",)),)),
            DocumentSection("Automations", (BulletList(("Lights on",)),)),
            DocumentSection("Scripts", (BulletList(("notify",)),)),
            DocumentSection("Scenes", (BulletList(("Relax",)),)),
            DocumentSection("Templates", (BulletList(("state",)),)),
        ),
    )


def test_package_generator_empty_collections_produce_empty_lists() -> None:
    package = PackageBuilder().build()
    structure = PackageStructure(package=package, sections=())

    document = PackageDocumentGenerator().generate(
        package,
        structure,
        (),
        (),
        (),
        (),
        (),
    )

    assert all(section.content == (BulletList(()),) for section in document.sections[1:])


def test_entity_generator_formats_available_fields_and_relationships() -> None:
    entity = (
        EntityBuilder("sensor.office_temperature")
        .with_name("Office temperature")
        .with_device_id("device-1")
        .build()
    )
    entity.area_id = "office"
    entity.disabled_by = "integration"
    entity.extra = MappingProxyType({"platform": "mqtt"})
    relationship = build_relationship(
        ObjectType.ENTITY,
        entity.entity_id,
        ObjectType.DEVICE,
        "device-1",
    )

    document = EntityDocumentGenerator().generate(entity, (relationship,))

    assert document.title == "Entity: sensor.office_temperature"
    assert document.sections == (
        DocumentSection(
            "Overview",
            (
                Paragraph(
                    "Entity ID: sensor.office_temperature\n"
                    "Friendly name: Office temperature\n"
                    "Platform: mqtt\n"
                    "Domain: sensor"
                ),
            ),
        ),
        DocumentSection(
            "Registry",
            (
                BulletList(
                    (
                        "unique_id: sensor.office_temperature",
                        "device_id: device-1",
                        "area_id: office",
                        "disabled_by: integration",
                    )
                ),
            ),
        ),
        DocumentSection(
            "Relationships",
            (BulletList(("references → device:device-1",)),),
        ),
    )


def test_entity_generator_handles_absent_optional_data() -> None:
    entity = EntityBuilder("light.bare").with_name(None).with_unique_id("").build()

    document = EntityDocumentGenerator().generate(entity, ())

    assert document.sections[0].content == (Paragraph("Entity ID: light.bare\nDomain: light"),)
    assert document.sections[1].content == (BulletList(()),)
    assert document.sections[2].content == (BulletList(()),)


def test_automation_generator_formats_explicit_raw_types_in_input_order() -> None:
    automation = replace(
        AutomationBuilder()
        .with_id("arrival")
        .with_alias("Arrival")
        .with_mode("single")
        .with_description("Welcome home")
        .build(),
        raw={
            "trigger": [
                {"platform": "state"},
                {"trigger": "time"},
                {"platform": 123},
            ],
            "conditions": {"condition": "state"},
            "action": [
                {"service": "light.turn_on"},
                {"action": "notify.mobile_app"},
            ],
        },
    )
    relationship = build_relationship(
        ObjectType.AUTOMATION,
        "arrival",
        ObjectType.ENTITY,
        "light.hall",
    )

    document = AutomationDocumentGenerator().generate(automation, (relationship,))

    assert document.title == "Automation: Arrival"
    assert document.sections == (
        DocumentSection(
            "Overview",
            (Paragraph("id: arrival\nalias: Arrival\nmode: single\ndescription: Welcome home"),),
        ),
        DocumentSection("Triggers", (BulletList(("state", "time")),)),
        DocumentSection("Conditions", (BulletList(("state",)),)),
        DocumentSection(
            "Actions",
            (BulletList(("light.turn_on", "notify.mobile_app")),),
        ),
        DocumentSection(
            "Relationships",
            (BulletList(("references → entity:light.hall",)),),
        ),
    )


def test_automation_generator_uses_id_fallback_and_empty_sections() -> None:
    automation = AutomationBuilder().with_alias(None).with_id("only-id").build()

    document = AutomationDocumentGenerator().generate(automation, ())

    assert document.title == "Automation: only-id"
    assert document.sections[0].content == (Paragraph("id: only-id"),)
    assert all(section.content == (BulletList(()),) for section in document.sections[1:])


def test_dashboard_generator_formats_metadata_views_and_relationships() -> None:
    dashboard = Dashboard(
        id="main",
        title="Overview",
        mode="yaml",
        path=Path("dashboards/main.yaml"),
        views=(
            MappingProxyType({"title": "Ground floor"}),
            MappingProxyType({"path": "unnamed"}),
        ),
    )
    relationship = build_relationship(
        ObjectType.DASHBOARD,
        "main",
        ObjectType.ENTITY,
        "light.hall",
    )

    document = DashboardDocumentGenerator().generate(dashboard, (relationship,))

    assert document == Document(
        "Dashboard: Overview",
        (
            DocumentSection(
                "Overview",
                (Paragraph(f"id: main\ntitle: Overview\nmode: yaml\npath: {dashboard.path}"),),
            ),
            DocumentSection(
                "Views",
                (BulletList(("Ground floor", "Unnamed view")),),
            ),
            DocumentSection(
                "Relationships",
                (BulletList(("references → entity:light.hall",)),),
            ),
        ),
    )


def test_dashboard_generator_uses_id_fallback_and_handles_empty_values() -> None:
    document = DashboardDocumentGenerator().generate(Dashboard(id="minimal"), ())

    assert document.title == "Dashboard: minimal"
    assert document.sections[0].content == (Paragraph("id: minimal"),)
    assert document.sections[1].content == (BulletList(()),)
    assert document.sections[2].content == (BulletList(()),)


def test_configuration_generator_counts_aggregates_and_relationship_types() -> None:
    model = build_sample_home_assistant_model()
    yaml_repository = build_sample_yaml_repository()
    relationship = build_relationship(
        ObjectType.AUTOMATION,
        "sample_automation",
        ObjectType.ENTITY,
        "light.sample",
    )
    repository = RelationshipRepository((relationship,))

    document = ConfigurationDocumentGenerator().generate(
        model,
        yaml_repository,
        repository,
    )

    assert document.title == "Home Assistant Configuration"
    assert document.sections[1].content == (
        Table(
            ("Type", "Aantal"),
            (
                ("Entities", "1"),
                ("Devices", "0"),
                ("Areas", "0"),
                ("Floors", "0"),
                ("Labels", "0"),
                ("Config Entries", "0"),
            ),
        ),
    )
    assert document.sections[2].content[0].rows[:2] == (
        ("Packages", "1"),
        ("Automations", "1"),
    )
    assert ("references", "1") in document.sections[3].content[0].rows
    assert document.sections[4].content == (
        BulletList(
            (
                "Total registry objects: 1",
                "Total YAML objects: 2",
                "Total relationships: 1",
            )
        ),
    )


def test_configuration_generator_empty_behavior_is_fully_zeroed() -> None:
    document = ConfigurationDocumentGenerator().generate(
        HomeAssistantModel(),
        YamlRepository(),
        RelationshipRepository(),
    )

    assert all(row[1] == "0" for row in document.sections[1].content[0].rows)
    assert all(row[1] == "0" for row in document.sections[2].content[0].rows)
    assert all(row[1] == "0" for row in document.sections[3].content[0].rows)
    assert document.sections[4].content == (
        BulletList(
            (
                "Total registry objects: 0",
                "Total YAML objects: 0",
                "Total relationships: 0",
            )
        ),
    )


def test_document_generators_are_stateless_and_repeatable() -> None:
    generators = (
        PackageDocumentGenerator(),
        EntityDocumentGenerator(),
        AutomationDocumentGenerator(),
        DashboardDocumentGenerator(),
        ConfigurationDocumentGenerator(),
    )

    assert all(vars(generator) == {} for generator in generators)
