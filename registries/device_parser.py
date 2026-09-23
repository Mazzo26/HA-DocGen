"""Pure parser for Home Assistant ``core.device_registry``.

Reads one registry file and maps JSON entries to Device objects.
Performs no filesystem discovery and no relationship analysis.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Final

from ..constants import DEFAULT_ENCODING
from .models import Device

# JSON keys mapped onto first-class Device attributes (not stored in extra).
_CONSUMED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "identifiers",
        "connections",
        "area_id",
        "via_device_id",
        "config_entries",
        "config_entry_id",
        "labels",
        "name",
        "manufacturer",
        "model",
        "model_id",
        "serial_number",
        "hw_version",
        "sw_version",
        "disabled_by",
        "created_at",
        "modified_at",
    }
)


class DeviceRegistryParser:
    """Parse ``core.device_registry`` JSON into Device objects."""

    def parse(self, path: Path) -> tuple[Device, ...]:
        """Read *path* and return every device entry as a Device."""
        payload = self._read_json(path)
        return self._parse_payload(payload)

    def _read_json(self, path: Path) -> Mapping[str, object]:
        """Load and validate the top-level registry JSON object."""
        with path.open("r", encoding=DEFAULT_ENCODING) as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"Device registry root must be an object: {path}")
        return payload

    def _parse_payload(self, payload: Mapping[str, object]) -> tuple[Device, ...]:
        """Extract and parse the devices list from a registry payload."""
        data = payload.get("data")
        if not isinstance(data, dict):
            return ()
        devices = data.get("devices")
        if not isinstance(devices, list):
            return ()
        return tuple(self._parse_device(item) for item in devices if isinstance(item, dict))

    def _parse_device(self, raw: Mapping[str, object]) -> Device:
        """Map one registry JSON object to a Device."""
        return Device(
            **_identity_fields(raw),
            **_relationship_fields(raw),
            **_display_fields(raw),
            **_status_fields(raw),
            **_lifecycle_fields(raw),
            extra=_build_extra(raw),
        )


def _identity_fields(raw: Mapping[str, object]) -> dict[str, object]:
    """Return identity keyword arguments for Device."""
    return {
        "registry_id": _as_str(raw.get("id")),
        "identifiers": _as_pair_tuple(raw.get("identifiers")),
        "connections": _as_pair_tuple(raw.get("connections")),
    }


def _relationship_fields(raw: Mapping[str, object]) -> dict[str, object]:
    """Return relationship keyword arguments for Device."""
    return {
        "area_id": _as_optional_str(raw.get("area_id")),
        "via_device_id": _as_optional_str(raw.get("via_device_id")),
        "config_entries": _config_entries(raw),
        "labels": _as_str_tuple(raw.get("labels")),
    }


def _display_fields(raw: Mapping[str, object]) -> dict[str, str | None]:
    """Return display keyword arguments for Device."""
    return {
        "name": _as_optional_str(raw.get("name")),
        "manufacturer": _as_optional_str(raw.get("manufacturer")),
        "model": _as_optional_str(raw.get("model")),
        "model_id": _as_optional_str(raw.get("model_id")),
        "serial_number": _as_optional_str(raw.get("serial_number")),
        "hw_version": _as_optional_str(raw.get("hw_version")),
        "sw_version": _as_optional_str(raw.get("sw_version")),
    }


def _status_fields(raw: Mapping[str, object]) -> dict[str, str | None]:
    """Return status keyword arguments for Device."""
    return {
        "disabled_by": _as_optional_str(raw.get("disabled_by")),
    }


def _lifecycle_fields(raw: Mapping[str, object]) -> dict[str, str | None]:
    """Return lifecycle keyword arguments for Device."""
    return {
        "created_at": _as_optional_str(raw.get("created_at")),
        "modified_at": _as_optional_str(raw.get("modified_at")),
    }


def _build_extra(raw: Mapping[str, object]) -> Mapping[str, object]:
    """Collect non-first-class registry fields into a read-only mapping."""
    leftover = {key: value for key, value in raw.items() if key not in _CONSUMED_KEYS}
    if not leftover:
        return MappingProxyType({})
    return MappingProxyType(leftover)


def _config_entries(raw: Mapping[str, object]) -> tuple[str, ...]:
    """Normalise config entry IDs from list or singular storage formats."""
    entries = raw.get("config_entries")
    if isinstance(entries, Sequence) and not isinstance(entries, str | bytes):
        return tuple(item for item in entries if isinstance(item, str))
    # Current HA storage often exposes a single config_entry_id instead.
    entry_id = raw.get("config_entry_id")
    if isinstance(entry_id, str):
        return (entry_id,)
    return ()


def _as_str(value: object, default: str = "") -> str:
    """Return *value* as str, or *default* when the type does not match."""
    return value if isinstance(value, str) else default


def _as_optional_str(value: object) -> str | None:
    """Return *value* as str, or None when absent or wrong type."""
    return value if isinstance(value, str) else None


def _as_str_tuple(value: object) -> tuple[str, ...]:
    """Normalise a JSON list to a tuple of strings."""
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    return tuple(item for item in value if isinstance(item, str))


def _as_pair_tuple(value: object) -> tuple[tuple[str, ...], ...]:
    """Normalise identifier/connection pairs to immutable string tuples."""
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    pairs: list[tuple[str, ...]] = []
    for item in value:
        if not isinstance(item, Sequence) or isinstance(item, str | bytes):
            continue
        pair = tuple(part for part in item if isinstance(part, str))
        if pair:
            pairs.append(pair)
    return tuple(pairs)
