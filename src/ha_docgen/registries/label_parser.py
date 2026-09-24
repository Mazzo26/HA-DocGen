"""Pure parser for Home Assistant ``core.label_registry``.

Reads one registry file and maps JSON entries to Label objects.
Performs no filesystem discovery and no relationship analysis.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Final

from ..constants import DEFAULT_ENCODING
from .models import Label

# JSON keys mapped onto first-class Label attributes (not stored in extra).
_CONSUMED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "label_id",
        "name",
        "color",
        "icon",
        "description",
        "created_at",
        "modified_at",
    }
)


class LabelRegistryParser:
    """Parse ``core.label_registry`` JSON into Label objects."""

    def parse(self, path: Path) -> tuple[Label, ...]:
        """Read *path* and return every label entry as a Label."""
        payload = self._read_json(path)
        return self._parse_payload(payload)

    def _read_json(self, path: Path) -> Mapping[str, object]:
        """Load and validate the top-level registry JSON object."""
        with path.open("r", encoding=DEFAULT_ENCODING) as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            raise ValueError(f"Label registry root must be an object: {path}")  # noqa: TRY004
        return payload

    def _parse_payload(self, payload: Mapping[str, object]) -> tuple[Label, ...]:
        """Extract and parse the labels list from a registry payload."""
        data = payload.get("data")
        if not isinstance(data, dict):
            return ()
        labels = data.get("labels")
        if not isinstance(labels, list):
            return ()
        return tuple(
            self._parse_label(item) for item in labels if isinstance(item, dict)
        )

    def _parse_label(self, raw: Mapping[str, object]) -> Label:
        """Map one registry JSON object to a Label."""
        return Label(
            **_identity_fields(raw),
            **_display_fields(raw),
            **_lifecycle_fields(raw),
            extra=_build_extra(raw),
        )


def _identity_fields(raw: Mapping[str, object]) -> dict[str, str]:
    """Return identity keyword arguments for Label."""
    return {
        "registry_id": _as_str(raw.get("label_id")),
        "name": _as_str(raw.get("name")),
    }


def _display_fields(raw: Mapping[str, object]) -> dict[str, str | None]:
    """Return display keyword arguments for Label."""
    return {
        "color": _as_optional_str(raw.get("color")),
        "icon": _as_optional_str(raw.get("icon")),
        "description": _as_optional_str(raw.get("description")),
    }


def _lifecycle_fields(raw: Mapping[str, object]) -> dict[str, str | None]:
    """Return lifecycle keyword arguments for Label."""
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
