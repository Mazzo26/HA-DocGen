"""Immutable AI context data models.

Pure context structure only — no Markdown, JSON, prompt text,
exporters, parsers or filesystem access.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

from ..automation import Automation
from ..dashboard.models import Dashboard
from ..esphome import ESPHomeBinarySensor, ESPHomeDevice, ESPHomeSensor, ESPHomeSwitch
from ..helper.models import Helper
from ..packages import Package
from ..registries.models import Area, ConfigEntry, Device, Entity, Floor, Label
from ..relationships import Relationship
from ..scene import Scene
from ..script import Script
from ..template.models import Template

ContextObject = Entity | Device | Area | Label | Floor | ConfigEntry


class ContextSectionKind(StrEnum):
    """Top-level categories present on ``HomeAssistantModel``.

    New members can be added later without changing ``AIContext``.
    """

    ENTITIES = "entities"
    DEVICES = "devices"
    AREAS = "areas"
    LABELS = "labels"
    FLOORS = "floors"
    CONFIG_ENTRIES = "config_entries"


@dataclass(frozen=True, slots=True)
class ContextMetadata:
    """Immutable provenance copied from ``HomeAssistantModel``.

    Every field stays ``None`` when the model does not contain that
    value. Nothing is inferred.
    """

    repository_name: str | None = None
    project_path: Path | None = None
    version: str | None = None
    generated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ContextSection:
    """Immutable section holding the original objects of one category.

    ``items`` are the same instances stored on ``HomeAssistantModel``.
    Later modules add further sections; they do not change this type.
    """

    kind: ContextSectionKind
    title: str
    items: tuple[ContextObject, ...] = ()

    def __post_init__(self) -> None:
        """Freeze ``items`` without copying the domain objects."""
        object.__setattr__(self, "items", tuple(self.items))


@dataclass(frozen=True, slots=True)
class EntityContext:
    """Immutable context for one registry entity.

    ``entity`` is the original ``HomeAssistantModel`` object. Registry
    information is read from that object: ``entity_id``, ``domain``,
    ``name``, ``unique_id``, ``device_id``, ``area_id``,
    ``config_entry_id``, ``labels``, visibility (``disabled_by``,
    ``hidden_by``) and lifecycle (``created_at``, ``modified_at``,
    ``orphaned_timestamp``). ``relationships`` are edges already stored
    for ``entity.entity_id``. ``packages`` are packages those edges name
    when the package object already exists. Nothing is inferred.
    """

    entity: Entity
    relationships: tuple[Relationship, ...] = ()
    packages: tuple[Package, ...] = ()

    def __post_init__(self) -> None:
        """Freeze related collections without copying domain objects."""
        object.__setattr__(self, "relationships", tuple(self.relationships))
        object.__setattr__(self, "packages", tuple(self.packages))


@dataclass(frozen=True, slots=True)
class AutomationContext:
    """Immutable context for one automation.

    ``automation`` is the original ``YamlRepository`` object, including
    triggers, conditions, actions and raw metadata. ``package`` is that
    automation's package reference. Related entities, scripts and scenes
    are existing objects. Missing targets stay unresolved ids.
    """

    automation: Automation
    package: Package
    relationships: tuple[Relationship, ...] = ()
    referenced_entities: tuple[Entity, ...] = ()
    unresolved_entity_ids: tuple[str, ...] = ()
    related_scripts: tuple[Script, ...] = ()
    unresolved_script_ids: tuple[str, ...] = ()
    related_scenes: tuple[Scene, ...] = ()
    unresolved_scene_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Freeze relationship and reference collections."""
        object.__setattr__(self, "relationships", tuple(self.relationships))
        object.__setattr__(self, "referenced_entities", tuple(self.referenced_entities))
        object.__setattr__(self, "unresolved_entity_ids", tuple(self.unresolved_entity_ids))
        object.__setattr__(self, "related_scripts", tuple(self.related_scripts))
        object.__setattr__(self, "unresolved_script_ids", tuple(self.unresolved_script_ids))
        object.__setattr__(self, "related_scenes", tuple(self.related_scenes))
        object.__setattr__(self, "unresolved_scene_ids", tuple(self.unresolved_scene_ids))


@dataclass(frozen=True, slots=True)
class DashboardContext:
    """Immutable context for one dashboard.

    ``dashboard`` is the original ``YamlRepository`` object, including
    its metadata. ``views`` are that object's opaque view mappings.
    No view key is read. Referenced entities and related automations
    are existing objects. Missing targets stay unresolved ids.
    """

    dashboard: Dashboard
    views: tuple[Mapping[str, object], ...] = ()
    relationships: tuple[Relationship, ...] = ()
    referenced_entities: tuple[Entity, ...] = ()
    unresolved_entity_ids: tuple[str, ...] = ()
    related_automations: tuple[Automation, ...] = ()
    unresolved_automation_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Freeze view and reference collections."""
        object.__setattr__(self, "views", tuple(self.views))
        object.__setattr__(self, "relationships", tuple(self.relationships))
        object.__setattr__(self, "referenced_entities", tuple(self.referenced_entities))
        object.__setattr__(self, "unresolved_entity_ids", tuple(self.unresolved_entity_ids))
        object.__setattr__(self, "related_automations", tuple(self.related_automations))
        object.__setattr__(
            self,
            "unresolved_automation_ids",
            tuple(self.unresolved_automation_ids),
        )


_PACKAGE_COLLECTIONS = (
    "automations",
    "scripts",
    "scenes",
    "helpers",
    "templates",
    "dashboards",
    "relationships",
    "referenced_entities",
    "unresolved_entity_ids",
    "referenced_scripts",
    "unresolved_script_ids",
    "referenced_scenes",
    "unresolved_scene_ids",
    "referenced_dashboards",
    "unresolved_dashboard_ids",
)


@dataclass(frozen=True, slots=True)
class PackageContext:
    """Immutable context for one package.

    ``package`` is the original ``YamlRepository`` object. Its name,
    path and document are the overview and metadata; those fields are
    not copied. Automations, scripts, scenes, helpers and templates are
    objects that already reference this package. Dashboards have no
    package reference, so ``dashboards`` stays empty. Referenced
    entities, scripts, scenes and dashboards are existing objects.
    Missing targets stay unresolved ids.
    """

    package: Package
    automations: tuple[Automation, ...] = ()
    scripts: tuple[Script, ...] = ()
    scenes: tuple[Scene, ...] = ()
    helpers: tuple[Helper, ...] = ()
    templates: tuple[Template, ...] = ()
    dashboards: tuple[Dashboard, ...] = ()
    relationships: tuple[Relationship, ...] = ()
    referenced_entities: tuple[Entity, ...] = ()
    unresolved_entity_ids: tuple[str, ...] = ()
    referenced_scripts: tuple[Script, ...] = ()
    unresolved_script_ids: tuple[str, ...] = ()
    referenced_scenes: tuple[Scene, ...] = ()
    unresolved_scene_ids: tuple[str, ...] = ()
    referenced_dashboards: tuple[Dashboard, ...] = ()
    unresolved_dashboard_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Freeze member and reference collections."""
        for name in _PACKAGE_COLLECTIONS:
            object.__setattr__(self, name, tuple(getattr(self, name)))


_REFERENCE_FIELDS = (
    "relationships",
    "referenced_entities",
    "unresolved_entity_ids",
)


@dataclass(frozen=True, slots=True)
class ESPHomeSensorContext:
    """Immutable context for one ESPHome sensor.

    ``sensor`` is the original component. Identity, platform, id and
    name stay on that object. Relationships are edges already stored
    for ``sensor.identity`` whose other endpoint is an entity.
    Missing targets stay unresolved ids.
    """

    sensor: ESPHomeSensor
    relationships: tuple[Relationship, ...] = ()
    referenced_entities: tuple[Entity, ...] = ()
    unresolved_entity_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Freeze relationship and entity collections."""
        _freeze_fields(self, _REFERENCE_FIELDS)


@dataclass(frozen=True, slots=True)
class ESPHomeBinarySensorContext:
    """Immutable context for one ESPHome binary sensor.

    ``binary_sensor`` is the original component. Identity, platform,
    id and name stay on that object. Relationships are edges already
    stored for ``binary_sensor.identity`` whose other endpoint is an
    entity. Missing targets stay unresolved ids.
    """

    binary_sensor: ESPHomeBinarySensor
    relationships: tuple[Relationship, ...] = ()
    referenced_entities: tuple[Entity, ...] = ()
    unresolved_entity_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Freeze relationship and entity collections."""
        _freeze_fields(self, _REFERENCE_FIELDS)


@dataclass(frozen=True, slots=True)
class ESPHomeSwitchContext:
    """Immutable context for one ESPHome switch.

    ``switch`` is the original component. Identity, platform, id and
    name stay on that object. Relationships are edges already stored
    for ``switch.identity`` whose other endpoint is an entity.
    Missing targets stay unresolved ids.
    """

    switch: ESPHomeSwitch
    relationships: tuple[Relationship, ...] = ()
    referenced_entities: tuple[Entity, ...] = ()
    unresolved_entity_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Freeze relationship and entity collections."""
        _freeze_fields(self, _REFERENCE_FIELDS)


@dataclass(frozen=True, slots=True)
class ESPHomeDeviceContext:
    """Immutable context for one ESPHome device.

    ``device`` is the original device and is the overview. Sensors,
    binary sensors and switches are contexts for the components stored
    on that device. Entity references come from relationships already
    stored for the device name. A device without a name contributes
    no relationships. Component entity references stay on the component.
    """

    device: ESPHomeDevice
    relationships: tuple[Relationship, ...] = ()
    referenced_entities: tuple[Entity, ...] = ()
    unresolved_entity_ids: tuple[str, ...] = ()
    sensors: tuple[ESPHomeSensorContext, ...] = ()
    binary_sensors: tuple[ESPHomeBinarySensorContext, ...] = ()
    switches: tuple[ESPHomeSwitchContext, ...] = ()

    def __post_init__(self) -> None:
        """Freeze references and order component overviews."""
        _freeze_fields(self, _REFERENCE_FIELDS)
        object.__setattr__(self, "sensors", _ordered_sensor_contexts(self.sensors))
        object.__setattr__(
            self,
            "binary_sensors",
            _ordered_binary_sensor_contexts(self.binary_sensors),
        )
        object.__setattr__(self, "switches", _ordered_switch_contexts(self.switches))


@dataclass(frozen=True, slots=True)
class AIContext:
    """Immutable AI context tree.

    Holds provenance, registry sections, entity contexts, automation
    contexts, dashboard contexts, package contexts and ESPHome device
    contexts. Prompt and export models are not part of this tree.
    """

    metadata: ContextMetadata
    sections: tuple[ContextSection, ...] = ()
    entity_contexts: tuple[EntityContext, ...] = ()
    automation_contexts: tuple[AutomationContext, ...] = ()
    dashboard_contexts: tuple[DashboardContext, ...] = ()
    package_contexts: tuple[PackageContext, ...] = ()
    esphome_contexts: tuple[ESPHomeDeviceContext, ...] = ()

    def __post_init__(self) -> None:
        """Freeze collections and order them deterministically."""
        object.__setattr__(self, "sections", _ordered_sections(self.sections))
        object.__setattr__(self, "entity_contexts", _ordered_entity_contexts(self.entity_contexts))
        object.__setattr__(
            self,
            "automation_contexts",
            _ordered_automation_contexts(self.automation_contexts),
        )
        object.__setattr__(
            self,
            "dashboard_contexts",
            _ordered_dashboard_contexts(self.dashboard_contexts),
        )
        object.__setattr__(
            self,
            "package_contexts",
            _ordered_package_contexts(self.package_contexts),
        )
        object.__setattr__(
            self,
            "esphome_contexts",
            _ordered_esphome_contexts(self.esphome_contexts),
        )


def _ordered_sections(
    sections: tuple[ContextSection, ...],
) -> tuple[ContextSection, ...]:
    """Return sections ordered by kind and title."""
    return tuple(sorted(sections, key=_section_key))


def _section_key(section: ContextSection) -> tuple[str, str]:
    """Sort sections by kind value, then title."""
    return (section.kind.value, section.title)


def _ordered_entity_contexts(
    contexts: tuple[EntityContext, ...],
) -> tuple[EntityContext, ...]:
    """Return entity contexts ordered by entity identity."""
    return tuple(sorted(contexts, key=_entity_context_key))


def _entity_context_key(context: EntityContext) -> tuple[str, str, str]:
    """Sort entity contexts by entity id, registry id and unique id."""
    entity = context.entity
    return (entity.entity_id, entity.registry_id, entity.unique_id)


def _ordered_automation_contexts(
    contexts: tuple[AutomationContext, ...],
) -> tuple[AutomationContext, ...]:
    """Return automation contexts ordered by automation identity."""
    return tuple(sorted(contexts, key=_automation_context_key))


def _automation_context_key(context: AutomationContext) -> tuple[str, str, str]:
    """Sort automation contexts by id, alias and package name."""
    automation = context.automation
    return (automation.id or "", automation.alias or "", automation.package.name)


def _ordered_dashboard_contexts(
    contexts: tuple[DashboardContext, ...],
) -> tuple[DashboardContext, ...]:
    """Return dashboard contexts ordered by dashboard identity."""
    return tuple(sorted(contexts, key=_dashboard_context_key))


def _dashboard_context_key(context: DashboardContext) -> tuple[str, str, str]:
    """Sort dashboard contexts by id, title and source path."""
    dashboard = context.dashboard
    path = "" if dashboard.path is None else dashboard.path.as_posix()
    return (dashboard.id or "", dashboard.title or "", path)


def _ordered_package_contexts(
    contexts: tuple[PackageContext, ...],
) -> tuple[PackageContext, ...]:
    """Return package contexts ordered by package identity."""
    return tuple(sorted(contexts, key=_package_context_key))


def _package_context_key(context: PackageContext) -> tuple[str, str]:
    """Sort package contexts by name and source path."""
    package = context.package
    return (package.name, package.path.as_posix())


def _freeze_fields(owner: object, names: tuple[str, ...]) -> None:
    """Store each named collection as a tuple."""
    for name in names:
        object.__setattr__(owner, name, tuple(getattr(owner, name)))


def _ordered_sensor_contexts(
    contexts: tuple[ESPHomeSensorContext, ...],
) -> tuple[ESPHomeSensorContext, ...]:
    """Return sensor contexts ordered by component identity."""
    return tuple(sorted(contexts, key=_sensor_context_key))


def _sensor_context_key(context: ESPHomeSensorContext) -> tuple[str, str, str, str]:
    """Sort sensor contexts by identity, platform, name and id."""
    return _component_sort_key(context.sensor)


def _ordered_binary_sensor_contexts(
    contexts: tuple[ESPHomeBinarySensorContext, ...],
) -> tuple[ESPHomeBinarySensorContext, ...]:
    """Return binary sensor contexts ordered by component identity."""
    return tuple(sorted(contexts, key=_binary_sensor_context_key))


def _binary_sensor_context_key(
    context: ESPHomeBinarySensorContext,
) -> tuple[str, str, str, str]:
    """Sort binary sensor contexts by identity, platform, name and id."""
    return _component_sort_key(context.binary_sensor)


def _ordered_switch_contexts(
    contexts: tuple[ESPHomeSwitchContext, ...],
) -> tuple[ESPHomeSwitchContext, ...]:
    """Return switch contexts ordered by component identity."""
    return tuple(sorted(contexts, key=_switch_context_key))


def _switch_context_key(context: ESPHomeSwitchContext) -> tuple[str, str, str, str]:
    """Sort switch contexts by identity, platform, name and id."""
    return _component_sort_key(context.switch)


def _component_sort_key(
    component: ESPHomeSensor | ESPHomeBinarySensor | ESPHomeSwitch,
) -> tuple[str, str, str, str]:
    """Sort one component by identity, platform, name and id."""
    return (
        component.identity,
        component.platform or "",
        component.name or "",
        component.id or "",
    )


def _ordered_esphome_contexts(
    contexts: tuple[ESPHomeDeviceContext, ...],
) -> tuple[ESPHomeDeviceContext, ...]:
    """Return device contexts ordered by device identity."""
    return tuple(sorted(contexts, key=_esphome_device_context_key))


def _esphome_device_context_key(
    context: ESPHomeDeviceContext,
) -> tuple[bool, str, str]:
    """Sort device contexts by name, then POSIX path. Unnamed devices are last."""
    device = context.device
    path = "" if device.path is None else device.path.as_posix()
    return (device.name is None, device.name or "", path)
