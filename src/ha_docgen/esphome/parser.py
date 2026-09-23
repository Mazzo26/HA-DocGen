"""Parse one YamlDocument into an ESPHomeDevice.

Reads device identity and sensor, binary sensor and switch components.
Does not open files, expand substitutions, resolve includes or
discover relationships.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..yaml import YamlDocument
from .models import ESPHomeBinarySensor, ESPHomeDevice, ESPHomeSensor, ESPHomeSwitch

type _Component = ESPHomeSensor | ESPHomeBinarySensor | ESPHomeSwitch
_COMPONENT_KEYS: frozenset[str] = frozenset({"id", "name", "platform"})


class ESPHomeParser:
    """Convert one loaded YAML document into an ESPHome device."""

    def parse(self, document: YamlDocument) -> ESPHomeDevice:
        """Return an immutable device from *document*."""
        data = document.data
        if not isinstance(data, dict):
            return ESPHomeDevice(path=document.path)
        return _device(document.path, data)


def _device(path: Path, data: Mapping[str, object]) -> ESPHomeDevice:
    """Build one device from an ESPHome document mapping."""
    name, friendly_name = _device_identity(data.get("esphome"))
    return ESPHomeDevice(
        name=name,
        friendly_name=friendly_name,
        path=path,
        sensors=_section(data.get("sensor"), name, ESPHomeSensor),
        binary_sensors=_section(data.get("binary_sensor"), name, ESPHomeBinarySensor),
        switches=_section(data.get("switch"), name, ESPHomeSwitch),
    )


def _device_identity(value: object) -> tuple[str | None, str | None]:
    """Return ``esphome.name`` and ``friendly_name`` when they are strings."""
    if not isinstance(value, dict):
        return None, None
    return _optional_text(value.get("name")), _optional_text(value.get("friendly_name"))


def _section[Component: (ESPHomeSensor, ESPHomeBinarySensor, ESPHomeSwitch)](
    value: object,
    device_name: str | None,
    component_type: type[Component],
) -> tuple[Component, ...]:
    """Collect components from one section in deterministic identity order."""
    found: list[Component] = []
    _collect(value, device_name, component_type, None, found)
    return _ordered(found)


def _collect[Component: (ESPHomeSensor, ESPHomeBinarySensor, ESPHomeSwitch)](
    value: object,
    device_name: str | None,
    component_type: type[Component],
    platform: str | None,
    found: list[Component],
) -> None:
    """Walk one section value and append components that have an identity."""
    if isinstance(value, list):
        for item in value:
            _collect(item, device_name, component_type, platform, found)
        return
    if not isinstance(value, dict):
        return
    current = _optional_text(value.get("platform")) or platform
    component = _component(value, device_name, component_type, current)
    if component is not None:
        found.append(component)
    _collect_children(value, device_name, component_type, current, found)


def _collect_children[Component: (ESPHomeSensor, ESPHomeBinarySensor, ESPHomeSwitch)](
    value: Mapping[str, object],
    device_name: str | None,
    component_type: type[Component],
    platform: str | None,
    found: list[Component],
) -> None:
    """Visit nested mappings and lists under one component block."""
    for key, child in value.items():
        if key in _COMPONENT_KEYS or not isinstance(child, dict | list):
            continue
        _collect(child, device_name, component_type, platform, found)


def _component[Component: (ESPHomeSensor, ESPHomeBinarySensor, ESPHomeSwitch)](
    value: Mapping[str, object],
    device_name: str | None,
    component_type: type[Component],
    platform: str | None,
) -> Component | None:
    """Map one component block when it has an id or a name."""
    component_id = _optional_text(value.get("id"))
    name = _optional_text(value.get("name"))
    identity = _identity(device_name, component_id, name)
    if identity is None:
        return None
    return component_type(identity=identity, platform=platform, id=component_id, name=name)


def _identity(
    device_name: str | None,
    component_id: str | None,
    name: str | None,
) -> str | None:
    """Return ``device:id``, ``device:name``, or the bare key when no device name exists."""
    key = component_id if component_id is not None else name
    if key is None:
        return None
    if device_name is None:
        return key
    return f"{device_name}:{key}"


def _ordered[Component: (ESPHomeSensor, ESPHomeBinarySensor, ESPHomeSwitch)](
    components: list[Component],
) -> tuple[Component, ...]:
    """Sort by identity and collapse duplicate identities deterministically."""
    chosen: dict[str, Component] = {}
    for component in components:
        current = chosen.get(component.identity)
        if current is None or _component_key(component) < _component_key(current):
            chosen[component.identity] = component
    return tuple(sorted(chosen.values(), key=_component_key))


def _component_key(component: _Component) -> tuple[str, str, str, str]:
    """Sort components by identity, platform, name and id."""
    return (
        component.identity,
        component.platform or "",
        component.name or "",
        component.id or "",
    )


def _optional_text(value: object) -> str | None:
    """Return a non-empty string, or None for every other value."""
    if isinstance(value, str) and value != "":
        return value
    return None
