"""Scene data models.

Pure data only — no YAML interpretation beyond field extraction,
and no relationship analysis.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from ..packages.models import Package

_EMPTY_MAPPING: Mapping[str, object] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class Scene:
    """Immutable representation of one Home Assistant scene.

    Holds first-class YAML fields only. ``package`` is the source
    package provenance. Unknown keys remain solely in ``raw``, which
    also retains the complete original mapping. Entity states and
    attributes stay opaque YAML values with no validation or semantic
    interpretation.
    """

    package: Package
    id: str | None = None
    name: str | None = None
    icon: str | None = None
    entities: Mapping[str, object] = field(default=_EMPTY_MAPPING)
    raw: Mapping[str, object] = field(default=_EMPTY_MAPPING, repr=False)
