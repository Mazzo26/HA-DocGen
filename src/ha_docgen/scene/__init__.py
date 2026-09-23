"""Scene models and YAML parsing for HA-DocGen.

``Scene`` is the immutable representation of one scene.
``SceneParser`` converts a ``PackageStructure`` scene section into
``Scene`` objects (with ``package`` provenance) without relationship
analysis or validation.
"""

from __future__ import annotations

from .models import Scene
from .parser import SceneParser

__all__ = [
    "Scene",
    "SceneParser",
]
