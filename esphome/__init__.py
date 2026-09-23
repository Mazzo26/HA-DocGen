"""ESPHome domain models for HA-DocGen.

``ESPHomeDevice`` is the immutable device aggregate.
``ESPHomeSensor``, ``ESPHomeBinarySensor`` and ``ESPHomeSwitch`` are
its components. ``ESPHomeParser`` converts one ``YamlDocument`` into
an ``ESPHomeDevice``. It does not discover files or discover
relationships.
"""

from __future__ import annotations

from .models import ESPHomeBinarySensor, ESPHomeDevice, ESPHomeSensor, ESPHomeSwitch
from .parser import ESPHomeParser

__all__ = [
    "ESPHomeBinarySensor",
    "ESPHomeDevice",
    "ESPHomeParser",
    "ESPHomeSensor",
    "ESPHomeSwitch",
]
