"""Tests for ESPHome YAML interpretation."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.ha_docgen.esphome import (
    ESPHomeBinarySensor,
    ESPHomeDevice,
    ESPHomeParser,
    ESPHomeSensor,
    ESPHomeSwitch,
)
from tools.ha_docgen.yaml import IncludeDirective, IncludeNode, YamlDocument

pytestmark = pytest.mark.unit


def test_parser_extracts_device_and_nested_components() -> None:
    """Nested platform blocks become typed components with inherited platform."""
    device = ESPHomeParser().parse(_document(_nested_config()))

    assert device == ESPHomeDevice(
        name="kiosk",
        friendly_name="Kiosk",
        path=Path("esphome/kiosk.yaml"),
        sensors=(
            ESPHomeSensor(
                identity="kiosk:Moving Distance",
                platform="ld2410",
                name="Moving Distance",
            ),
        ),
        binary_sensors=(
            ESPHomeBinarySensor(
                identity="kiosk:presence",
                platform="ld2410",
                id="presence",
                name="Presence",
            ),
        ),
        switches=(ESPHomeSwitch(identity="kiosk:relay", platform="gpio", id="relay"),),
    )


def test_parser_orders_components_independent_of_yaml_order() -> None:
    """The same components compare equal when their YAML order differs."""
    reverse = {
        "esphome": {"name": "node"},
        "sensor": [
            {"platform": "dht", "id": "zeta", "name": "Zeta"},
            {"platform": "dht", "id": "alpha", "name": "Alpha"},
        ],
    }
    forward = {
        "esphome": {"name": "node"},
        "sensor": [
            {"platform": "dht", "id": "alpha", "name": "Alpha"},
            {"platform": "dht", "id": "zeta", "name": "Zeta"},
        ],
    }

    assert ESPHomeParser().parse(_document(reverse)) == ESPHomeParser().parse(_document(forward))
    identities = tuple(
        sensor.identity for sensor in ESPHomeParser().parse(_document(reverse)).sensors
    )
    assert identities == ("node:alpha", "node:zeta")


def test_duplicate_component_identity_collapses_deterministically() -> None:
    """One identity remains, chosen by the stable component sort key."""
    data = {
        "esphome": {"name": "node"},
        "sensor": [
            {"platform": "b", "id": "temp", "name": "Beta"},
            {"platform": "a", "id": "temp", "name": "Alpha"},
        ],
    }

    device = ESPHomeParser().parse(_document(data))

    assert device.sensors == (
        ESPHomeSensor(identity="node:temp", platform="a", id="temp", name="Alpha"),
    )


def test_parser_skips_includes_substitutions_and_unrelated_keys() -> None:
    """Include nodes stay unloaded and other top-level keys are ignored."""
    data = {
        "esphome": {"name": "${device_name}", "friendly_name": "Room"},
        "wifi": {"ssid": "secret"},
        "sensor": IncludeNode(IncludeDirective.INCLUDE, "sensors.yaml"),
        "switch": [{"platform": "gpio", "name": "Lamp"}],
    }

    device = ESPHomeParser().parse(_document(data))

    assert device.name == "${device_name}"
    assert device.sensors == ()
    assert device.switches == (
        ESPHomeSwitch(identity="${device_name}:Lamp", platform="gpio", name="Lamp"),
    )


def test_non_mapping_document_keeps_only_the_path() -> None:
    """A document that is not a mapping yields an empty device."""
    document = YamlDocument(Path("esphome/empty.yaml"), "", ["not", "a", "mapping"])

    assert ESPHomeParser().parse(document) == ESPHomeDevice(path=Path("esphome/empty.yaml"))


def test_missing_device_name_uses_the_component_key() -> None:
    """Components remain addressable when the device name is absent."""
    data = {"sensor": [{"id": "temp", "name": "Temperature"}]}

    device = ESPHomeParser().parse(_document(data))

    assert device.name is None
    assert device.sensors == (
        ESPHomeSensor(identity="temp", id="temp", name="Temperature"),
    )


def _document(data: object) -> YamlDocument:
    """Return an in-memory document that was not read from disk."""
    return YamlDocument(Path("esphome/kiosk.yaml"), "", data)


def _nested_config() -> dict[str, object]:
    """Return one document with nested sensor and binary sensor blocks."""
    return {
        "esphome": {"name": "kiosk", "friendly_name": "Kiosk"},
        "esp32": {"board": "esp32-c3"},
        "sensor": [{"platform": "ld2410", "moving_distance": {"name": "Moving Distance"}}],
        "binary_sensor": [
            {"platform": "ld2410", "id": "presence", "name": "Presence"},
        ],
        "switch": [{"platform": "gpio", "id": "relay"}],
    }
