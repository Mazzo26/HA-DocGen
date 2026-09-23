"""Tests for ESPHome integration through AnalysisModel."""

from __future__ import annotations

from pathlib import Path

import pytest

from ha_docgen.analysis import AnalysisModel
from ha_docgen.esphome import ESPHomeParser, ESPHomeSensor
from ha_docgen.relationships import (
    ObjectType,
    Relationship,
    RelationshipRepository,
    RelationshipType,
)
from ha_docgen.yaml import YamlDocument, YamlRepository

pytestmark = pytest.mark.unit


def test_analysis_model_reaches_parsed_devices_by_reference() -> None:
    """ESPHome stays on the existing YAML aggregate inside AnalysisModel."""
    device = ESPHomeParser().parse(_document())
    repository = YamlRepository(esphome_devices=(device,))
    analysis = AnalysisModel(yaml_repository=repository)

    assert analysis.yaml_repository is repository
    assert analysis.yaml_repository.get_esphome_device("node") is device
    assert analysis.yaml_repository.esphome_devices[0].sensors[0] is device.sensors[0]


def test_relationships_address_device_component_and_entity() -> None:
    """Existing relationship storage accepts ESPHome endpoint kinds."""
    device = ESPHomeParser().parse(_document())
    sensor = device.sensors[0]
    contains = _contains(device.name or "", sensor.identity)
    references = _references(sensor.identity, "sensor.node_temperature")
    relationships = RelationshipRepository((references, contains))
    analysis = AnalysisModel(
        yaml_repository=YamlRepository(esphome_devices=(device,)),
        relationship_repository=relationships,
    )

    stored = analysis.relationship_repository
    assert stored.by_source(ObjectType.ESPHOME_DEVICE, "node") == (contains,)
    assert stored.by_target(ObjectType.ESPHOME_SENSOR, sensor.identity) == (contains,)
    assert stored.by_source(ObjectType.ESPHOME_SENSOR, sensor.identity) == (references,)
    assert stored.by_target(ObjectType.ENTITY, "sensor.node_temperature") == (references,)


def test_default_analysis_model_has_no_esphome_devices() -> None:
    """An empty analysis still compares equal and exposes no ESPHome device."""
    first = AnalysisModel()
    second = AnalysisModel()

    assert first == second
    assert first.yaml_repository.esphome_devices == ()
    assert first.yaml_repository.get_esphome_device("node") is None
    assert first.relationship_repository.by_source(ObjectType.ESPHOME_SWITCH, "node:relay") == ()


def _document() -> YamlDocument:
    """Return one in-memory ESPHome document."""
    data = {
        "esphome": {"name": "node", "friendly_name": "Node"},
        "sensor": [{"platform": "dht", "id": "temp", "name": "Temperature"}],
    }
    return YamlDocument(Path("esphome/node.yaml"), "", data)


def _contains(device_name: str, sensor_identity: str) -> Relationship:
    """Return one device-contains-sensor relationship."""
    return Relationship(
        source_type=ObjectType.ESPHOME_DEVICE,
        source_id=device_name,
        target_type=ObjectType.ESPHOME_SENSOR,
        target_id=sensor_identity,
        relationship_type=RelationshipType.CONTAINS,
    )


def _references(sensor_identity: str, entity_id: str) -> Relationship:
    """Return one sensor-references-entity relationship."""
    return Relationship(
        source_type=ObjectType.ESPHOME_SENSOR,
        source_id=sensor_identity,
        target_type=ObjectType.ENTITY,
        target_id=entity_id,
        relationship_type=RelationshipType.REFERENCES,
    )


def test_component_identity_matches_the_parsed_sensor() -> None:
    """The relationship target is the sensor identity stored on the device."""
    sensor = ESPHomeParser().parse(_document()).sensors[0]

    assert sensor == ESPHomeSensor(
        identity="node:temp",
        platform="dht",
        id="temp",
        name="Temperature",
    )
