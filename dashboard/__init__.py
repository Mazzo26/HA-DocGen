"""Dashboard models and YAML parsing for HA-DocGen.

``Dashboard`` is the immutable representation of one YAML dashboard.
``DashboardParser`` converts a ``YamlDocument`` into a ``Dashboard``
without card, entity, badge or navigation analysis.
"""

from __future__ import annotations

from .models import Dashboard
from .parser import DashboardParser

__all__ = [
    "Dashboard",
    "DashboardParser",
]
