"""Pure parser for Home Assistant ``core.floor_registry``.

Reads one registry file and maps JSON entries to Floor objects.
Performs no filesystem discovery and no relationship analysis.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Final

from ..constants import DEFAULT_ENCODING
from .models import Floor

# JSON keys mapped onto first-class Floor attributes (not stored in extra).
_CONSUMED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "floor_id",
        "name",
        "level",
        "icon",
        "created_at",
        "modified_at",
    }
)


class FloorRegistryParser:
    """Parse ``core.floor_registry`` JSON into Floor objects."""

    def parse(self, path: Path) -> tuple[Floor, ...]:
        """Read *path* and return every floor entry as a Floor."""
        payload = self._read_json(path)
        return self._parse_payload(payload)

    def _read_json(self, path: Path) -> Mapping[str, object]:
        """Load and validate the top-level registry JSON object."""
        with path.open("r", encoding=DEFAULT_ENCODING) as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"Floor registry root must be an object: {path}")  # noqa: TRY004
        return payload

    def _parse_payload(self, payload: Mapping[str, object]) -> tuple[Floor, ...]:
        """Extract and parse the floors list from a registry payload."""
        data = payload.get("data")
        if not isinstance(data, dict):
            return ()
        floors = data.get("floors")
        if not isinstance(floors, list):
            return ()
        return tuple(
            self._parse_floor(item) for item in floors if isinstance(item, dict)
        )

    def _parse_floor(self, raw: Mapping[str, object]) -> Floor:
        """Map one registry JSON object to a Floor."""
        return Floor(
            **_identity_fields(raw),
            **_display_fields(raw),
            **_lifecycle_fields(raw),
            extra=_build_extra(raw),
        )


def _identity_fields(raw: Mapping[str, object]) -> dict[str, str]:
    """Return identity keyword arguments for Floor."""
    return {
        "registry_id": _as_str(raw.get("floor_id")),
        "name": _as_str(raw.get("name")),
    }


def _display_fields(raw: Mapping[str, object]) -> dict[str, int | str | None]:
    """Return display keyword arguments for Floor."""
    return {
        "level": _as_optional_int(raw.get("level")),
        "icon": _as_optional_str(raw.get("icon")),
    }


def _lifecycle_fields(raw: Mapping[str, object]) -> dict[str, str | None]:
    """Return lifecycle keyword arguments for Floor."""
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


def _as_optional_int(value: object) -> int | None:
    """Return *value* as int, or None when absent or wrong type."""
    return value if isinstance(value, int) and not isinstance(value, bool) else None
