"""Script data models.

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
class Script:
    """Immutable representation of one Home Assistant script.

    Holds first-class YAML fields only. ``package`` is the source
    package provenance. Unknown keys remain solely in ``raw``, which
    also retains the complete original mapping. Sequence, fields and
    variables are opaque YAML values with no template, service or
    validation interpretation.
    """

    package: Package
    id: str | None = None
    alias: str | None = None
    description: str | None = None
    icon: str | None = None
    mode: str | None = None
    sequence: object = ()
    fields: Mapping[str, object] = field(default=_EMPTY_MAPPING)
    variables: Mapping[str, object] = field(default=_EMPTY_MAPPING)
    raw: Mapping[str, object] = field(default=_EMPTY_MAPPING, repr=False)
