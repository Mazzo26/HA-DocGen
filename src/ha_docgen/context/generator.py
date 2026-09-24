"""Generate an AIContext from an AnalysisModel.

Projects registry sections, entity contexts, automation contexts,
dashboard contexts, package contexts and ESPHome contexts from
aggregates already stored on the analysis model. Performs no parsing,
discovery, validation or filesystem access, and does not modify the
aggregate.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TypeVar

from ..analysis import AnalysisModel
from ..registries.home_assistant_model import HomeAssistantModel
from ..registries.models import Area, ConfigEntry, Device, Entity, Floor, Label
from .automation_context import project_automation_contexts
from .dashboard_context import project_dashboard_contexts
from .entity_context import project_entity_contexts
from .esphome_context import project_esphome_contexts
from .models import AIContext, ContextMetadata, ContextSection, ContextSectionKind
from .package_context import project_package_contexts

_Item = TypeVar("_Item")


class ContextGenerator:
    """Project an ``AnalysisModel`` into an immutable ``AIContext``.

    Fully stateless: no instance state, no caching and no side effects.
    The same analysis aggregate always yields an equal context.
    """

    def generate(self, analysis_model: AnalysisModel) -> AIContext:
        """Return an AIContext projected from one analysis aggregate."""
        return AIContext(
            metadata=ContextMetadata(),
            sections=_sections(analysis_model.home_assistant_model),
            entity_contexts=project_entity_contexts(analysis_model),
            automation_contexts=project_automation_contexts(analysis_model),
            dashboard_contexts=project_dashboard_contexts(analysis_model),
            package_contexts=project_package_contexts(analysis_model),
            esphome_contexts=project_esphome_contexts(analysis_model),
        )


def _sections(model: HomeAssistantModel) -> tuple[ContextSection, ...]:
    """Return one section per non-empty top-level collection."""
    return _keep(
        (
            _section(ContextSectionKind.ENTITIES, "Entities", model.entities, _entity_key),
            _section(ContextSectionKind.DEVICES, "Devices", model.devices, _device_key),
            _section(ContextSectionKind.AREAS, "Areas", model.areas, _area_key),
            _section(ContextSectionKind.LABELS, "Labels", model.labels, _label_key),
            _section(ContextSectionKind.FLOORS, "Floors", model.floors, _floor_key),
            _section(
                ContextSectionKind.CONFIG_ENTRIES,
                "Config Entries",
                model.config_entries,
                _config_entry_key,
            ),
        )
    )


def _section(  # noqa: UP047
    kind: ContextSectionKind,
    title: str,
    items: Sequence[_Item],
    key: Callable[[_Item], str],
) -> ContextSection | None:
    """Return a deterministically ordered section, or None when empty."""
    if not items:
        return None
    return ContextSection(kind=kind, title=title, items=tuple(sorted(items, key=key)))


def _keep(
    sections: tuple[ContextSection | None, ...],
) -> tuple[ContextSection, ...]:
    """Drop categories that contain no objects."""
    return tuple(section for section in sections if section is not None)


def _entity_key(entity: Entity) -> str:
    """Return the entity sort key already stored on the object."""
    return entity.entity_id


def _device_key(device: Device) -> str:
    """Return the device sort key already stored on the object."""
    return device.registry_id


def _area_key(area: Area) -> str:
    """Return the area sort key already stored on the object."""
    return area.registry_id


def _label_key(label: Label) -> str:
    """Return the label sort key already stored on the object."""
    return label.registry_id


def _floor_key(floor: Floor) -> str:
    """Return the floor sort key already stored on the object."""
    return floor.registry_id


def _config_entry_key(entry: ConfigEntry) -> str:
    """Return the config-entry sort key already stored on the object."""
    return entry.registry_id
