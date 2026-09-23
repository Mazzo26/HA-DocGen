"""Deterministic Home Assistant project data for integration tests."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

from .filesystem import sample_project_files


def integration_project_files() -> Mapping[str, str]:
    """Return a representative project spanning every analysed layer."""
    files = {
        "configuration.yaml": "homeassistant:\n  name: Integration\n",
        "packages/climate.yaml": _CLIMATE_PACKAGE,
        "packages/lighting.yaml": _LIGHTING_PACKAGE,
        "dashboards/main.yaml": _DASHBOARD,
        ".storage/core.entity_registry": _registry("entities", _ENTITIES),
        ".storage/core.device_registry": _registry("devices", _DEVICES),
        ".storage/core.area_registry": _registry("areas", _AREAS),
        ".storage/floor_registry": _registry("floors", _FLOORS),
        ".storage/core.config_entries": _registry("entries", _CONFIG_ENTRIES),
    }
    return MappingProxyType(files)


def project_profile_files(profile: str) -> Mapping[str, str]:
    """Return one deterministic project profile by name."""
    if profile == "minimal":
        return sample_project_files()
    if profile == "typical":
        return integration_project_files()
    if profile == "larger":
        return _larger_project_files()
    if profile == "edge":
        return _edge_case_project_files()
    raise ValueError(f"Unknown project profile: {profile}")


def runtime_config_text(root: Path) -> str:
    """Return a complete runtime configuration for ``root``."""
    return _RUNTIME_CONFIG.format(root=root.as_posix())


def _registry(key: str, entries: tuple[dict[str, object], ...]) -> str:
    """Serialize one Home Assistant registry deterministically."""
    return json.dumps(
        {"data": {key: entries}},
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    ) + "\n"


def _larger_project_files() -> Mapping[str, str]:
    """Return a larger project without duplicating the representative files."""
    files = dict(integration_project_files())
    for index in range(1, 9):
        files[f"packages/generated_{index:02}.yaml"] = (
            "automation:\n"
            f"  - id: generated_{index:02}\n"
            f"    alias: Generated {index:02}\n"
            "    action:\n"
            "      - service: light.turn_on\n"
            "        target:\n"
            "          entity_id: light.kitchen\n"
        )
    return MappingProxyType(files)


def _edge_case_project_files() -> Mapping[str, str]:
    """Return a project with empty, nested and unsupported files."""
    files = dict(sample_project_files())
    files.update(
        {
            "packages/empty.yaml": "",
            "packages/nested/mixed.YML": "script: {}\n",
            "dashboards/empty.yaml": "views: []\n",
            "notes/readme.txt": "not analysed\n",
            ".storage/unrelated": "{}\n",
        }
    )
    return MappingProxyType(files)


_LIGHTING_PACKAGE = """\
automation:
  - id: arrival
    alias: Arrival
    trigger:
      - platform: state
        entity_id: binary_sensor.door
    action:
      - service: light.turn_on
        target:
          entity_id: light.kitchen
script:
  evening:
    alias: Evening
    mode: single
    sequence:
      - service: mqtt.publish
        data:
          topic: home/evening
          payload: "on"
scene:
  - id: relaxed
    name: Relaxed
    entities:
      light.kitchen: "on"
input_boolean:
  guests:
    name: Guests
mqtt:
  sensor:
    - unique_id: room_temperature
      name: Room temperature
      state_topic: home/temperature
template:
  - sensor:
      - entity_id: sensor.comfort
        name: Comfort
        state: "{{ states('sensor.temperature') }}"
"""

_CLIMATE_PACKAGE = """\
automation:
  - id: climate_notice
    alias: Climate notice
    action:
      - service: script.turn_on
        target:
          entity_id: script.evening
"""

_DASHBOARD = """\
id: main
title: Main
mode: yaml
views:
  - title: Home
    cards:
      - type: entities
        entities:
          - light.kitchen
          - sensor.temperature
"""

_ENTITIES = (
    {
        "id": "entity-light",
        "entity_id": "light.kitchen",
        "unique_id": "light-kitchen",
        "device_id": "device-kitchen",
        "area_id": "kitchen",
        "config_entry_id": "entry-mqtt",
        "name": "Kitchen light",
        "platform": "mqtt",
    },
    {
        "id": "entity-temperature",
        "entity_id": "sensor.temperature",
        "unique_id": "temperature",
        "device_id": "device-kitchen",
        "name": "Temperature",
    },
    {
        "id": "entity-door",
        "entity_id": "binary_sensor.door",
        "unique_id": "door",
        "device_id": "device-kitchen",
        "name": "Door",
    },
    {
        "id": "entity-orphan",
        "entity_id": "sensor.orphan",
        "unique_id": "orphan",
        "name": "Orphan",
    },
)

_DEVICES = (
    {
        "id": "device-kitchen",
        "identifiers": [["mqtt", "kitchen"]],
        "area_id": "kitchen",
        "config_entries": ["entry-mqtt"],
        "name": "Kitchen device",
    },
)

_AREAS = ({"area_id": "kitchen", "name": "Kitchen", "floor_id": "ground"},)
_FLOORS = ({"floor_id": "ground", "name": "Ground", "level": 0},)
_CONFIG_ENTRIES = (
    {
        "entry_id": "entry-mqtt",
        "domain": "mqtt",
        "title": "MQTT",
        "state": "loaded",
    },
)

_RUNTIME_CONFIG = """\
project:
  name: Integration
  version: "0.1.0"
paths:
  root: "{root}"
  configuration: "configuration.yaml"
  packages: "packages"
  dashboards: "dashboards"
  esphome: "esphome"
  docs: "docs"
  themes: "themes"
  custom_components: "custom_components"
  www: "www"
  storage: ".storage"
files:
  entity_registry: ".storage/core.entity_registry"
  device_registry: ".storage/core.device_registry"
  area_registry: ".storage/core.area_registry"
  floor_registry: ".storage/floor_registry"
  config_entries: ".storage/core.config_entries"
output:
  readme: "README.md"
  ai_context: "AI_CONTEXT.md"
  entity_map: "ENTITY_MAP.md"
  docs: "generated"
cache:
  path: ".cache/integration.json"
"""
