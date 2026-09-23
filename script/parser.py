"""Parse PackageStructure script section into Script objects.

Reads YAML structure only. Supports the standard Home Assistant
mapping form. Performs no entity, automation, device or
HomeAssistantModel linking.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from ..packages import Package, PackageStructure
from .models import Script

_SECTION_NAME: Final[str] = "script"


class ScriptParser:
    """Convert a package script section into Script objects."""

    def parse(self, structure: PackageStructure) -> tuple[Script, ...]:
        """Return every script in *structure* as an immutable tuple."""
        section = structure.get_section(_SECTION_NAME)
        if section is None:
            return ()
        return self._parse_data(section.data, structure.package)

    def _parse_data(
        self,
        data: object,
        package: Package,
    ) -> tuple[Script, ...]:
        """Parse the standard HA mapping form of a script section."""
        if not isinstance(data, dict):
            return ()
        return tuple(
            self._parse_item(key, item, package)
            for key, item in data.items()
            if isinstance(item, dict)
        )

    def _parse_item(
        self,
        mapping_key: object,
        raw: Mapping[str, object],
        package: Package,
    ) -> Script:
        """Map one named script mapping to a Script."""
        explicit_id = _as_optional_str(raw.get("id"))
        return Script(
            package=package,
            id=explicit_id if explicit_id is not None else _mapping_key_as_id(mapping_key),
            alias=_as_optional_str(raw.get("alias")),
            description=_as_optional_str(raw.get("description")),
            icon=_as_optional_str(raw.get("icon")),
            mode=_as_optional_str(raw.get("mode")),
            sequence=raw["sequence"] if "sequence" in raw else (),
            fields=_as_mapping(raw.get("fields")),
            variables=_as_mapping(raw.get("variables")),
            raw=_freeze_mapping(raw),
        )


def _freeze_mapping(raw: Mapping[str, object]) -> Mapping[str, object]:
    """Return a read-only copy of the complete original mapping."""
    if not raw:
        return MappingProxyType({})
    return MappingProxyType(dict(raw))


def _as_mapping(value: object) -> Mapping[str, object]:
    """Return *value* as an immutable mapping, or empty when unsuitable."""
    if isinstance(value, dict):
        return MappingProxyType(value)
    return MappingProxyType({})


def _mapping_key_as_id(key: object) -> str | None:
    """Return the mapping key as script id when usable."""
    if isinstance(key, str):
        return key
    if key is None:
        return None
    return str(key)


def _as_optional_str(value: object) -> str | None:
    """Return *value* as str, or None when absent or wrong type."""
    return value if isinstance(value, str) else None
