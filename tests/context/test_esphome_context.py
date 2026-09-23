"""Unit tests for ESPHome context projection."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from tools.ha_docgen.analysis import AnalysisModel
from tools.ha_docgen.automation import Automation
from tools.ha_docgen.context import AIContext, ContextGenerator
from tools.ha_docgen.context import esphome_context as esphome_context_module
from tools.ha_docgen.esphome import (
    ESPHomeBinarySensor,
    ESPHomeDevice,
    ESPHomeSensor,
    ESPHomeSwitch,
)
from tools.ha_docgen.prompt import PromptBuilder, PromptType
from tools.ha_docgen.registries.home_assistant_model import HomeAssistantModel
from tools.ha_docgen.registries.models import Entity
from tools.ha_docgen.relationships import (
    ObjectType,
    Relationship,
    RelationshipRepository,
    RelationshipType,
)
from tools.ha_docgen.tests.support import PackageBuilder, build_relationship
from tools.ha_docgen.yaml import YamlRepository


def _entity(entity_id: str) -> Entity:
    return Entity(registry_id=entity_id, entity_id=entity_id, unique_id=entity_id)


def _sensor(
    identity: str,
    *,
    platform: str | None = None,
    name: str | None = None,
    component_id: str | None = None,
) -> ESPHomeSensor:
    return ESPHomeSensor(identity=identity, platform=platform, id=component_id, name=name)


def _device(
    name: str | None,
    *,
    friendly_name: str | None = None,
    path: Path | None = None,
    sensors: tuple[ESPHomeSensor, ...] = (),
    binary_sensors: tuple[ESPHomeBinarySensor, ...] = (),
    switches: tuple[ESPHomeSwitch, ...] = (),
) -> ESPHomeDevice:
    return ESPHomeDevice(
        name=name,
        friendly_name=friendly_name,
        path=path,
        sensors=sensors,
        binary_sensors=binary_sensors,
        switches=switches,
    )


def _edge(
    source_type: ObjectType,
    source_id: str,
    target_type: ObjectType,
    target_id: str,
    relationship_type: RelationshipType = RelationshipType.REFERENCES,
) -> Relationship:
    return build_relationship(
        source_type,
        source_id,
        target_type,
        target_id,
        relationship_type,
    )


def _generate(
    *,
    devices: tuple[ESPHomeDevice, ...] = (),
    entities: tuple[Entity, ...] = (),
    relationships: tuple[Relationship, ...] = (),
    automations: tuple[Automation, ...] = (),
) -> AIContext:
    repository = YamlRepository(esphome_devices=devices, automations=automations)
    return ContextGenerator().generate(
        AnalysisModel(
            home_assistant_model=HomeAssistantModel(entities=entities),
            yaml_repository=repository,
            relationship_repository=RelationshipRepository(relationships),
        )
    )


def test_empty_repository_has_no_esphome_contexts() -> None:
    assert _generate().esphome_contexts == ()


def test_single_device_keeps_the_original_device() -> None:
    device = _device("alpha", friendly_name="Alpha", path=Path("esphome/alpha.yaml"))
    projected = _generate(devices=(device,)).esphome_contexts
    assert len(projected) == 1
    assert projected[0].device is device
    assert projected[0].sensors == ()
    assert projected[0].binary_sensors == ()
    assert projected[0].switches == ()
    assert projected[0].relationships == ()
    with pytest.raises(FrozenInstanceError):
        projected[0].device = device  # type: ignore[misc]


def test_multiple_devices_are_ordered_by_name_then_path() -> None:
    unnamed = ESPHomeDevice(path=Path("esphome/z.yaml"))
    zeta = _device("zeta", path=Path("esphome/a.yaml"))
    alpha_b = _device("alpha", path=Path("esphome/b.yaml"))
    alpha_a = _device("alpha", path=Path("esphome/a.yaml"))
    projected = _generate(devices=(unnamed, zeta, alpha_b, alpha_a)).esphome_contexts
    assert [item.device for item in projected] == [alpha_a, alpha_b, zeta, unnamed]
    assert projected[0].device is alpha_a
    assert projected[1].device is alpha_b


def test_component_overviews_keep_original_objects() -> None:
    second = _sensor("alpha:b", platform="gpio")
    first = _sensor("alpha:a", platform="template")
    binary = ESPHomeBinarySensor(identity="alpha:door", platform="gpio", name="Door")
    switch = ESPHomeSwitch(identity="alpha:relay", platform="gpio", id="relay")
    device = _device(
        "alpha",
        sensors=(second, first),
        binary_sensors=(binary,),
        switches=(switch,),
    )
    projected = _generate(devices=(device,)).esphome_contexts[0]
    assert device.sensors == (second, first)
    assert [item.sensor for item in projected.sensors] == [first, second]
    assert projected.sensors[0].sensor is first
    assert projected.binary_sensors[0].binary_sensor is binary
    assert projected.switches[0].switch is switch


def test_entity_references_resolve_in_both_directions() -> None:
    sensor = _sensor("alpha:temp")
    kitchen = _entity("sensor.kitchen")
    porch = _entity("sensor.porch")
    kitchen_edge = _edge(
        ObjectType.ENTITY,
        "sensor.kitchen",
        ObjectType.ESPHOME_SENSOR,
        "alpha:temp",
    )
    porch_edge = _edge(
        ObjectType.ESPHOME_SENSOR,
        "alpha:temp",
        ObjectType.ENTITY,
        "sensor.porch",
        RelationshipType.USES,
    )
    missing = _edge(
        ObjectType.ESPHOME_SENSOR,
        "alpha:temp",
        ObjectType.ENTITY,
        "sensor.missing",
    )
    projected = _generate(
        devices=(_device("alpha", sensors=(sensor,)),),
        entities=(porch, kitchen),
        relationships=(porch_edge, missing, kitchen_edge),
    ).esphome_contexts[0].sensors[0]
    assert projected.sensor is sensor
    assert projected.referenced_entities == (kitchen, porch)
    assert projected.referenced_entities[0] is kitchen
    assert projected.unresolved_entity_ids == ("sensor.missing",)
    assert projected.relationships == (kitchen_edge, missing, porch_edge)


def test_duplicate_entity_links_collapse_to_one_object() -> None:
    entity = _entity("sensor.temp")
    references = _edge(
        ObjectType.ESPHOME_SENSOR,
        "alpha:temp",
        ObjectType.ENTITY,
        "sensor.temp",
    )
    uses = _edge(
        ObjectType.ESPHOME_SENSOR,
        "alpha:temp",
        ObjectType.ENTITY,
        "sensor.temp",
        RelationshipType.USES,
    )
    projected = _generate(
        devices=(_device("alpha", sensors=(_sensor("alpha:temp"),)),),
        entities=(entity,),
        relationships=(uses, references),
    ).esphome_contexts[0].sensors[0]
    assert projected.referenced_entities == (entity,)
    assert projected.referenced_entities[0] is entity
    assert projected.relationships == (references, uses)


def test_binary_sensor_and_switch_resolve_their_own_entities() -> None:
    binary = ESPHomeBinarySensor(identity="alpha:door")
    switch = ESPHomeSwitch(identity="alpha:relay")
    door = _entity("binary_sensor.door")
    relay = _entity("switch.relay")
    projected = _generate(
        devices=(_device("alpha", binary_sensors=(binary,), switches=(switch,)),),
        entities=(relay, door),
        relationships=(
            _edge(
                ObjectType.ESPHOME_BINARY_SENSOR,
                "alpha:door",
                ObjectType.ENTITY,
                "binary_sensor.door",
            ),
            _edge(ObjectType.ENTITY, "switch.relay", ObjectType.ESPHOME_SWITCH, "alpha:relay"),
        ),
    ).esphome_contexts[0]
    assert projected.binary_sensors[0].binary_sensor is binary
    assert projected.binary_sensors[0].referenced_entities == (door,)
    assert projected.switches[0].referenced_entities == (relay,)
    assert projected.switches[0].referenced_entities[0] is relay
    assert projected.referenced_entities == ()


def test_device_and_component_references_stay_separate() -> None:
    device_entity = _entity("sensor.alpha")
    sensor_entity = _entity("sensor.temp")
    projected = _generate(
        devices=(_device("alpha", sensors=(_sensor("alpha:temp"),)),),
        entities=(sensor_entity, device_entity),
        relationships=(
            _edge(ObjectType.ESPHOME_DEVICE, "alpha", ObjectType.ENTITY, "sensor.alpha"),
            _edge(ObjectType.ESPHOME_SENSOR, "alpha:temp", ObjectType.ENTITY, "sensor.temp"),
        ),
    ).esphome_contexts[0]
    assert projected.referenced_entities == (device_entity,)
    assert projected.sensors[0].referenced_entities == (sensor_entity,)


def test_non_entity_edges_are_not_copied() -> None:
    projected = _generate(
        devices=(_device("alpha", sensors=(_sensor("alpha:temp"),)),),
        relationships=(
            _edge(ObjectType.ESPHOME_SENSOR, "alpha:temp", ObjectType.SCRIPT, "evening"),
        ),
    ).esphome_contexts[0].sensors[0]
    assert projected.relationships == ()
    assert projected.referenced_entities == ()
    assert projected.unresolved_entity_ids == ()


def test_component_name_is_not_matched_to_an_entity_id() -> None:
    entity = _entity("sensor.kitchen")
    projected = _generate(
        devices=(_device("alpha", sensors=(_sensor("alpha:temp", name="sensor.kitchen"),)),),
        entities=(entity,),
    ).esphome_contexts[0].sensors[0]
    assert projected.referenced_entities == ()
    assert projected.unresolved_entity_ids == ()


def test_device_without_a_name_has_no_relationships() -> None:
    device = ESPHomeDevice(friendly_name="Node", path=Path("esphome/node.yaml"))
    entity = _entity("sensor.node")
    projected = _generate(
        devices=(device,),
        entities=(entity,),
        relationships=(
            _edge(ObjectType.ESPHOME_DEVICE, "Node", ObjectType.ENTITY, "sensor.node"),
        ),
    ).esphome_contexts[0]
    assert projected.device is device
    assert projected.relationships == ()
    assert projected.referenced_entities == ()


def test_identity_is_qualified_by_object_type() -> None:
    entity = _entity("switch.temp")
    projected = _generate(
        devices=(
            _device(
                "alpha",
                sensors=(_sensor("alpha:temp"),),
                switches=(ESPHomeSwitch(identity="alpha:temp"),),
            ),
        ),
        entities=(entity,),
        relationships=(
            _edge(ObjectType.ESPHOME_SWITCH, "alpha:temp", ObjectType.ENTITY, "switch.temp"),
        ),
    ).esphome_contexts[0]
    assert projected.sensors[0].referenced_entities == ()
    assert projected.switches[0].referenced_entities == (entity,)


def test_generation_is_idempotent_and_does_not_read_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("filesystem access")

    monkeypatch.setattr("builtins.open", _fail)
    device = _device("alpha", sensors=(_sensor("alpha:temp"),))
    entity = _entity("sensor.temp")
    relationship = _edge(
        ObjectType.ESPHOME_SENSOR,
        "alpha:temp",
        ObjectType.ENTITY,
        "sensor.temp",
    )
    analysis = AnalysisModel(
        home_assistant_model=HomeAssistantModel(entities=(entity,)),
        yaml_repository=YamlRepository(esphome_devices=(device,)),
        relationship_repository=RelationshipRepository((relationship,)),
    )
    devices = analysis.yaml_repository.esphome_devices
    generator = ContextGenerator()
    first = generator.generate(analysis)
    second = generator.generate(analysis)
    assert first == second
    assert first.esphome_contexts[0].device is device
    assert first.esphome_contexts[0].sensors[0].referenced_entities[0] is entity
    assert analysis.yaml_repository.esphome_devices is devices


def test_other_contexts_stay_unchanged() -> None:
    package = PackageBuilder("lighting").build()
    entity = _entity("light.kitchen")
    automation = Automation(package=package, id="evening", alias="Evening")
    relationship = _edge(ObjectType.AUTOMATION, "evening", ObjectType.ENTITY, "light.kitchen")
    registry = HomeAssistantModel(entities=(entity,))
    relationships = RelationshipRepository((relationship,))
    baseline = ContextGenerator().generate(
        AnalysisModel(
            home_assistant_model=registry,
            yaml_repository=YamlRepository(packages=(package,), automations=(automation,)),
            relationship_repository=relationships,
        )
    )
    populated = ContextGenerator().generate(
        AnalysisModel(
            home_assistant_model=registry,
            yaml_repository=YamlRepository(
                packages=(package,),
                automations=(automation,),
                esphome_devices=(_device("alpha"),),
            ),
            relationship_repository=relationships,
        )
    )
    assert populated.metadata == baseline.metadata
    assert populated.sections == baseline.sections
    assert populated.entity_contexts == baseline.entity_contexts
    assert populated.automation_contexts == baseline.automation_contexts
    assert populated.dashboard_contexts == baseline.dashboard_contexts
    assert populated.package_contexts == baseline.package_contexts
    assert [item.device.name for item in populated.esphome_contexts] == ["alpha"]
    assert baseline.esphome_contexts == ()


def test_prompt_builder_does_not_select_esphome_contexts() -> None:
    context = _generate(devices=(_device("alpha", sensors=(_sensor("alpha:temp"),)),))
    contexts = context.esphome_contexts
    for prompt_type in PromptType:
        prompt = PromptBuilder().build(context, prompt_type)
        assert all(section.content is not contexts for section in prompt.sections)
    assert context.esphome_contexts is contexts


def test_projection_does_not_parse_or_discover() -> None:
    source = inspect.getsource(esphome_context_module)
    assert "YamlLoader" not in source
    assert "ESPHomeParser" not in source
    assert "discover_project" not in source
    assert "rglob" not in source
    assert list(inspect.signature(ContextGenerator.generate).parameters) == [
        "self",
        "analysis_model",
    ]
