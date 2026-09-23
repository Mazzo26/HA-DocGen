"""Immutable Home Assistant inventory projection.

Lists source paths already stored on the YAML aggregate separately
from parsed Home Assistant objects. Holds no Markdown, JSON, console
formatting or filesystem logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..automation import Automation
from ..blueprint import Blueprint
from ..helper import Helper
from ..registries import Label
from ..scene import Scene
from ..script import Script


@dataclass(frozen=True, slots=True)
class DiscoveredFile:
    """One source path already stored on a package or blueprint.

    ``path`` is that existing ``Path``. This record is not a parsed
    Home Assistant object. Its presence does not mean the file
    produced an automation, script, scene, blueprint, helper or label.
    """

    path: Path


@dataclass(frozen=True, slots=True)
class HomeAssistantInventory:
    """Parsed Home Assistant objects from one completed analysis.

    ``discovered_files`` are file provenance. The other collections are
    the original repository instances, ordered deterministically.
    """

    discovered_files: tuple[DiscoveredFile, ...] = ()
    automations: tuple[Automation, ...] = ()
    scripts: tuple[Script, ...] = ()
    scenes: tuple[Scene, ...] = ()
    blueprints: tuple[Blueprint, ...] = ()
    helpers: tuple[Helper, ...] = ()
    labels: tuple[Label, ...] = ()

    def __post_init__(self) -> None:
        """Freeze every collection without copying domain objects."""
        for name in (
            "discovered_files",
            "automations",
            "scripts",
            "scenes",
            "blueprints",
            "helpers",
            "labels",
        ):
            object.__setattr__(self, name, tuple(getattr(self, name)))
