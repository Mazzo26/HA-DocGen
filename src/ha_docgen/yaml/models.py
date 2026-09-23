"""YAML document data models.

Pure data only — no filesystem I/O, no YAML parsing, and no
Home Assistant domain logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class YamlDocument:
    """Immutable representation of one loaded YAML document.

    Holds the source path, original text and already-parsed Python
    object. Loading and interpretation belong in later modules.
    """

    path: Path
    text: str
    data: object
