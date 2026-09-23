"""Blueprint models and YAML parsing for HA-DocGen.

``Blueprint`` is the immutable representation of one Home Assistant
blueprint. ``BlueprintParser`` converts a ``YamlDocument`` into a
``Blueprint`` without selector, automation or relationship analysis.
"""

from __future__ import annotations

from .models import Blueprint
from .parser import BlueprintParser

__all__ = [
    "Blueprint",
    "BlueprintParser",
]
