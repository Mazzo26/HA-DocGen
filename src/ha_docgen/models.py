"""
HA-DocGen datamodellen.

Alle communicatie tussen modules verloopt via deze dataclasses.
Deze module bevat bewust geen logica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


# =============================================================================
# Algemene scanresultaten
# =============================================================================


@dataclass(slots=True)
class ScanResult:
    """Samenvatting van een volledige scan."""

    root: Path

    yaml_files: int = 0
    json_files: int = 0
    python_files: int = 0

    package_count: int = 0
    dashboard_count: int = 0
    esphome_count: int = 0
    theme_count: int = 0
    custom_component_count: int = 0

    entity_count: int = 0
    device_count: int = 0
    area_count: int = 0
    integration_count: int = 0


# =============================================================================
# Folder informatie
# =============================================================================


@dataclass(slots=True)
class FolderInfo:
    """Informatie over een projectmap."""

    name: str
    path: Path
    exists: bool
    file_count: int = 0


# =============================================================================
# Package informatie
# =============================================================================


@dataclass(slots=True)
class PackageInfo:
    """Beschrijving van een Home Assistant package."""

    name: str
    path: Path


# =============================================================================
# Dashboard informatie
# =============================================================================


@dataclass(slots=True)
class DashboardInfo:
    """Beschrijving van een dashboard."""

    name: str
    path: Path


# =============================================================================
# ESPHome
# =============================================================================


@dataclass(slots=True)
class ESPHomeNode:
    """Beschrijving van een ESPHome node."""

    name: str
    path: Path


# =============================================================================
# Devices
# =============================================================================


@dataclass(slots=True)
class DeviceInfo:
    """Beschrijving van een Home Assistant device."""

    id: str
    name: str
    manufacturer: str | None = None
    model: str | None = None


# =============================================================================
# Entities
# =============================================================================


@dataclass(slots=True)
class EntityInfo:
    """Beschrijving van een Home Assistant entity."""

    entity_id: str
    platform: str
    domain: str
    device_id: str | None = None


# =============================================================================
# Integraties
# =============================================================================


@dataclass(slots=True)
class IntegrationInfo:
    """Beschrijving van een Home Assistant integratie."""

    domain: str
    title: str


# =============================================================================
# Hoofdmodel
# =============================================================================


@dataclass(slots=True)
class HomeAssistantModel:
    """Volledige representatie van een Home Assistant installatie."""

    scan: ScanResult

    folders: list[FolderInfo] = field(default_factory=list)

    packages: list[PackageInfo] = field(default_factory=list)

    dashboards: list[DashboardInfo] = field(default_factory=list)

    esphome_nodes: list[ESPHomeNode] = field(default_factory=list)

    devices: list[DeviceInfo] = field(default_factory=list)

    entities: list[EntityInfo] = field(default_factory=list)

    integrations: list[IntegrationInfo] = field(default_factory=list)