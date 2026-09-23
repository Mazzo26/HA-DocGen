"""Template data models.

Pure data only — no Jinja interpretation, validation, or relationship
analysis. A Template is solely a found template string from YAML.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from ..packages.models import Package

_EMPTY_MAPPING: Mapping[str, object] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class Template:
    """Immutable representation of one template string found in YAML.

    Holds source ``package`` provenance, origin ``kind``, the original
    ``source`` string, optional source ``path``, and the parent YAML
    mapping in ``raw``. No Jinja parsing or Home Assistant semantics.
    """

    package: Package
    kind: str
    source: str
    path: Path | None = None
    raw: Mapping[str, object] = field(default=_EMPTY_MAPPING, repr=False)
