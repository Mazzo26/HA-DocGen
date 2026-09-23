"""Parse a YamlDocument into an immutable Blueprint.

Reads blueprint metadata only. Inputs remain opaque mappings with no
selector, automation, template or relationship interpretation.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from ..yaml import YamlDocument
from .models import Blueprint


class BlueprintParser:
    """Convert one YAML blueprint document into a Blueprint."""

    def parse(self, document: YamlDocument) -> Blueprint:
        """Return an immutable Blueprint from *document*."""
        data = document.data
        if not isinstance(data, dict):
            return Blueprint(path=document.path)
        meta = data.get("blueprint")
        if not isinstance(meta, dict):
            return Blueprint(path=document.path, raw=_freeze_mapping(data))
        return Blueprint(
            name=_as_optional_str(meta.get("name")),
            description=_as_optional_str(meta.get("description")),
            domain=_as_optional_str(meta.get("domain")),
            source_url=_as_optional_str(meta.get("source_url")),
            path=document.path,
            input=_as_input(meta.get("input")),
            raw=_freeze_mapping(data),
        )


def _freeze_mapping(raw: Mapping[str, object]) -> Mapping[str, object]:
    """Return a read-only copy of the complete original mapping."""
    if not raw:
        return MappingProxyType({})
    return MappingProxyType(dict(raw))


def _as_input(value: object) -> Mapping[str, object]:
    """Return raw blueprint inputs as an immutable mapping."""
    if not isinstance(value, dict):
        return MappingProxyType({})
    return _freeze_mapping(value)


def _as_optional_str(value: object) -> str | None:
    """Return *value* as str, or None when absent or wrong type."""
    return value if isinstance(value, str) else None
