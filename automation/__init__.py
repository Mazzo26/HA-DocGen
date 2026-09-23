"""Automation models and YAML parsing for HA-DocGen.

``Automation`` is the immutable representation of one automation.
``AutomationParser`` converts a ``PackageStructure`` automation section
into ``Automation`` objects (with ``package`` provenance) without
relationship analysis or validation.
"""

from __future__ import annotations

from .models import Automation
from .parser import AutomationParser

__all__ = [
    "Automation",
    "AutomationParser",
]
