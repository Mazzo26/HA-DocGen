"""Storage discovery data models.

Pure data only — no filesystem access, no JSON parsing, and no
Home Assistant registry semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class StorageFile:
    """Metadata for one file discovered under the storage root."""

    name: str
    path: Path
    relative_path: Path
    size: int
    modified: datetime
