"""Home Assistant project structure constants.

Project-specific folder names and structural markers.
Configurable paths remain in tools/config.yaml.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

ROOT_RELATIVE: Final[Path] = Path(".")

FOLDER_PACKAGES: Final[str] = "packages"
FOLDER_DASHBOARDS: Final[str] = "dashboards"
FOLDER_ESPHOME: Final[str] = "esphome"
FOLDER_THEMES: Final[str] = "themes"
FOLDER_CUSTOM_COMPONENTS: Final[str] = "custom_components"
FOLDER_WWW: Final[str] = "www"
FOLDER_STORAGE: Final[str] = ".storage"

FILE_ENTITY_REGISTRY: Final[str] = "core.entity_registry"
FILE_DEVICE_REGISTRY: Final[str] = "core.device_registry"
FILE_AREA_REGISTRY: Final[str] = "core.area_registry"
FILE_LABEL_REGISTRY: Final[str] = "core.label_registry"
FILE_FLOOR_REGISTRY: Final[str] = "core.floor_registry"
FILE_CONFIG_ENTRIES: Final[str] = "core.config_entries"

PROJECT_FOLDERS: Final[tuple[str, ...]] = (
    FOLDER_PACKAGES,
    FOLDER_DASHBOARDS,
    FOLDER_ESPHOME,
    FOLDER_THEMES,
    FOLDER_CUSTOM_COMPONENTS,
    FOLDER_WWW,
    FOLDER_STORAGE,
)
