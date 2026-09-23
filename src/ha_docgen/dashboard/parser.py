"""Parse a YamlDocument into an immutable Dashboard.

Reads dashboard metadata only. Views remain opaque mappings with no
card, entity, badge, navigation or template interpretation.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from ..yaml import YamlDocument
from .models import Dashboard


class DashboardParser:
    """Convert one YAML dashboard document into a Dashboard."""

    def parse(self, document: YamlDocument) -> Dashboard:
        """Return an immutable Dashboard from *document*."""
        data = document.data
        if not isinstance(data, dict):
            return Dashboard(path=document.path)
        return Dashboard(
            id=_as_optional_str(data.get("id")),
            title=_as_optional_str(data.get("title")),
            mode=_as_optional_str(data.get("mode")),
            path=document.path,
            views=_as_views(data.get("views")),
            raw=_freeze_mapping(data),
        )


def _freeze_mapping(raw: Mapping[str, object]) -> Mapping[str, object]:
    """Return a read-only copy of the complete original mapping."""
    if not raw:
        return MappingProxyType({})
    return MappingProxyType(dict(raw))


def _as_views(value: object) -> tuple[Mapping[str, object], ...]:
    """Return raw view mappings as an immutable tuple."""
    if not isinstance(value, list):
        return ()
    return tuple(
        MappingProxyType(dict(item)) for item in value if isinstance(item, dict)
    )


def _as_optional_str(value: object) -> str | None:
    """Return *value* as str, or None when absent or wrong type."""
    return value if isinstance(value, str) else None
