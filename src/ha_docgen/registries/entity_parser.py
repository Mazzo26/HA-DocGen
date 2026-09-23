"""Pure parser for Home Assistant ``core.entity_registry``.

Reads one registry file and maps JSON entries to Entity objects.
Performs no filesystem discovery and no relationship analysis.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Final

from ..constants import DEFAULT_ENCODING
from .models import Entity

# JSON keys mapped onto first-class Entity attributes (not stored in extra).
_CONSUMED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "entity_id",
        "unique_id",
        "device_id",
        "area_id",
        "config_entry_id",
        "config_subentry_id",
        "name",
        "original_name",
        "icon",
        "original_icon",
        "device_class",
        "original_device_class",
        "entity_category",
        "unit_of_measurement",
        "has_entity_name",
        "disabled_by",
        "hidden_by",
        "orphaned_timestamp",
        "labels",
        "aliases",
        "translation_key",
        "created_at",
        "modified_at",
    }
)


class EntityRegistryParser:
    """Parse ``core.entity_registry`` JSON into Entity objects."""

    def parse(self, path: Path) -> tuple[Entity, ...]:
        """Read *path* and return every entity entry as an Entity."""
        payload = self._read_json(path)
        return self._parse_payload(payload)

    def _read_json(self, path: Path) -> Mapping[str, object]:
        """Load and validate the top-level registry JSON object."""
        with path.open("r", encoding=DEFAULT_ENCODING) as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"Entity registry root must be an object: {path}")
        return payload

    def _parse_payload(self, payload: Mapping[str, object]) -> tuple[Entity, ...]:
        """Extract and parse the entities list from a registry payload."""
        data = payload.get("data")
        if not isinstance(data, dict):
            return ()
        entities = data.get("entities")
        if not isinstance(entities, list):
            return ()
        return tuple(self._parse_entity(item) for item in entities if isinstance(item, dict))

    def _parse_entity(self, raw: Mapping[str, object]) -> Entity:
        """Map one registry JSON object to an Entity."""
        return Entity(
            **_identity_fields(raw),
            **_relationship_fields(raw),
            **_display_fields(raw),
            **_visibility_fields(raw),
            **_metadata_fields(raw),
            **_lifecycle_fields(raw),
            extra=_build_extra(raw),
        )


def _identity_fields(raw: Mapping[str, object]) -> dict[str, str]:
    """Return identity keyword arguments for Entity."""
    return {
        "registry_id": _as_str(raw.get("id")),
        "entity_id": _as_str(raw.get("entity_id")),
        "unique_id": _as_str(raw.get("unique_id")),
    }


def _relationship_fields(raw: Mapping[str, object]) -> dict[str, str | None]:
    """Return relationship keyword arguments for Entity."""
    return {
        "device_id": _as_optional_str(raw.get("device_id")),
        "area_id": _as_optional_str(raw.get("area_id")),
        "config_entry_id": _as_optional_str(raw.get("config_entry_id")),
        "config_subentry_id": _as_optional_str(raw.get("config_subentry_id")),
    }


def _display_fields(raw: Mapping[str, object]) -> dict[str, object]:
    """Return display keyword arguments for Entity."""
    return {
        "name": _as_optional_str(raw.get("name")),
        "original_name": _as_optional_str(raw.get("original_name")),
        "icon": _as_optional_str(raw.get("icon")),
        "original_icon": _as_optional_str(raw.get("original_icon")),
        "device_class": _as_optional_str(raw.get("device_class")),
        "original_device_class": _as_optional_str(raw.get("original_device_class")),
        "entity_category": _as_optional_str(raw.get("entity_category")),
        "unit_of_measurement": _as_optional_str(raw.get("unit_of_measurement")),
        "has_entity_name": _as_bool(raw.get("has_entity_name")),
    }


def _visibility_fields(raw: Mapping[str, object]) -> dict[str, object]:
    """Return visibility keyword arguments for Entity."""
    return {
        "disabled_by": _as_optional_str(raw.get("disabled_by")),
        "hidden_by": _as_optional_str(raw.get("hidden_by")),
        "orphaned_timestamp": _as_optional_float(raw.get("orphaned_timestamp")),
    }


def _metadata_fields(raw: Mapping[str, object]) -> dict[str, object]:
    """Return metadata keyword arguments for Entity."""
    return {
        "labels": _as_str_tuple(raw.get("labels")),
        "aliases": _as_str_tuple(raw.get("aliases")),
        "translation_key": _as_optional_str(raw.get("translation_key")),
    }


def _lifecycle_fields(raw: Mapping[str, object]) -> dict[str, str | None]:
    """Return lifecycle keyword arguments for Entity."""
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


def _as_str(value: object, default: str = "") -> str:
    """Return *value* as str, or *default* when the type does not match."""
    return value if isinstance(value, str) else default


def _as_optional_str(value: object) -> str | None:
    """Return *value* as str, or None when absent or wrong type."""
    return value if isinstance(value, str) else None


def _as_bool(value: object, default: bool = False) -> bool:
    """Return *value* as bool, or *default* when the type does not match."""
    return value if isinstance(value, bool) else default


def _as_optional_float(value: object) -> float | None:
    """Return *value* as float, accepting ints; otherwise None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _as_str_tuple(value: object) -> tuple[str, ...]:
    """Normalise a JSON list to a tuple of strings."""
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    return tuple(item for item in value if isinstance(item, str))
