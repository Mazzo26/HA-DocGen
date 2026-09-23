"""Collect template strings from a PackageStructure into Template objects.

Walks package section YAML recursively and records strings under known
template field names. Performs no Jinja parsing, validation, entity
extraction, or relationship analysis.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Final

from ..packages import Package, PackageStructure, Section
from .models import Template

# Field name → Template.kind. Mapping-valued fields yield one Template
# per string value; scalar fields yield one Template for a string value.
_FIELD_KINDS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "state": "state",
        "state_template": "state",
        "value_template": "value",
        "availability": "availability",
        "availability_template": "availability",
        "icon": "icon",
        "icon_template": "icon",
        "name": "name",
        "name_template": "name",
        "attribute_templates": "attribute",
        "trigger_variables": "trigger",
        "variables": "variables",
    }
)

_MAPPING_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "attribute_templates",
        "trigger_variables",
        "variables",
    }
)


class TemplateParser:
    """Collect templates from package YAML without interpreting them."""

    def __init__(self) -> None:
        self._unknown_fields: set[str] = set()

    @property
    def unknown_fields(self) -> frozenset[str]:
        """Return field names ending in ``_template`` that are not known."""
        return frozenset(self._unknown_fields)

    def parse(self, structure: PackageStructure) -> tuple[Template, ...]:
        """Return every template string found in *structure*."""
        self._unknown_fields.clear()
        package = structure.package
        path = package.path
        found: list[Template] = []
        for section in structure.sections:
            found.extend(self._collect_section(section, package, path))
        return tuple(found)

    def _collect_section(
        self,
        section: Section,
        package: Package,
        path: Path,
    ) -> list[Template]:
        """Collect templates from one section's YAML data."""
        found: list[Template] = []
        self._walk(section.data, package, path, found)
        return found

    def _walk(
        self,
        node: object,
        package: Package,
        path: Path,
        found: list[Template],
    ) -> None:
        """Recurse through mappings and lists; collect known template fields."""
        if isinstance(node, dict):
            self._walk_mapping(node, package, path, found)
            return
        if isinstance(node, list):
            for item in node:
                self._walk(item, package, path, found)

    def _walk_mapping(
        self,
        mapping: Mapping[str, object],
        package: Package,
        path: Path,
        found: list[Template],
    ) -> None:
        """Process one mapping: extract known fields, then recurse values."""
        for key, value in mapping.items():
            field = key if isinstance(key, str) else str(key)
            if field in _FIELD_KINDS:
                found.extend(self._extract(field, value, package, path, mapping))
            elif field.endswith("_template"):
                self._unknown_fields.add(field)
            self._walk(value, package, path, found)

    def _extract(
        self,
        field: str,
        value: object,
        package: Package,
        path: Path,
        parent: Mapping[str, object],
    ) -> list[Template]:
        """Build Template objects for *field* without interpreting Jinja."""
        kind = _FIELD_KINDS[field]
        raw = _freeze_mapping(parent)
        if isinstance(value, str):
            return [
                Template(
                    package=package,
                    kind=kind,
                    source=value,
                    path=path,
                    raw=raw,
                )
            ]
        if field in _MAPPING_FIELDS and isinstance(value, dict):
            return _from_mapping(kind, value, package, path, raw)
        if isinstance(value, list):
            return _from_list(kind, value, package, path, raw)
        return []


def _from_mapping(
    kind: str,
    mapping: Mapping[str, object],
    package: Package,
    path: Path,
    raw: Mapping[str, object],
) -> list[Template]:
    """Return one Template per string value in *mapping*."""
    return [
        Template(package=package, kind=kind, source=item, path=path, raw=raw)
        for item in mapping.values()
        if isinstance(item, str)
    ]


def _from_list(
    kind: str,
    items: list[object],
    package: Package,
    path: Path,
    raw: Mapping[str, object],
) -> list[Template]:
    """Return one Template per string element in *items*."""
    return [
        Template(package=package, kind=kind, source=item, path=path, raw=raw)
        for item in items
        if isinstance(item, str)
    ]


def _freeze_mapping(raw: Mapping[str, object]) -> Mapping[str, object]:
    """Return a read-only shallow copy of *raw*."""
    if not raw:
        return MappingProxyType({})
    return MappingProxyType(dict(raw))
