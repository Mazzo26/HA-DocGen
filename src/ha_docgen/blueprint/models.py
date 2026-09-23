"""Blueprint data models.

Pure data only — no YAML interpretation beyond field extraction,
and no selector, automation or relationship analysis.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

_EMPTY_MAPPING: Mapping[str, object] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class Blueprint:
    """Immutable representation of one Home Assistant blueprint.

    Holds blueprint metadata only. ``input`` contains the raw input
    definitions with no selector interpretation. Unknown keys remain
    solely in ``raw``, which also retains the complete original YAML.
    """

    name: str | None = None
    description: str | None = None
    domain: str | None = None
    source_url: str | None = None
    path: Path | None = None
    input: Mapping[str, object] = field(default=_EMPTY_MAPPING)
    raw: Mapping[str, object] = field(default=_EMPTY_MAPPING, repr=False)
