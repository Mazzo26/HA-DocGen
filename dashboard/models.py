"""Dashboard data models.

Pure data only — no YAML interpretation beyond field extraction,
and no card, entity, badge or navigation analysis.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

_EMPTY_MAPPING: Mapping[str, object] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class Dashboard:
    """Immutable representation of one Home Assistant YAML dashboard.

    Holds dashboard metadata only. ``views`` contains raw view
    definitions with no card interpretation. Unknown keys remain
    solely in ``raw``, which also retains the complete original
    mapping.
    """

    id: str | None = None
    title: str | None = None
    mode: str | None = None
    path: Path | None = None
    views: tuple[Mapping[str, object], ...] = ()
    raw: Mapping[str, object] = field(default=_EMPTY_MAPPING, repr=False)
