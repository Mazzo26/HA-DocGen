"""Unit tests for all relationship analyzers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

from ha_docgen.dashboard import Dashboard
from ha_docgen.helper import Helper
from ha_docgen.packages import PackageStructure, Section
from ha_docgen.registries import Device, HomeAssistantModel
from ha_docgen.relationships import (
    AutomationRelationshipAnalyzer,
    DashboardRelationshipAnalyzer,
    DeviceRelationshipAnalyzer,
    EntityRelationshipAnalyzer,
    MQTTRelationshipAnalyzer,
    ObjectType,
    RelationshipType,
    ScriptRelationshipAnalyzer,
)
from ha_docgen.script import Script
from tests.support.builders import (
    AutomationBuilder,
    EntityBuilder,
    PackageBuilder,
    build_relationship,
)


def test_entity_analyzer_emits_only_explicit_registry_relationships() -> None:
    entity = EntityBuilder("light.desk").with_device_id("device-1").build()
    entity.area_id = "office"
    entity.config_entry_id = "hue"
    entity.labels = ("lighting", "upstairs")
    model = HomeAssistantModel(entities=(entity,))

    result = EntityRelationshipAnalyzer().analyze(model)

    assert result == (
        build_relationship(
            ObjectType.ENTITY,
            "light.desk",
            ObjectType.DEVICE,
            "device-1",
            RelationshipType.BELONGS_TO,
        ),
        build_relationship(
            ObjectType.ENTITY,
            "light.desk",
            ObjectType.AREA,
            "office",
            RelationshipType.BELONGS_TO,
        ),
        build_relationship(
            ObjectType.ENTITY,
            "light.desk",
            ObjectType.CONFIG_ENTRY,
            "hue",
            RelationshipType.BELONGS_TO,
        ),
        build_relationship(
            ObjectType.ENTITY,
            "light.desk",
            ObjectType.LABEL,
            "lighting",
            RelationshipType.BELONGS_TO,
        ),
        build_relationship(
            ObjectType.ENTITY,
            "light.desk",
            ObjectType.LABEL,
            "upstairs",
            RelationshipType.BELONGS_TO,
        ),
    )


def test_entity_analyzer_returns_empty_for_unlinked_entities() -> None:
    model = HomeAssistantModel(entities=(EntityBuilder().build(),))

    assert EntityRelationshipAnalyzer().analyze(model) == ()


def test_device_analyzer_emits_area_entries_and_labels_without_derived_links() -> None:
    device = Device(
        registry_id="device-1",
        area_id="office",
        config_entries=("z-wave", "matter"),
        labels=("critical",),
    )
    model = HomeAssistantModel(devices=(device,))

    result = DeviceRelationshipAnalyzer().analyze(model)

    assert tuple((item.target_type, item.target_id) for item in result) == (
        (ObjectType.AREA, "office"),
        (ObjectType.CONFIG_ENTRY, "z-wave"),
        (ObjectType.CONFIG_ENTRY, "matter"),
        (ObjectType.LABEL, "critical"),
    )
    assert all(item.relationship_type is RelationshipType.BELONGS_TO for item in result)


def test_automation_analyzer_recurses_deduplicates_and_sorts() -> None:
    raw = {
        "trigger": {"platform": "state", "entity_id": "binary_sensor.door"},
        "action": [
            {"target": {"entity_id": ["light.desk", "light.desk"]}},
            {"device_id": "device-1", "area_id": "office"},
            {
                "service": "script.turn_on",
                "target": {"entity_id": "script.notify"},
            },
            {
                "action": "scene.turn_on",
                "target": {"entity_id": "scene.relax"},
            },
            {
                "service": "automation.trigger",
                "target": {"entity_id": "automation.follow_up"},
            },
        ],
    }
    before = deepcopy(raw)
    automation = replace(AutomationBuilder().build(), raw=raw)

    result = AutomationRelationshipAnalyzer().analyze((automation,))

    assert raw == before
    assert result == tuple(
        sorted(
            set(result),
            key=lambda item: (
                item.source_id,
                item.relationship_type,
                item.target_type,
                item.target_id,
            ),
        )
    )
    assert {(item.target_type, item.target_id) for item in result} == {
        (ObjectType.ENTITY, "binary_sensor.door"),
        (ObjectType.ENTITY, "light.desk"),
        (ObjectType.DEVICE, "device-1"),
        (ObjectType.AREA, "office"),
        (ObjectType.ENTITY, "script.notify"),
        (ObjectType.ENTITY, "scene.relax"),
        (ObjectType.ENTITY, "automation.follow_up"),
        (ObjectType.SCRIPT, "script.notify"),
        (ObjectType.SCENE, "scene.relax"),
        (ObjectType.AUTOMATION, "automation.follow_up"),
    }


def test_automation_analyzer_uses_alias_and_ignores_implicit_service_targets() -> None:
    automation = replace(
        AutomationBuilder().with_id(None).with_alias("Fallback").build(),
        raw={
            "service": "light.turn_on",
            "target": {"entity_id": "script.not_a_script_call"},
        },
    )

    result = AutomationRelationshipAnalyzer().analyze((automation,))

    assert result == (
        build_relationship(
            ObjectType.AUTOMATION,
            "Fallback",
            ObjectType.ENTITY,
            "script.not_a_script_call",
        ),
    )
    assert AutomationRelationshipAnalyzer().analyze((replace(automation, alias=None),)) == ()


def test_script_analyzer_handles_entity_script_and_scene_references() -> None:
    package = PackageBuilder().build()
    script = Script(
        package=package,
        id="morning",
        raw={
            "sequence": [
                {"entity_id": ["light.desk", "sensor.temperature"]},
                {
                    "service": "script.turn_on",
                    "target": {"entity_id": "script.notify"},
                },
                {
                    "service": "scene.turn_on",
                    "target": {"entity_id": "scene.day"},
                },
            ]
        },
    )

    result = ScriptRelationshipAnalyzer().analyze((script, script))

    assert len(result) == 6
    assert {(item.target_type, item.target_id) for item in result} == {
        (ObjectType.ENTITY, "light.desk"),
        (ObjectType.ENTITY, "sensor.temperature"),
        (ObjectType.ENTITY, "script.notify"),
        (ObjectType.ENTITY, "scene.day"),
        (ObjectType.SCRIPT, "script.notify"),
        (ObjectType.SCENE, "scene.day"),
    }


def test_script_analyzer_empty_behavior_and_alias_fallback() -> None:
    package = PackageBuilder().build()
    aliased = Script(package=package, alias="Fallback", raw={"entity_id": "light.desk"})
    anonymous = Script(package=package, raw={"entity_id": "light.ignored"})

    assert ScriptRelationshipAnalyzer().analyze((aliased,))[0].source_id == "Fallback"
    assert ScriptRelationshipAnalyzer().analyze((anonymous,)) == ()
    assert ScriptRelationshipAnalyzer().analyze(()) == ()


def test_dashboard_analyzer_detects_explicit_nested_ids_only() -> None:
    view = {
        "title": "Main",
        "cards": [
            {"type": "entities", "entities": ["light.desk", "sensor.temp"]},
            {"entity": "light.desk"},
            {"device_id": "device-1"},
            {"type": "button"},
        ],
    }
    dashboard = Dashboard(id="main", views=(view,))

    result = DashboardRelationshipAnalyzer().analyze((dashboard,))

    assert {(item.target_type, item.target_id) for item in result} == {
        (ObjectType.ENTITY, "light.desk"),
        (ObjectType.ENTITY, "sensor.temp"),
        (ObjectType.DEVICE, "device-1"),
    }
    assert len(result) == 3


def test_dashboard_analyzer_uses_title_and_ignores_templates() -> None:
    dashboard = Dashboard(
        title="Overview",
        views=({"entity": "{{ dynamic_entity }}"},),
    )

    assert DashboardRelationshipAnalyzer().analyze((dashboard,)) == ()
    assert DashboardRelationshipAnalyzer().analyze((Dashboard(),)) == ()


def test_mqtt_analyzer_emits_publish_relationships_for_all_source_types() -> None:
    package = PackageBuilder().build()
    publish = {
        "service": "mqtt.publish",
        "data": {"topic": "home/status"},
    }
    automation = replace(AutomationBuilder().build(), raw=publish)
    script = Script(package=package, id="publish", raw=publish)
    helper = Helper(package=package, type="input_button", id="send", raw=publish)

    result = MQTTRelationshipAnalyzer().analyze(
        automations=(automation,),
        scripts=(script,),
        helpers=(helper,),
    )

    assert {(item.source_type, item.source_id) for item in result} == {
        (ObjectType.AUTOMATION, "sample_automation"),
        (ObjectType.SCRIPT, "publish"),
        (ObjectType.HELPER, "send"),
    }
    assert all(item.target_id == "home/status" for item in result)
    assert all(item.relationship_type is RelationshipType.PUBLISHES for item in result)


def test_mqtt_analyzer_subscribes_entities_or_package_and_deduplicates() -> None:
    package = PackageBuilder("climate").build()
    structure = PackageStructure(
        package=package,
        sections=(
            Section(
                name="mqtt",
                data=[
                    {
                        "entity_id": "sensor.room",
                        "state_topic": "room/state",
                        "availability_topic": "room/status",
                    },
                    {"state_topic": "package/state"},
                    {"state_topic": "package/state"},
                ],
            ),
        ),
    )

    result = MQTTRelationshipAnalyzer().analyze(package_structures=(structure,))

    assert {(item.source_type, item.source_id, item.target_id) for item in result} == {
        (ObjectType.ENTITY, "sensor.room", "room/state"),
        (ObjectType.ENTITY, "sensor.room", "room/status"),
        (ObjectType.PACKAGE, "climate", "package/state"),
    }
    assert all(item.relationship_type is RelationshipType.SUBSCRIBES for item in result)


def test_mqtt_analyzer_ignores_missing_sections_non_publish_and_jinja_topics() -> None:
    package = PackageBuilder().build()
    automation = replace(
        AutomationBuilder().build(),
        raw={"service": "light.turn_on", "topic": "ignored"},
    )
    structure = PackageStructure(
        package=package,
        sections=(
            Section(name="mqtt", data={"state_topic": "{{ dynamic_topic }}"}),
            Section(name="automation", data={}),
        ),
    )
    empty_structure = PackageStructure(package=package, sections=())

    analyzer = MQTTRelationshipAnalyzer()
    assert (
        analyzer.analyze(
            automations=(automation,),
            package_structures=(structure, empty_structure),
        )
        == ()
    )


def test_analyzers_are_stateless() -> None:
    analyzers = (
        EntityRelationshipAnalyzer(),
        DeviceRelationshipAnalyzer(),
        AutomationRelationshipAnalyzer(),
        ScriptRelationshipAnalyzer(),
        DashboardRelationshipAnalyzer(),
        MQTTRelationshipAnalyzer(),
    )

    assert all(vars(analyzer) == {} for analyzer in analyzers)
