"""ESPHome domain models.

Pure data only. No YAML loading, file discovery, relationship
discovery or reporting.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ESPHomeSensor:
    """One ESPHome sensor.

    ``identity`` is the relationship endpoint. ``id`` and ``name`` are
    the ESPHome values when present. ``platform`` is the nearest
    platform string.
    """

    identity: str
    platform: str | None = None
    id: str | None = None
    name: str | None = None


@dataclass(frozen=True, slots=True)
class ESPHomeBinarySensor:
    """One ESPHome binary sensor.

    ``identity`` is the relationship endpoint. ``id`` and ``name`` are
    the ESPHome values when present. ``platform`` is the nearest
    platform string.
    """

    identity: str
    platform: str | None = None
    id: str | None = None
    name: str | None = None


@dataclass(frozen=True, slots=True)
class ESPHomeSwitch:
    """One ESPHome switch.

    ``identity`` is the relationship endpoint. ``id`` and ``name`` are
    the ESPHome values when present. ``platform`` is the nearest
    platform string.
    """

    identity: str
    platform: str | None = None
    id: str | None = None
    name: str | None = None


@dataclass(frozen=True, slots=True)
class ESPHomeDevice:
    """One ESPHome device and its sensor, binary sensor and switch components.

    Holds domain values only. YAML mappings are not retained.
    ``name`` is the ``esphome.name`` value. Components are stored in
    the order supplied by the caller.
    """

    name: str | None = None
    friendly_name: str | None = None
    path: Path | None = None
    sensors: tuple[ESPHomeSensor, ...] = ()
    binary_sensors: tuple[ESPHomeBinarySensor, ...] = ()
    switches: tuple[ESPHomeSwitch, ...] = ()
