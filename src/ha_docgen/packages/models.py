"""Package data models.

Pure data only — no filesystem I/O, no YAML interpretation, and no
Home Assistant domain objects (automations, scripts, sensors, …).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from ..yaml.models import YamlDocument


@dataclass(frozen=True, slots=True)
class Package:
    """Immutable public representation of one Home Assistant package.

    Holds identity (``name``, ``path``) and the already-loaded
    ``YamlDocument``. Interpretation of YAML contents belongs in
    later modules.
    """

    name: str
    path: Path
    document: YamlDocument


@dataclass(frozen=True, slots=True)
class Section:
    """Immutable representation of one top-level package YAML section.

    Holds only the section ``name`` and the raw YAML ``data``. No
    parsing, validation, or Home Assistant semantics.
    """

    name: str
    data: object


@dataclass(frozen=True, slots=True)
class PackageStructure:
    """Immutable structural view of one package.

    Holds the source ``Package`` and the top-level ``Section`` objects
    present in its YAML root. Section contents are not interpreted.
    """

    package: Package
    sections: tuple[Section, ...]
    _index: Mapping[str, Section] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """Build an immutable O(1) section-name index."""
        object.__setattr__(
            self,
            "_index",
            MappingProxyType({section.name: section for section in self.sections}),
        )

    def has_section(self, name: str) -> bool:
        """Return True when a section with the given name exists."""
        return name in self._index

    def get_section(self, name: str) -> Section | None:
        """Return the section with the given name, or None."""
        return self._index.get(name)
