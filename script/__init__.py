"""Script models and YAML parsing for HA-DocGen.

``Script`` is the immutable representation of one script.
``ScriptParser`` converts a ``PackageStructure`` script section into
``Script`` objects (with ``package`` provenance) without relationship
analysis or validation.
"""

from __future__ import annotations

from .models import Script
from .parser import ScriptParser

__all__ = [
    "Script",
    "ScriptParser",
]
