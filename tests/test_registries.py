"""Unit tests for registry models, parsers and aggregate lookups."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from ha_docgen.registries import (
    Area,
    AreaRegistryParser,
    ConfigEntry,
    ConfigEntryRegistryParser,
    Device,
    DeviceRegistryParser,
    Entity,
    EntityRegistryParser,
    Floor,
    FloorRegistryParser,
    HomeAssistantModel,
    Label,
    LabelRegistryParser,
)

RegistryParser = (
    AreaRegistryParser
    | ConfigEntryRegistryParser
    | DeviceRegistryParser
    | EntityRegistryParser
    | FloorRegistryParser
    | LabelRegistryParser
)


def _write_registry(tmp_path: Path, payload: object) -> Path:
    """Write one registry JSON payload in the isolated test directory."""
    path = tmp_path / "registry"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("model"),
    [
        Area("area", "Kitchen"),
        ConfigEntry("entry", "hue", "Hue"),
        Device("device"),
        Entity("entity", "light.kitchen", "unique"),
        Floor("floor", "Ground"),
        Label("label", "Important"),
    ],
)
def test_registry_models_use_slots_and_value_equality(model: object) -> None:
    """Registry data objects have slot-backed, value-based dataclass semantics."""
    assert model == replace(model)
    assert not hasattr(model, "__dict__")


def test_entity_parser_maps_full_entry_and_safe_defaults(tmp_path: Path) -> None:
    """Entity parsing normalises fields, retains extras and skips non-objects."""
    path = _write_registry(
        tmp_path,
        {
            "data": {
                "entities": [
                    {
                        "id": "registry",
                        "entity_id": "sensor.temperature",
                        "unique_id": "unique",
                        "device_id": "device",
                        "area_id": "kitchen",
                        "config_entry_id": "entry",
                        "config_subentry_id": "subentry",
                        "name": "Temperature",
                        "original_name": "Original",
                        "icon": "mdi:thermometer",
                        "original_icon": "mdi:home",
                        "device_class": "temperature",
                        "original_device_class": "temperature",
                        "entity_category": "diagnostic",
                        "unit_of_measurement": "°C",
                        "has_entity_name": True,
                        "disabled_by": "user",
                        "hidden_by": "integration",
                        "orphaned_timestamp": 12,
                        "labels": ["climate", 3],
                        "aliases": ["Room"],
                        "translation_key": "temperature",
                        "created_at": "created",
                        "modified_at": "modified",
                        "platform": "demo",
                    },
                    "ignored",
                    {"entity_id": 3, "has_entity_name": "yes"},
                ]
            }
        },
    )

    entity, incomplete = EntityRegistryParser().parse(path)

    assert entity == Entity(
        registry_id="registry",
        entity_id="sensor.temperature",
        unique_id="unique",
        device_id="device",
        area_id="kitchen",
        config_entry_id="entry",
        config_subentry_id="subentry",
        name="Temperature",
        original_name="Original",
        icon="mdi:thermometer",
        original_icon="mdi:home",
        device_class="temperature",
        original_device_class="temperature",
        entity_category="diagnostic",
        unit_of_measurement="°C",
        has_entity_name=True,
        disabled_by="user",
        hidden_by="integration",
        orphaned_timestamp=12.0,
        labels=("climate",),
        aliases=("Room",),
        translation_key="temperature",
        created_at="created",
        modified_at="modified",
        extra={"platform": "demo"},
    )
    with pytest.raises(TypeError):
        entity.extra["platform"] = "other"  # type: ignore[index]
    assert incomplete == Entity("", "", "")


@pytest.mark.parametrize(
    ("config_entries", "config_entry_id", "expected"),
    [
        (["first", 3, "second"], None, ("first", "second")),
        (None, "single", ("single",)),
        ("invalid", 3, ()),
    ],
)
def test_device_parser_normalises_config_entry_formats(
    tmp_path: Path,
    config_entries: object,
    config_entry_id: object,
    expected: tuple[str, ...],
) -> None:
    """Device parser supports plural and legacy singular config entry storage."""
    raw = {
        "id": "device",
        "identifiers": [["demo", "one"], "bad", ["partial", 4]],
        "connections": [["mac", "00:00"]],
        "area_id": "kitchen",
        "via_device_id": "bridge",
        "config_entries": config_entries,
        "config_entry_id": config_entry_id,
        "labels": ["important", 4],
        "name": "Lamp",
        "manufacturer": "Example",
        "model": "Model",
        "model_id": "model-id",
        "serial_number": "serial",
        "hw_version": "1",
        "sw_version": "2",
        "disabled_by": "user",
        "created_at": "created",
        "modified_at": "modified",
        "entry_type": "service",
    }
    path = _write_registry(tmp_path, {"data": {"devices": [raw]}})

    (device,) = DeviceRegistryParser().parse(path)

    assert device.registry_id == "device"
    assert device.identifiers == (("demo", "one"), ("partial",))
    assert device.connections == (("mac", "00:00"),)
    assert device.config_entries == expected
    assert device.labels == ("important",)
    assert device.area_id == "kitchen"
    assert device.via_device_id == "bridge"
    assert device.name == "Lamp"
    assert device.extra == {"entry_type": "service"}


@pytest.mark.parametrize(
    ("parser", "collection_key", "raw", "expected"),
    [
        (
            AreaRegistryParser(),
            "areas",
            {
                "id": "kitchen",
                "name": "Kitchen",
                "aliases": ["Cooking", 4],
                "labels": ["downstairs"],
                "picture": "/local/kitchen.png",
                "created_at": "created",
                "modified_at": "modified",
                "floor_id": "ground",
            },
            Area(
                "kitchen",
                "Kitchen",
                aliases=("Cooking",),
                labels=("downstairs",),
                picture="/local/kitchen.png",
                created_at="created",
                modified_at="modified",
                extra={"floor_id": "ground"},
            ),
        ),
        (
            LabelRegistryParser(),
            "labels",
            {
                "label_id": "important",
                "name": "Important",
                "color": "red",
                "icon": "mdi:alert",
                "description": "Priority",
                "created_at": "created",
                "modified_at": "modified",
                "custom": True,
            },
            Label(
                "important",
                "Important",
                color="red",
                icon="mdi:alert",
                description="Priority",
                created_at="created",
                modified_at="modified",
                extra={"custom": True},
            ),
        ),
        (
            FloorRegistryParser(),
            "floors",
            {
                "floor_id": "ground",
                "name": "Ground",
                "level": 0,
                "icon": "mdi:home-floor-0",
                "created_at": "created",
                "modified_at": "modified",
                "aliases": ["Downstairs"],
            },
            Floor(
                "ground",
                "Ground",
                level=0,
                icon="mdi:home-floor-0",
                created_at="created",
                modified_at="modified",
                extra={"aliases": ["Downstairs"]},
            ),
        ),
        (
            ConfigEntryRegistryParser(),
            "entries",
            {
                "entry_id": "entry",
                "domain": "hue",
                "title": "Hue",
                "version": 2,
                "minor_version": 1,
                "disabled_by": "user",
                "source": "user",
                "pref_disable_new_entities": True,
                "pref_disable_polling": False,
                "created_at": "created",
                "modified_at": "modified",
                "data": {"host": "example"},
            },
            ConfigEntry(
                "entry",
                "hue",
                "Hue",
                version=2,
                minor_version=1,
                disabled_by="user",
                source="user",
                pref_disable_new_entities=True,
                pref_disable_polling=False,
                created_at="created",
                modified_at="modified",
                extra={"data": {"host": "example"}},
            ),
        ),
    ],
)
def test_registry_parsers_map_simple_registry_entries(
    tmp_path: Path,
    parser: RegistryParser,
    collection_key: str,
    raw: Mapping[str, object],
    expected: object,
) -> None:
    """Structurally similar parsers map first-class and opaque fields uniformly."""
    path = _write_registry(tmp_path, {"data": {collection_key: [raw, None]}})

    assert parser.parse(path) == (expected,)


@pytest.mark.parametrize(
    ("parser"),
    [
        AreaRegistryParser(),
        ConfigEntryRegistryParser(),
        DeviceRegistryParser(),
        EntityRegistryParser(),
        FloorRegistryParser(),
        LabelRegistryParser(),
    ],
)
@pytest.mark.parametrize("payload", [{}, {"data": None}, {"data": {}}, {"data": []}])
def test_registry_parsers_return_empty_for_missing_collections(
    tmp_path: Path,
    parser: RegistryParser,
    payload: object,
) -> None:
    """Absent or malformed registry collection containers safely yield no models."""
    assert parser.parse(_write_registry(tmp_path, payload)) == ()


@pytest.mark.parametrize(
    ("parser"),
    [
        AreaRegistryParser(),
        ConfigEntryRegistryParser(),
        DeviceRegistryParser(),
        EntityRegistryParser(),
        FloorRegistryParser(),
        LabelRegistryParser(),
    ],
)
def test_registry_parsers_reject_non_object_roots(
    tmp_path: Path,
    parser: RegistryParser,
) -> None:
    """All registry parsers require a JSON object at the document root."""
    with pytest.raises(ValueError, match="root|registry|entries"):
        parser.parse(_write_registry(tmp_path, []))


def test_registry_parsers_surface_invalid_json(tmp_path: Path) -> None:
    """Malformed JSON is not silently converted into an empty registry."""
    path = tmp_path / "registry"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        EntityRegistryParser().parse(path)


def test_home_assistant_model_freezes_collections_and_is_deterministic() -> None:
    """Aggregate construction copies inputs and equal inputs produce equal models."""
    first = Entity("one", "light.one", "unique-one")
    second = Entity("two", "light.two", "unique-two")
    source = [second, first]

    model = HomeAssistantModel(entities=source)  # type: ignore[arg-type]
    equivalent = HomeAssistantModel(entities=(second, first))
    source.reverse()

    assert model.entities == (second, first)
    assert model == equivalent
    with pytest.raises(FrozenInstanceError):
        model.entities = ()  # type: ignore[misc]


def test_home_assistant_model_supports_every_lookup() -> None:
    """Every registry collection has O(1)-style found and missing lookup behaviour."""
    entity = Entity("entity-registry", "light.kitchen", "unique")
    device = Device("device")
    area = Area("area", "Kitchen")
    label = Label("label", "Important")
    floor = Floor("floor", "Ground")
    entry = ConfigEntry("entry", "hue", "Hue")
    model = HomeAssistantModel(
        entities=(entity,),
        devices=(device,),
        areas=(area,),
        labels=(label,),
        floors=(floor,),
        config_entries=(entry,),
    )

    assert model.get_entity("light.kitchen") is entity
    assert model.get_device("device") is device
    assert model.get_area("area") is area
    assert model.get_label("label") is label
    assert model.get_floor("floor") is floor
    assert model.get_config_entry("entry") is entry
    assert model.get_entity("missing") is None
    assert model.get_device("missing") is None
    assert model.get_area("missing") is None
    assert model.get_label("missing") is None
    assert model.get_floor("missing") is None
    assert model.get_config_entry("missing") is None


def test_home_assistant_model_duplicate_lookup_is_deterministic() -> None:
    """Duplicate identifiers consistently resolve to the final supplied object."""
    first = Entity("first", "light.same", "one")
    second = Entity("second", "light.same", "two")

    model = HomeAssistantModel(entities=(first, second))

    assert model.entities == (first, second)
    assert model.get_entity("light.same") is second
