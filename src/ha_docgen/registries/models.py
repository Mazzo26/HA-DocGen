"""Home Assistant registry data models.

Pure data only — no filesystem access and no JSON parsing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

_EMPTY_EXTRA: Mapping[str, object] = MappingProxyType({})


@dataclass(slots=True)
class Entity:
    """One Home Assistant entity from core.entity_registry.

    Models HA architecture (identity, relationships, display, visibility).
    Opaque registry JSON that is not part of the public API lives in
    ``extra`` when retained by the parser.
    """

    # Identity
    registry_id: str
    entity_id: str
    unique_id: str

    # Relationships
    device_id: str | None = None
    area_id: str | None = None
    config_entry_id: str | None = None
    config_subentry_id: str | None = None

    # Display
    name: str | None = None
    original_name: str | None = None
    icon: str | None = None
    original_icon: str | None = None
    device_class: str | None = None
    original_device_class: str | None = None
    entity_category: str | None = None
    unit_of_measurement: str | None = None
    has_entity_name: bool = False

    # Visibility
    disabled_by: str | None = None
    hidden_by: str | None = None
    orphaned_timestamp: float | None = None

    # Metadata
    labels: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    translation_key: str | None = None

    # Lifecycle
    created_at: str | None = None
    modified_at: str | None = None

    # Opaque leftover registry fields (not first-class API)
    extra: Mapping[str, object] = field(default=_EMPTY_EXTRA, repr=False)

    @property
    def domain(self) -> str:
        """Entity domain derived from ``entity_id`` (segment before the first dot)."""
        return self.entity_id.split(".", 1)[0]


@dataclass(slots=True)
class Device:
    """One Home Assistant device from core.device_registry.

    Models HA architecture (identity, relationships, display, status).
    Opaque registry JSON that is not part of the public API lives in
    ``extra`` when retained by the parser.
    """

    # Identity
    registry_id: str
    identifiers: tuple[tuple[str, ...], ...] = ()
    connections: tuple[tuple[str, ...], ...] = ()

    # Relationships
    area_id: str | None = None
    via_device_id: str | None = None
    config_entries: tuple[str, ...] = ()
    labels: tuple[str, ...] = ()

    # Display
    name: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    model_id: str | None = None
    serial_number: str | None = None
    hw_version: str | None = None
    sw_version: str | None = None

    # Status
    disabled_by: str | None = None

    # Lifecycle
    created_at: str | None = None
    modified_at: str | None = None

    # Opaque leftover registry fields (not first-class API)
    extra: Mapping[str, object] = field(default=_EMPTY_EXTRA, repr=False)


@dataclass(slots=True)
class Area:
    """One Home Assistant area from core.area_registry.

    Models HA architecture (identity, metadata, lifecycle).
    Opaque registry JSON that is not part of the public API lives in
    ``extra`` when retained by the parser.
    """

    # Identity
    registry_id: str
    name: str

    # Metadata
    aliases: tuple[str, ...] = ()
    labels: tuple[str, ...] = ()
    picture: str | None = None

    # Lifecycle
    created_at: str | None = None
    modified_at: str | None = None

    # Opaque leftover registry fields (not first-class API)
    extra: Mapping[str, object] = field(default=_EMPTY_EXTRA, repr=False)


@dataclass(slots=True)
class Label:
    """One Home Assistant label from core.label_registry.

    Models HA architecture (identity, display, lifecycle).
    Opaque registry JSON that is not part of the public API lives in
    ``extra`` when retained by the parser.
    """

    # Identity
    registry_id: str
    name: str

    # Display
    color: str | None = None
    icon: str | None = None
    description: str | None = None

    # Lifecycle
    created_at: str | None = None
    modified_at: str | None = None

    # Opaque leftover registry fields (not first-class API)
    extra: Mapping[str, object] = field(default=_EMPTY_EXTRA, repr=False)


@dataclass(slots=True)
class Floor:
    """One Home Assistant floor from core.floor_registry.

    Models HA architecture (identity, display, lifecycle).
    Opaque registry JSON that is not part of the public API lives in
    ``extra`` when retained by the parser.
    """

    # Identity
    registry_id: str
    name: str

    # Display
    level: int | None = None
    icon: str | None = None

    # Lifecycle
    created_at: str | None = None
    modified_at: str | None = None

    # Opaque leftover registry fields (not first-class API)
    extra: Mapping[str, object] = field(default=_EMPTY_EXTRA, repr=False)


@dataclass(slots=True)
class ConfigEntry:
    """One Home Assistant config entry from core.config_entries.

    Models HA architecture (identity, status, preferences, lifecycle).
    Opaque registry JSON that is not part of the public API lives in
    ``extra`` when retained by the parser.
    """

    # Identity
    registry_id: str
    domain: str
    title: str
    version: int | None = None
    minor_version: int | None = None

    # Status
    disabled_by: str | None = None
    source: str | None = None

    # Preferences
    pref_disable_new_entities: bool | None = None
    pref_disable_polling: bool | None = None

    # Lifecycle
    created_at: str | None = None
    modified_at: str | None = None

    # Opaque leftover registry fields (not first-class API)
    extra: Mapping[str, object] = field(default=_EMPTY_EXTRA, repr=False)
