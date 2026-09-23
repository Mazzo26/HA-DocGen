"""Parse PackageStructure scene section into Scene objects.

Reads YAML structure only. Supports list and mapping forms. Performs
no entity, device, automation, script or HomeAssistantModel linking.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from ..packages import Package, PackageStructure
from .models import Scene

_SECTION_NAME: Final[str] = "scene"


class SceneParser:
    """Convert a package scene section into Scene objects."""

    def parse(self, structure: PackageStructure) -> tuple[Scene, ...]:
        """Return every scene in *structure* as an immutable tuple."""
        section = structure.get_section(_SECTION_NAME)
        if section is None:
            return ()
        return self._parse_data(section.data, structure.package)

    def _parse_data(
        self,
        data: object,
        package: Package,
    ) -> tuple[Scene, ...]:
        """Dispatch list and mapping scene section shapes."""
        if isinstance(data, list):
            return tuple(
                self._parse_item(item, package)
                for item in data
                if isinstance(item, dict)
            )
        if isinstance(data, dict):
            return tuple(
                self._parse_item(item, package, mapping_key=key)
                for key, item in data.items()
                if isinstance(item, dict)
            )
        return ()

    def _parse_item(
        self,
        raw: Mapping[str, object],
        package: Package,
        mapping_key: object | None = None,
    ) -> Scene:
        """Map one scene mapping to a Scene."""
        explicit_id = _as_optional_str(raw.get("id"))
        return Scene(
            package=package,
            id=explicit_id if explicit_id is not None else _mapping_key_as_id(mapping_key),
            name=_as_optional_str(raw.get("name")),
            icon=_as_optional_str(raw.get("icon")),
            entities=_as_mapping(raw.get("entities")),
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


def _mapping_key_as_id(key: object | None) -> str | None:
    """Return the mapping key as scene id when usable."""
    if key is None:
        return None
    if isinstance(key, str):
        return key
    return str(key)


def _as_optional_str(value: object) -> str | None:
    """Return *value* as str, or None when absent or wrong type."""
    return value if isinstance(value, str) else None
