"""Pure parser for Home Assistant ``core.area_registry``.

Reads one registry file and maps JSON entries to Area objects.
Performs no filesystem discovery and no relationship analysis.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Final

from ..constants import DEFAULT_ENCODING
from .models import Area

# JSON keys mapped onto first-class Area attributes (not stored in extra).
_CONSUMED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "name",
        "aliases",
        "labels",
        "picture",
        "created_at",
        "modified_at",
    }
)


class AreaRegistryParser:
    """Parse ``core.area_registry`` JSON into Area objects."""

    def parse(self, path: Path) -> tuple[Area, ...]:
        """Read *path* and return every area entry as an Area."""
        payload = self._read_json(path)
        return self._parse_payload(payload)

    def _read_json(self, path: Path) -> Mapping[str, object]:
        """Load and validate the top-level registry JSON object."""
        with path.open("r", encoding=DEFAULT_ENCODING) as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"Area registry root must be an object: {path}")
        return payload

    def _parse_payload(self, payload: Mapping[str, object]) -> tuple[Area, ...]:
        """Extract and parse the areas list from a registry payload."""
        data = payload.get("data")
        if not isinstance(data, dict):
            return ()
        areas = data.get("areas")
        if not isinstance(areas, list):
            return ()
        return tuple(self._parse_area(item) for item in areas if isinstance(item, dict))

    def _parse_area(self, raw: Mapping[str, object]) -> Area:
        """Map one registry JSON object to an Area."""
        return Area(
            **_identity_fields(raw),
            **_metadata_fields(raw),
            **_lifecycle_fields(raw),
            extra=_build_extra(raw),
        )


def _identity_fields(raw: Mapping[str, object]) -> dict[str, str]:
    """Return identity keyword arguments for Area."""
    return {
        "registry_id": _as_str(raw.get("id")),
        "name": _as_str(raw.get("name")),
    }


def _metadata_fields(raw: Mapping[str, object]) -> dict[str, object]:
    """Return metadata keyword arguments for Area."""
    return {
        "aliases": _as_str_tuple(raw.get("aliases")),
        "labels": _as_str_tuple(raw.get("labels")),
        "picture": _as_optional_str(raw.get("picture")),
    }


def _lifecycle_fields(raw: Mapping[str, object]) -> dict[str, str | None]:
    """Return lifecycle keyword arguments for Area."""
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


def _as_str_tuple(value: object) -> tuple[str, ...]:
    """Normalise a JSON list to a tuple of strings."""
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        return ()
    return tuple(item for item in value if isinstance(item, str))
