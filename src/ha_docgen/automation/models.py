"""Automation data models.

Pure data only — no YAML interpretation beyond field extraction,
and no relationship analysis.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from ..packages.models import Package

_EMPTY_RAW: Mapping[str, object] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class Automation:
    """Immutable representation of one Home Assistant automation.

    Holds first-class YAML fields plus ``raw`` as a read-only copy of
    the complete original mapping (aligned with Script/Scene).
    ``package`` is the source package provenance. Triggers, conditions
    and actions are opaque YAML values with no template, service or
    validation interpretation.
    """

    package: Package
    id: str | None = None
    alias: str | None = None
    description: str | None = None
    mode: str | None = None
    triggers: object = ()
    conditions: object = ()
    actions: object = ()
    raw: Mapping[str, object] = field(default=_EMPTY_RAW, repr=False)
