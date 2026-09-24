"""Tests for ESPHome storage on the existing YAML repository."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType

import pytest

from ha_docgen.esphome import ESPHomeDevice
from ha_docgen.yaml import YamlRepository
from tests.support import PackageBuilder

pytestmark = pytest.mark.unit


def test_empty_repository_has_no_esphome_devices() -> None:
    """The default repository exposes an empty immutable ESPHome collection."""
    repository = YamlRepository()

    assert repository.esphome_devices == ()
    assert repository.get_esphome_device("missing") is None
    assert isinstance(repository._esphome_device_index, MappingProxyType)


def test_repository_orders_devices_by_name_and_path() -> None:
    """Device order does not follow caller insertion order."""
    unnamed = ESPHomeDevice(path=Path("esphome/z.yaml"))
    zeta = ESPHomeDevice(name="zeta", path=Path("esphome/a.yaml"))
    alpha = ESPHomeDevice(name="alpha", path=Path("esphome/b.yaml"))
    later_alpha = ESPHomeDevice(name="alpha", path=Path("esphome/c.yaml"))

    repository = YamlRepository(esphome_devices=(unnamed, zeta, later_alpha, alpha))

    assert tuple(device.path for device in repository.esphome_devices) == (
        Path("esphome/b.yaml"),
        Path("esphome/c.yaml"),
        Path("esphome/a.yaml"),
        Path("esphome/z.yaml"),
    )


def test_duplicate_device_name_lookup_uses_the_later_sorted_device() -> None:
    """The index keeps the last device for one name after deterministic sorting."""
    first = ESPHomeDevice(name="node", path=Path("esphome/a.yaml"), friendly_name="First")
    second = ESPHomeDevice(name="node", path=Path("esphome/b.yaml"), friendly_name="Second")

    repository = YamlRepository(esphome_devices=(second, first))

    assert repository.get_esphome_device("node") is second
    assert repository.esphome_devices == (first, second)


def test_device_without_a_name_is_retained_but_not_indexed() -> None:
    """A missing name stays in the collection and cannot be looked up."""
    device = ESPHomeDevice(path=Path("esphome/node.yaml"))

    repository = YamlRepository(esphome_devices=(device,))

    assert repository.esphome_devices == (device,)
    assert repository.get_esphome_device("") is None


def test_repository_freezes_esphome_devices_and_the_index() -> None:
    """Mutable input becomes a tuple and the lookup map rejects mutation."""
    device = ESPHomeDevice(name="node")
    supplied = [device]

    repository = YamlRepository(esphome_devices=supplied)  # type: ignore[arg-type]
    supplied.append(ESPHomeDevice(name="later"))

    assert repository.esphome_devices == (device,)
    with pytest.raises(TypeError):
        repository._esphome_device_index["new"] = device  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        repository.esphome_devices = ()  # type: ignore[misc]


def test_existing_collections_keep_caller_order() -> None:
    """Sorting ESPHome devices does not reorder other repository collections."""
    zeta = PackageBuilder("zeta").build()
    alpha = PackageBuilder("alpha").build()
    device = ESPHomeDevice(name="node")

    repository = YamlRepository(packages=(zeta, alpha), esphome_devices=(device,))

    assert repository.packages == (zeta, alpha)
    assert repository.get_esphome_device("node") is device
