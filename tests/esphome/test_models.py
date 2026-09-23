"""Tests for immutable ESPHome domain models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from ha_docgen.esphome import (
    ESPHomeBinarySensor,
    ESPHomeDevice,
    ESPHomeSensor,
    ESPHomeSwitch,
)

pytestmark = pytest.mark.unit


def test_device_and_components_are_frozen() -> None:
    """Public ESPHome models reject attribute assignment."""
    device = ESPHomeDevice(name="node")
    sensor = ESPHomeSensor(identity="node:temp")

    with pytest.raises(FrozenInstanceError):
        device.name = "other"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        sensor.name = "Temperature"  # type: ignore[misc]


def test_component_tuples_are_immutable() -> None:
    """Component collections are tuples and reject in-place mutation."""
    device = _device()

    assert isinstance(device.sensors, tuple)
    assert isinstance(device.binary_sensors, tuple)
    assert isinstance(device.switches, tuple)
    with pytest.raises(AttributeError):
        device.sensors.append(ESPHomeSensor(identity="extra"))  # type: ignore[attr-defined]


def test_equal_devices_compare_equal_and_are_hashable() -> None:
    """Equality uses field values, so equal devices collapse in a set."""
    first = _device()
    second = _device()

    assert first == second
    assert {first, second} == {first}


def test_different_component_order_is_not_equal() -> None:
    """Caller-supplied component order is part of the device value."""
    temperature = ESPHomeSensor(identity="node:temp", id="temp")
    humidity = ESPHomeSensor(identity="node:humidity", id="humidity")
    forward = ESPHomeDevice(name="node", sensors=(temperature, humidity))
    reverse = ESPHomeDevice(name="node", sensors=(humidity, temperature))

    assert forward != reverse


def test_models_do_not_keep_a_raw_mapping() -> None:
    """Domain models expose typed fields rather than a YAML dictionary."""
    device = _device()
    sensor = device.sensors[0]

    assert not hasattr(device, "raw")
    assert not hasattr(sensor, "raw")
    assert sensor.platform == "dht"
    assert device.path == Path("esphome/node.yaml")


def _device() -> ESPHomeDevice:
    """Return one device covering sensor, binary sensor and switch."""
    return ESPHomeDevice(
        name="node",
        friendly_name="Node",
        path=Path("esphome/node.yaml"),
        sensors=(ESPHomeSensor(identity="node:temp", platform="dht", id="temp", name="Temp"),),
        binary_sensors=(
            ESPHomeBinarySensor(identity="node:motion", platform="gpio", name="Motion"),
        ),
        switches=(ESPHomeSwitch(identity="node:light", platform="gpio", id="light"),),
    )
