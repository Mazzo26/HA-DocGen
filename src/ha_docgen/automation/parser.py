"""Parse PackageStructure automation section into Automation objects.

Reads YAML structure only. Supports list and mapping forms. Performs
no entity, device, script or HomeAssistantModel linking.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from ..packages import Package, PackageStructure
from .models import Automation

_SECTION_NAME: Final[str] = "automation"


class AutomationParser:
    """Convert a package automation section into Automation objects."""

    def parse(self, structure: PackageStructure) -> tuple[Automation, ...]:
        """Return every automation in *structure* as an immutable tuple."""
        section = structure.get_section(_SECTION_NAME)
        if section is None:
            return ()
        return self._parse_data(section.data, structure.package)

    def _parse_data(
        self,
        data: object,
        package: Package,
    ) -> tuple[Automation, ...]:
        """Dispatch list and mapping automation section shapes."""
        if isinstance(data, list):
            return tuple(
                self._parse_item(item, package)
                for item in data
                if isinstance(item, dict)
            )
        if isinstance(data, dict):
            return tuple(
                self._parse_item(item, package)
                for item in data.values()
                if isinstance(item, dict)
            )
        return ()

    def _parse_item(
        self,
        raw: Mapping[str, object],
        package: Package,
    ) -> Automation:
        """Map one automation mapping to an Automation."""
        return Automation(
            package=package,
            id=_as_optional_str(raw.get("id")),
            alias=_as_optional_str(raw.get("alias")),
            description=_as_optional_str(raw.get("description")),
            mode=_as_optional_str(raw.get("mode")),
            triggers=_field_or_alias(raw, "triggers", "trigger"),
            conditions=_field_or_alias(raw, "conditions", "condition"),
            actions=_field_or_alias(raw, "actions", "action"),
            raw=_freeze_mapping(raw),
        )


def _field_or_alias(
    raw: Mapping[str, object],
    primary: str,
    alias: str,
) -> object:
    """Return *primary* if present, else *alias*, else an empty tuple."""
    if primary in raw:
        return raw[primary]
    if alias in raw:
        return raw[alias]
    return ()


def _freeze_mapping(raw: Mapping[str, object]) -> Mapping[str, object]:
    """Return a read-only copy of the complete original mapping."""
    if not raw:
        return MappingProxyType({})
    return MappingProxyType(dict(raw))


def _as_optional_str(value: object) -> str | None:
    """Return *value* as str, or None when absent or wrong type."""
    return value if isinstance(value, str) else None
