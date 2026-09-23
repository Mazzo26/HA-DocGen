"""
Filesystem modellen.

Deze modellen bevatten alle informatie die tijdens het uitlezen
van de schijf wordt verzameld.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class FilesystemEntry:
    """Representatie van één bestand of map."""

    path: Path
    relative_path: Path

    name: str

    is_file: bool
    is_dir: bool

    extension: str

    size: int

    modified: datetime