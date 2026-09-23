"""Immutable AI context models and generator.

``AIContext`` holds provenance, registry sections, entity contexts,
automation contexts, dashboard contexts, package contexts and ESPHome
device contexts. ``ContextGenerator`` projects an ``AnalysisModel``
into that tree. No parsers, exporters, CLI or filesystem coupling.
"""

from __future__ import annotations

from .generator import ContextGenerator
from .models import (
    AIContext,
    AutomationContext,
    ContextMetadata,
    ContextSection,
    ContextSectionKind,
    DashboardContext,
    EntityContext,
    ESPHomeBinarySensorContext,
    ESPHomeDeviceContext,
    ESPHomeSensorContext,
    ESPHomeSwitchContext,
    PackageContext,
)

__all__ = [
    "AIContext",
    "AutomationContext",
    "ContextGenerator",
    "ContextMetadata",
    "ContextSection",
    "ContextSectionKind",
    "DashboardContext",
    "ESPHomeBinarySensorContext",
    "ESPHomeDeviceContext",
    "ESPHomeSensorContext",
    "ESPHomeSwitchContext",
    "EntityContext",
    "PackageContext",
]
