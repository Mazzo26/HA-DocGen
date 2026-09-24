"""Pure parser for Home Assistant ``core.config_entries``.

Reads one registry file and maps JSON entries to ConfigEntry objects.
Performs no filesystem discovery and no relationship analysis.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Final

from ..constants import DEFAULT_ENCODING
from .models import ConfigEntry

# JSON keys mapped onto first-class ConfigEntry attributes (not stored in extra).
_CONSUMED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "entry_id",
        "domain",
        "title",
        "version",
        "minor_version",
        "disabled_by",
        "source",
        "pref_disable_new_entities",
        "pref_disable_polling",
        "created_at",
        "modified_at",
    }
)


class ConfigEntryRegistryParser:
    """Parse ``core.config_entries`` JSON into ConfigEntry objects."""

    def parse(self, path: Path) -> tuple[ConfigEntry, ...]:
        """Read *path* and return every config entry as a ConfigEntry."""
        payload = self._read_json(path)
        return self._parse_payload(payload)

    def _read_json(self, path: Path) -> Mapping[str, object]:
        """Load and validate the top-level registry JSON object."""
        with path.open("r", encoding=DEFAULT_ENCODING) as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"Config entries root must be an object: {path}")  # noqa: TRY004
        return payload

    def _parse_payload(self, payload: Mapping[str, object]) -> tuple[ConfigEntry, ...]:
        """Extract and parse the entries list from a registry payload."""
        data = payload.get("data")
        if not isinstance(data, dict):
            return ()
        entries = data.get("entries")
        if not isinstance(entries, list):
            return ()
        return tuple(
            self._parse_entry(item) for item in entries if isinstance(item, dict)
        )

    def _parse_entry(self, raw: Mapping[str, object]) -> ConfigEntry:
        """Map one registry JSON object to a ConfigEntry."""
        return ConfigEntry(
            **_identity_fields(raw),
            **_status_fields(raw),
            **_preference_fields(raw),
            **_lifecycle_fields(raw),
            extra=_build_extra(raw),
        )


def _identity_fields(raw: Mapping[str, object]) -> dict[str, str | int | None]:
    """Return identity keyword arguments for ConfigEntry."""
    return {
        "registry_id": _as_str(raw.get("entry_id")),
        "domain": _as_str(raw.get("domain")),
        "title": _as_str(raw.get("title")),
        "version": _as_optional_int(raw.get("version")),
        "minor_version": _as_optional_int(raw.get("minor_version")),
    }


def _status_fields(raw: Mapping[str, object]) -> dict[str, str | None]:
    """Return status keyword arguments for ConfigEntry."""
    return {
        "disabled_by": _as_optional_str(raw.get("disabled_by")),
        "source": _as_optional_str(raw.get("source")),
    }


def _preference_fields(raw: Mapping[str, object]) -> dict[str, bool | None]:
    """Return preference keyword arguments for ConfigEntry."""
    return {
        "pref_disable_new_entities": _as_optional_bool(
            raw.get("pref_disable_new_entities")
        ),
        "pref_disable_polling": _as_optional_bool(raw.get("pref_disable_polling")),
    }


def _lifecycle_fields(raw: Mapping[str, object]) -> dict[str, str | None]:
    """Return lifecycle keyword arguments for ConfigEntry."""
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


def _as_optional_bool(value: object) -> bool | None:
    """Return *value* as bool, or None when absent or wrong type."""
    return value if isinstance(value, bool) else None
