"""
ProjectTree modellen.

Deze module beschrijft de volledige directorystructuur van een
Home Assistant configuratie.

Bevat bewust geen logica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# =============================================================================
# Bestand
# =============================================================================


@dataclass(slots=True)
class ProjectFile:
    """Representatie van één bestand."""

    name: str
    path: Path
    relative_path: Path

    extension: str

    size: int

    modified: datetime


# =============================================================================
# Map
# =============================================================================


@dataclass(slots=True)
class ProjectFolder:
    """Representatie van één map."""

    name: str
    path: Path
    relative_path: Path

    parent: ProjectFolder | None = None

    files: list[ProjectFile] = field(default_factory=list)

    subfolders: list[ProjectFolder] = field(default_factory=list)


# =============================================================================
# ProjectTree
# =============================================================================


@dataclass(slots=True)
class ProjectTree:
    """Volledige projectstructuur."""

    root: Path

    folders: list[ProjectFolder] = field(default_factory=list)