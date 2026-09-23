"""Immutable relationship models and analyzers for HA-DocGen.

``Relationship`` is a generic directed identity edge.
``RelationshipCollection`` holds relationships and exposes O(1)
source/target lookups. ``RelationshipRepository`` is the central
immutable store with read-only identity lookups. Entity, device,
automation, script, dashboard and MQTT analyzers derive links as
``tuple[Relationship, ...]``. No graph construction or Home
Assistant write coupling.
"""

from __future__ import annotations

from .automation_analyzer import AutomationRelationshipAnalyzer
from .dashboard_analyzer import DashboardRelationshipAnalyzer
from .device_analyzer import DeviceRelationshipAnalyzer
from .entity_analyzer import EntityRelationshipAnalyzer
from .models import (
    ObjectType,
    Relationship,
    RelationshipCollection,
    RelationshipType,
)
from .mqtt_analyzer import MQTTRelationshipAnalyzer
from .repository import RelationshipRepository
from .script_analyzer import ScriptRelationshipAnalyzer

__all__ = [
    "AutomationRelationshipAnalyzer",
    "DashboardRelationshipAnalyzer",
    "DeviceRelationshipAnalyzer",
    "EntityRelationshipAnalyzer",
    "MQTTRelationshipAnalyzer",
    "ObjectType",
    "Relationship",
    "RelationshipCollection",
    "RelationshipRepository",
    "RelationshipType",
    "ScriptRelationshipAnalyzer",
]
