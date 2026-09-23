"""Central read-only Home Assistant registry model.

Holds parsed registry objects and provides O(1) lookups.
Performs no parsing, analysis or relationship assembly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .models import Area, ConfigEntry, Device, Entity, Floor, Label


@dataclass(slots=True, frozen=True)
class HomeAssistantModel:
    """Immutable aggregate of Home Assistant registry metadata.

    Accepts only already-parsed registry objects. Lookups return
    ``None`` when an identifier is unknown — never raise.
    """

    entities: tuple[Entity, ...] = ()
    devices: tuple[Device, ...] = ()
    areas: tuple[Area, ...] = ()
    labels: tuple[Label, ...] = ()
    floors: tuple[Floor, ...] = ()
    config_entries: tuple[ConfigEntry, ...] = ()

    _entity_index: Mapping[str, Entity] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _device_index: Mapping[str, Device] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _area_index: Mapping[str, Area] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _label_index: Mapping[str, Label] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _floor_index: Mapping[str, Floor] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _config_entry_index: Mapping[str, ConfigEntry] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """Freeze collections and build immutable O(1) lookup indexes."""
        object.__setattr__(self, "entities", tuple(self.entities))
        object.__setattr__(self, "devices", tuple(self.devices))
        object.__setattr__(self, "areas", tuple(self.areas))
        object.__setattr__(self, "labels", tuple(self.labels))
        object.__setattr__(self, "floors", tuple(self.floors))
        object.__setattr__(self, "config_entries", tuple(self.config_entries))
        self._build_indexes()

    def _build_indexes(self) -> None:
        """Populate MappingProxyType indexes for every registry collection."""
        indexes: dict[str, dict[str, object]] = {
            "_entity_index": {e.entity_id: e for e in self.entities},
            "_device_index": {d.registry_id: d for d in self.devices},
            "_area_index": {a.registry_id: a for a in self.areas},
            "_label_index": {label.registry_id: label for label in self.labels},
            "_floor_index": {f.registry_id: f for f in self.floors},
            "_config_entry_index": {
                entry.registry_id: entry for entry in self.config_entries
            },
        }
        for name, mapping in indexes.items():
            object.__setattr__(self, name, MappingProxyType(mapping))

    def get_entity(self, entity_id: str) -> Entity | None:
        """Return the entity with the given ``entity_id``, if present."""
        return self._entity_index.get(entity_id)

    def get_device(self, device_id: str) -> Device | None:
        """Return the device with the given device id, if present."""
        return self._device_index.get(device_id)

    def get_area(self, area_id: str) -> Area | None:
        """Return the area with the given area id, if present."""
        return self._area_index.get(area_id)

    def get_label(self, label_id: str) -> Label | None:
        """Return the label with the given label id, if present."""
        return self._label_index.get(label_id)

    def get_floor(self, floor_id: str) -> Floor | None:
        """Return the floor with the given floor id, if present."""
        return self._floor_index.get(floor_id)

    def get_config_entry(self, entry_id: str) -> ConfigEntry | None:
        """Return the config entry with the given entry id, if present."""
        return self._config_entry_index.get(entry_id)
