"""Helper data models.

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
class Helper:
    """Immutable representation of one Home Assistant helper.

    ``package`` is the source package provenance. ``type`` is the
    helper domain (for example ``input_boolean``). ``id`` is the YAML
    mapping key. Optional ``name`` and ``icon`` are first-class fields;
    all other YAML keys remain solely in ``raw``, which also retains
    the complete original mapping.
    """

    package: Package
    type: str
    id: str
    name: str | None = None
    icon: str | None = None
    raw: Mapping[str, object] = field(default=_EMPTY_MAPPING, repr=False)
