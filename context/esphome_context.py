"""Project ESPHome context from an AnalysisModel.

Maps devices already stored on the YAML aggregate. Resolves Home
Assistant entities only through existing relationships. Missing
targets stay unresolved ids.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple, TypeVar

from ..analysis import AnalysisModel
from ..esphome import ESPHomeBinarySensor, ESPHomeDevice, ESPHomeSensor, ESPHomeSwitch
from ..registries.models import Entity
from ..relationships import ObjectType, Relationship, RelationshipRepository
from .models import (
    ESPHomeBinarySensorContext,
    ESPHomeDeviceContext,
    ESPHomeSensorContext,
    ESPHomeSwitchContext,
    _esphome_device_context_key,
)
from .ordering import relationship_sort_key

_Resolved = TypeVar("_Resolved")


class _EntityLinks(NamedTuple):
    """Entity edges already stored for one ESPHome identity."""

    relationships: tuple[Relationship, ...]
    referenced_entities: tuple[Entity, ...]
    unresolved_entity_ids: tuple[str, ...]


def project_esphome_contexts(analysis: AnalysisModel) -> tuple[ESPHomeDeviceContext, ...]:
    """Return one context per ESPHome device, ordered by identity."""
    contexts = tuple(
        _device_context(device, analysis) for device in analysis.yaml_repository.esphome_devices
    )
    return tuple(sorted(contexts, key=_esphome_device_context_key))


def _device_context(device: ESPHomeDevice, analysis: AnalysisModel) -> ESPHomeDeviceContext:
    """Project one device without copying its domain object."""
    links = _links(analysis, ObjectType.ESPHOME_DEVICE, device.name)
    return ESPHomeDeviceContext(
        device=device,
        relationships=links.relationships,
        referenced_entities=links.referenced_entities,
        unresolved_entity_ids=links.unresolved_entity_ids,
        sensors=tuple(_sensor_context(sensor, analysis) for sensor in device.sensors),
        binary_sensors=tuple(
            _binary_sensor_context(sensor, analysis) for sensor in device.binary_sensors
        ),
        switches=tuple(_switch_context(switch, analysis) for switch in device.switches),
    )


def _sensor_context(sensor: ESPHomeSensor, analysis: AnalysisModel) -> ESPHomeSensorContext:
    """Project one sensor and the entities already linked to its identity."""
    links = _links(analysis, ObjectType.ESPHOME_SENSOR, sensor.identity)
    return _sensor_from_links(sensor, links)


def _sensor_from_links(sensor: ESPHomeSensor, links: _EntityLinks) -> ESPHomeSensorContext:
    """Attach already resolved entity links to the original sensor."""
    return ESPHomeSensorContext(
        sensor=sensor,
        relationships=links.relationships,
        referenced_entities=links.referenced_entities,
        unresolved_entity_ids=links.unresolved_entity_ids,
    )


def _binary_sensor_context(
    sensor: ESPHomeBinarySensor,
    analysis: AnalysisModel,
) -> ESPHomeBinarySensorContext:
    """Project one binary sensor and the entities linked to its identity."""
    links = _links(analysis, ObjectType.ESPHOME_BINARY_SENSOR, sensor.identity)
    return _binary_sensor_from_links(sensor, links)


def _binary_sensor_from_links(
    sensor: ESPHomeBinarySensor,
    links: _EntityLinks,
) -> ESPHomeBinarySensorContext:
    """Attach already resolved entity links to the original binary sensor."""
    return ESPHomeBinarySensorContext(
        binary_sensor=sensor,
        relationships=links.relationships,
        referenced_entities=links.referenced_entities,
        unresolved_entity_ids=links.unresolved_entity_ids,
    )


def _switch_context(switch: ESPHomeSwitch, analysis: AnalysisModel) -> ESPHomeSwitchContext:
    """Project one switch and the entities already linked to its identity."""
    links = _links(analysis, ObjectType.ESPHOME_SWITCH, switch.identity)
    return _switch_from_links(switch, links)


def _switch_from_links(switch: ESPHomeSwitch, links: _EntityLinks) -> ESPHomeSwitchContext:
    """Attach already resolved entity links to the original switch."""
    return ESPHomeSwitchContext(
        switch=switch,
        relationships=links.relationships,
        referenced_entities=links.referenced_entities,
        unresolved_entity_ids=links.unresolved_entity_ids,
    )


def _links(
    analysis: AnalysisModel,
    object_type: ObjectType,
    identity: str | None,
) -> _EntityLinks:
    """Return entity edges and resolved entities for one identity."""
    relationships = _relationships(analysis.relationship_repository, object_type, identity)
    entities, missing = _resolve(
        _entity_ids(relationships, object_type, identity),
        analysis.home_assistant_model.get_entity,
    )
    return _EntityLinks(relationships, entities, missing)


def _relationships(
    repository: RelationshipRepository,
    object_type: ObjectType,
    identity: str | None,
) -> tuple[Relationship, ...]:
    """Return unique entity edges already stored for this identity."""
    if identity is None:
        return ()
    combined = (
        *repository.by_source(object_type, identity),
        *repository.by_target(object_type, identity),
    )
    selected = [item for item in set(combined) if _links_entity(item, object_type, identity)]
    return tuple(sorted(selected, key=relationship_sort_key))


def _links_entity(
    relationship: Relationship,
    object_type: ObjectType,
    identity: str,
) -> bool:
    """Return True when the other endpoint is a Home Assistant entity."""
    endpoint = _other_endpoint(relationship, object_type, identity)
    return endpoint[0] is ObjectType.ENTITY


def _other_endpoint(
    relationship: Relationship,
    object_type: ObjectType,
    identity: str,
) -> tuple[ObjectType, str]:
    """Return the endpoint that is not this ESPHome object."""
    if _outgoing(relationship, object_type, identity):
        return (relationship.target_type, relationship.target_id)
    return (relationship.source_type, relationship.source_id)


def _outgoing(relationship: Relationship, object_type: ObjectType, identity: str) -> bool:
    """Return True when this ESPHome object is the relationship source."""
    return relationship.source_type is object_type and relationship.source_id == identity


def _entity_ids(
    relationships: tuple[Relationship, ...],
    object_type: ObjectType,
    identity: str | None,
) -> tuple[str, ...]:
    """Return sorted unique entity ids linked to this identity."""
    if identity is None:
        return ()
    found = {
        _other_endpoint(relationship, object_type, identity)[1] for relationship in relationships
    }
    return tuple(sorted(found))


def _resolve(
    identifiers: tuple[str, ...],
    resolve: Callable[[str], _Resolved | None],
) -> tuple[tuple[_Resolved, ...], tuple[str, ...]]:
    """Split ids into existing objects and unresolved ids, preserving order."""
    resolved: list[_Resolved] = []
    missing: list[str] = []
    for identifier in identifiers:
        item = resolve(identifier)
        if item is None:
            missing.append(identifier)
        else:
            resolved.append(item)
    return tuple(resolved), tuple(missing)
