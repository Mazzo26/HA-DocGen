"""Immutable analysis aggregate for HA-DocGen.

``AnalysisModel`` references the registry, YAML and relationship
aggregates. ESPHome devices are part of ``YamlRepository``. The
aggregate does not parse, analyse or copy their contents.
"""

from __future__ import annotations

from .models import AnalysisModel

__all__ = ["AnalysisModel"]
