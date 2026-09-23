"""Parse PackageStructure helper sections into Helper objects.

Reads YAML structure only. Processes supported helper domains from
the package structure and ignores unknown top-level sections.
Performs no entity, automation, script or HomeAssistantModel linking.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from ..packages import Package, PackageStructure, Section
from .models import Helper

# Extensible allow-list: add a domain here to support a new helper type.
SUPPORTED_HELPER_TYPES: Final[frozenset[str]] = frozenset(
    {
        "input_boolean",
        "input_number",
        "input_text",
        "input_select",
        "input_datetime",
        "input_button",
        "counter",
        "timer",
        "schedule",
    }
)


class HelperParser:
    """Convert supported helper sections into Helper objects."""

    def parse(self, structure: PackageStructure) -> tuple[Helper, ...]:
        """Return every helper found in *structure* as an immutable tuple."""
        helpers: list[Helper] = []
        package = structure.package
        for section in structure.sections:
            if section.name not in SUPPORTED_HELPER_TYPES:
                continue
            helpers.extend(self._parse_section(section, package))
        return tuple(helpers)

    def _parse_section(
        self,
        section: Section,
        package: Package,
    ) -> tuple[Helper, ...]:
        """Parse one helper section mapping into Helper objects."""
        data = section.data
        if not isinstance(data, dict):
            return ()
        return tuple(
            self._parse_item(package, section.name, key, item)
            for key, item in data.items()
            if isinstance(item, dict)
        )

    def _parse_item(
        self,
        package: Package,
        helper_type: str,
        mapping_key: object,
        raw: Mapping[str, object],
    ) -> Helper:
        """Map one named helper mapping to a Helper."""
        return Helper(
            package=package,
            type=helper_type,
            id=_mapping_key_as_id(mapping_key),
            name=_as_optional_str(raw.get("name")),
            icon=_as_optional_str(raw.get("icon")),
            raw=_freeze_mapping(raw),
        )


def _freeze_mapping(raw: Mapping[str, object]) -> Mapping[str, object]:
    """Return a read-only copy of the complete original mapping."""
    if not raw:
        return MappingProxyType({})
    return MappingProxyType(dict(raw))


def _mapping_key_as_id(key: object) -> str:
    """Return the mapping key as a non-empty helper id."""
    if isinstance(key, str):
        return key
    return str(key)


def _as_optional_str(value: object) -> str | None:
    """Return *value* as str, or None when absent or wrong type."""
    return value if isinstance(value, str) else None
