"""Home Assistant registry parsers and aggregate model.

Each registry parser reads one ``.storage`` file and returns typed models.
``HomeAssistantModel`` aggregates parsed registry objects for lookup.
Filesystem discovery remains in ``ha_docgen.storage``.
"""

from __future__ import annotations

from .area_parser import AreaRegistryParser
from .config_entry_parser import ConfigEntryRegistryParser
from .device_parser import DeviceRegistryParser
from .entity_parser import EntityRegistryParser
from .floor_parser import FloorRegistryParser
from .home_assistant_model import HomeAssistantModel
from .label_parser import LabelRegistryParser
from .models import Area, ConfigEntry, Device, Entity, Floor, Label

__all__ = [
    "Area",
    "AreaRegistryParser",
    "ConfigEntry",
    "ConfigEntryRegistryParser",
    "Device",
    "DeviceRegistryParser",
    "Entity",
    "EntityRegistryParser",
    "Floor",
    "FloorRegistryParser",
    "HomeAssistantModel",
    "Label",
    "LabelRegistryParser",
]
