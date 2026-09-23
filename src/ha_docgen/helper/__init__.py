"""Helper models and YAML parsing for HA-DocGen.

``Helper`` is the immutable representation of one helper.
``HelperParser`` converts supported helper sections from a
``PackageStructure`` into ``Helper`` objects (with ``package``
provenance) without relationship analysis or validation.
"""

from __future__ import annotations

from .models import Helper
from .parser import SUPPORTED_HELPER_TYPES, HelperParser

__all__ = [
    "SUPPORTED_HELPER_TYPES",
    "Helper",
    "HelperParser",
]
