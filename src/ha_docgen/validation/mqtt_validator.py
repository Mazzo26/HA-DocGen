"""Validate MQTT definitions against explicit structural rules.

Produces immutable ``ValidationResult`` tuples only. Consumes already
parsed package MQTT sections — no YAML loading, broker access, runtime
inspection or CLI coupling.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from ..packages.models import PackageStructure
from ..relationships.models import ObjectType
from ..yaml.repository import YamlRepository
from .models import (
    ValidationCollection,
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)

_SECTION_MQTT: Final[str] = "mqtt"
_KEY_PLATFORM: Final[str] = "platform"
_KEY_UNIQUE_ID: Final[str] = "unique_id"
_KEY_OBJECT_ID: Final[str] = "object_id"
_KEY_NAME: Final[str] = "name"
_KEY_TOPIC: Final[str] = "topic"
_KEY_AVAILABILITY: Final[str] = "availability"
_TOPIC_SUFFIX: Final[str] = "_topic"
_JINJA_MARKERS: Final[tuple[str, ...]] = ("{{", "{%")
_SHARED_TOPIC_FIELDS: Final[frozenset[str]] = frozenset({"availability_topic"})
_UNIQUE_TOPIC_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "command_topic",
        "state_topic",
        "topic",
        "url_topic",
        "image_topic",
    }
)
_MQTT_PLATFORMS: Final[frozenset[str]] = frozenset(
    {
        "alarm_control_panel",
        "binary_sensor",
        "button",
        "camera",
        "climate",
        "cover",
        "device_tracker",
        "device_trigger",
        "event",
        "fan",
        "humidifier",
        "image",
        "lawn_mower",
        "light",
        "lock",
        "notify",
        "number",
        "scene",
        "select",
        "sensor",
        "siren",
        "switch",
        "tag",
        "text",
        "update",
        "vacuum",
        "valve",
        "water_heater",
        "weather",
    }
)
_REQUIRED_TOPICS: Final[dict[str, frozenset[str]]] = {
    "alarm_control_panel": frozenset({"command_topic"}),
    "binary_sensor": frozenset({"state_topic"}),
    "button": frozenset({"command_topic"}),
    "camera": frozenset({"topic"}),
    "device_tracker": frozenset({"state_topic"}),
    "device_trigger": frozenset({"topic"}),
    "event": frozenset({"state_topic"}),
    "fan": frozenset({"command_topic"}),
    "humidifier": frozenset({"command_topic"}),
    "lock": frozenset({"command_topic"}),
    "light": frozenset({"command_topic"}),
    "notify": frozenset({"command_topic"}),
    "number": frozenset({"command_topic"}),
    "scene": frozenset({"command_topic"}),
    "select": frozenset({"command_topic"}),
    "sensor": frozenset({"state_topic"}),
    "siren": frozenset({"command_topic"}),
    "switch": frozenset({"command_topic"}),
    "tag": frozenset({"topic"}),
    "text": frozenset({"command_topic"}),
    "update": frozenset({"state_topic"}),
    "vacuum": frozenset({"command_topic"}),
    "valve": frozenset({"command_topic"}),
}
_IMAGE_TOPIC_FIELDS: Final[frozenset[str]] = frozenset({"url_topic", "image_topic"})


@dataclass(frozen=True, slots=True)
class _MqttEntity:
    """One already-parsed MQTT entity mapping with extracted topic fields."""

    identity: str
    platform: str
    unique_id: str
    discovery_id: str
    location: str
    topics: tuple[tuple[str, str], ...]


class MQTTValidator:
    """Stateless validator for MQTT structural consistency.

    Accepts an already-populated ``YamlRepository``. Emits findings
    only; does not parse YAML, connect to a broker or inspect runtime.
    """

    def validate(self, repository: YamlRepository) -> tuple[ValidationResult, ...]:
        """Return sorted MQTT validation findings for *repository*."""
        return _validate(repository.package_structures)


def _validate(
    structures: tuple[PackageStructure, ...],
) -> tuple[ValidationResult, ...]:
    """Run all MQTT checks against parsed package structures."""
    entities = _collect_entities(structures)
    results: list[ValidationResult] = []
    for entity in entities:
        results.extend(_validate_entity(entity))
    results.extend(_duplicate_topics(entities))
    results.extend(_duplicate_unique_ids(entities))
    results.extend(_duplicate_discovery_ids(entities))
    return ValidationCollection(results=tuple(results)).results


def _validate_entity(entity: _MqttEntity) -> tuple[ValidationResult, ...]:
    """Run per-entity topic presence, emptiness and format checks."""
    results: list[ValidationResult] = []
    results.extend(_validate_required_topics(entity))
    results.extend(_validate_topic_values(entity))
    return tuple(results)


def _collect_entities(
    structures: tuple[PackageStructure, ...],
) -> tuple[_MqttEntity, ...]:
    """Collect MQTT entities from parsed ``mqtt`` package sections."""
    found: list[_MqttEntity] = []
    for structure in structures:
        section = structure.get_section(_SECTION_MQTT)
        if section is None:
            continue
        found.extend(_entities_from_section(section.data, structure.package.path))
    return tuple(found)


def _entities_from_section(data: object, path: Path) -> tuple[_MqttEntity, ...]:
    """Return MQTT entities declared in one parsed ``mqtt`` section."""
    if isinstance(data, Mapping):
        return _entities_from_platform_mapping(data, path)
    if not isinstance(data, list):
        return ()
    return tuple(
        entity
        for item in data
        if isinstance(item, Mapping)
        for entity in _legacy_entity(item, path)
    )


def _entities_from_platform_mapping(
    data: Mapping[object, object],
    path: Path,
) -> tuple[_MqttEntity, ...]:
    """Return entities from a platform-keyed MQTT mapping."""
    found: list[_MqttEntity] = []
    for key, value in data.items():
        if not isinstance(key, str) or key not in _MQTT_PLATFORMS:
            continue
        found.extend(_entities_from_platform(key, value, path))
    return tuple(found)


def _entities_from_platform(
    platform: str,
    value: object,
    path: Path,
) -> tuple[_MqttEntity, ...]:
    """Return entities declared under one MQTT platform key."""
    if isinstance(value, Mapping):
        return (_make_entity(platform, value, path),)
    if not isinstance(value, list):
        return ()
    return tuple(
        _make_entity(platform, item, path)
        for item in value
        if isinstance(item, Mapping)
    )


def _legacy_entity(
    mapping: Mapping[object, object],
    path: Path,
) -> tuple[_MqttEntity, ...]:
    """Return an entity from a legacy ``platform`` mapping, if valid."""
    platform = mapping.get(_KEY_PLATFORM)
    if not isinstance(platform, str) or platform not in _MQTT_PLATFORMS:
        return ()
    return (_make_entity(platform, mapping, path),)


def _make_entity(
    platform: str,
    mapping: Mapping[object, object],
    path: Path,
) -> _MqttEntity:
    """Build an ``_MqttEntity`` from one parsed entity mapping."""
    unique_id = _string_field(mapping, _KEY_UNIQUE_ID)
    discovery_id = _string_field(mapping, _KEY_OBJECT_ID)
    name = _string_field(mapping, _KEY_NAME)
    identity = unique_id or discovery_id or name or platform
    return _MqttEntity(
        identity=identity,
        platform=platform,
        unique_id=unique_id,
        discovery_id=discovery_id,
        location=_path_location(path),
        topics=_topics_from_mapping(mapping),
    )


def _topics_from_mapping(
    mapping: Mapping[object, object],
) -> tuple[tuple[str, str], ...]:
    """Extract topic field/value pairs from one entity mapping."""
    found: list[tuple[str, str]] = []
    for key, value in mapping.items():
        if not isinstance(key, str):
            continue
        if key == _KEY_AVAILABILITY:
            found.extend(_availability_topics(value))
            continue
        if _is_topic_key(key) and isinstance(value, str):
            found.append((key, value))
    return tuple(found)


def _availability_topics(value: object) -> tuple[tuple[str, str], ...]:
    """Extract availability topics from a mapping, list or string."""
    if isinstance(value, str):
        return (("availability_topic", value),)
    if isinstance(value, Mapping):
        topic = value.get(_KEY_TOPIC)
        if isinstance(topic, str):
            return (("availability_topic", topic),)
        return ()
    if not isinstance(value, list):
        return ()
    return tuple(
        ("availability_topic", topic)
        for item in value
        for topic in _availability_item_topic(item)
    )


def _availability_item_topic(item: object) -> tuple[str, ...]:
    """Return the topic string from one availability list item."""
    if isinstance(item, str):
        return (item,)
    if isinstance(item, Mapping):
        topic = item.get(_KEY_TOPIC)
        if isinstance(topic, str):
            return (topic,)
    return ()


def _validate_required_topics(entity: _MqttEntity) -> tuple[ValidationResult, ...]:
    """Flag MQTT platforms that omit a mandatory topic field."""
    present = _non_empty_fields(entity)
    missing = _missing_required_fields(entity.platform, present)
    return tuple(
        _finding(
            entity.identity,
            ValidationType.INVALID_CONFIGURATION,
            ValidationSeverity.ERROR,
            f"MQTT entity is missing required {field}.",
        )
        for field in missing
    )


def _missing_required_fields(
    platform: str,
    present: frozenset[str],
) -> tuple[str, ...]:
    """Return sorted required topic fields that are absent or empty."""
    if platform == "image":
        if present & _IMAGE_TOPIC_FIELDS:
            return ()
        return ("url_topic",)
    required = _REQUIRED_TOPICS.get(platform, frozenset())
    return tuple(sorted(field for field in required if field not in present))


def _validate_topic_values(entity: _MqttEntity) -> tuple[ValidationResult, ...]:
    """Flag empty and obviously invalid topic strings."""
    results: list[ValidationResult] = []
    for field, topic in entity.topics:
        if _is_template(topic):
            continue
        results.extend(_topic_value_findings(entity.identity, field, topic))
    return tuple(results)


def _topic_value_findings(
    identity: str,
    field: str,
    topic: str,
) -> tuple[ValidationResult, ...]:
    """Return emptiness and format findings for one topic string."""
    if topic.strip() == "":
        return (
            _finding(
                identity,
                ValidationType.INVALID_CONFIGURATION,
                ValidationSeverity.ERROR,
                f"MQTT {field} is empty.",
            ),
        )
    if not _is_invalid_topic_format(topic):
        return ()
    return (
        _finding(
            identity,
            ValidationType.INVALID_CONFIGURATION,
            ValidationSeverity.ERROR,
            f"MQTT {field} has invalid format.",
        ),
    )


def _duplicate_topics(
    entities: tuple[_MqttEntity, ...],
) -> tuple[ValidationResult, ...]:
    """Flag unique-required topics that appear on more than one entity."""
    grouped: dict[tuple[str, str], list[_MqttEntity]] = defaultdict(list)
    for entity in entities:
        for field, topic in entity.topics:
            if field in _SHARED_TOPIC_FIELDS or field not in _UNIQUE_TOPIC_FIELDS:
                continue
            if topic.strip() == "" or _is_template(topic):
                continue
            grouped[(field, topic)].append(entity)
    return tuple(
        _duplicate_topic_finding(field, topic, matches)
        for (field, topic), matches in sorted(grouped.items())
        if len(matches) > 1
    )


def _duplicate_topic_finding(
    field: str,
    topic: str,
    matches: Sequence[_MqttEntity],
) -> ValidationResult:
    """Build one duplicate-topic finding for *matches*."""
    identities = tuple(sorted({entity.identity for entity in matches}))
    locations = tuple(sorted({entity.location for entity in matches}))
    return _finding(
        topic,
        ValidationType.DUPLICATE,
        ValidationSeverity.ERROR,
        (
            f"Duplicate MQTT {field} '{topic}'. "
            f"Object IDs: {', '.join(identities)}. "
            f"Locations: {', '.join(locations)}."
        ),
    )


def _duplicate_unique_ids(
    entities: tuple[_MqttEntity, ...],
) -> tuple[ValidationResult, ...]:
    """Flag MQTT unique_id values that appear more than once."""
    return _duplicate_identifier_findings(
        (
            (entity.unique_id, entity.location)
            for entity in entities
            if entity.unique_id != ""
        ),
        "unique_id",
    )


def _duplicate_discovery_ids(
    entities: tuple[_MqttEntity, ...],
) -> tuple[ValidationResult, ...]:
    """Flag duplicate discovery identifiers when object_id is present."""
    return _duplicate_identifier_findings(
        (
            (entity.discovery_id, entity.location)
            for entity in entities
            if entity.discovery_id != ""
        ),
        "discovery identifier",
    )


def _duplicate_identifier_findings(
    items: Iterable[tuple[str, str]],
    label: str,
) -> tuple[ValidationResult, ...]:
    """Build duplicate findings for identifier/location pairs."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for object_id, location in items:
        grouped[object_id].append(location)
    return tuple(
        _finding(
            object_id,
            ValidationType.DUPLICATE,
            ValidationSeverity.ERROR,
            _duplicate_identifier_message(label, locations),
        )
        for object_id, locations in sorted(grouped.items())
        if len(locations) > 1
    )


def _duplicate_identifier_message(label: str, locations: Sequence[str]) -> str:
    """Return a duplicate-identifier message with file locations."""
    available = tuple(sorted(set(locations)))
    return f"Duplicate MQTT {label}. Locations: {', '.join(available)}."


def _finding(
    object_id: str,
    validation_type: ValidationType,
    severity: ValidationSeverity,
    message: str,
) -> ValidationResult:
    """Build an MQTT ``ValidationResult``."""
    return ValidationResult(
        object_type=ObjectType.MQTT_TOPIC,
        object_id=object_id,
        validation_type=validation_type,
        severity=severity,
        message=message,
    )


def _non_empty_fields(entity: _MqttEntity) -> frozenset[str]:
    """Return topic fields whose values are not empty or whitespace."""
    return frozenset(
        field for field, topic in entity.topics if topic.strip() != ""
    )


def _string_field(mapping: Mapping[object, object], key: str) -> str:
    """Return a non-empty string field, or an empty skip marker."""
    value = mapping.get(key)
    if isinstance(value, str) and value != "":
        return value
    return ""


def _is_topic_key(key: str) -> bool:
    """Return True when *key* is a topic field name."""
    return key == _KEY_TOPIC or key.endswith(_TOPIC_SUFFIX)


def _is_invalid_topic_format(topic: str) -> bool:
    """Return True for leading/trailing spaces or empty path segments."""
    if topic != topic.strip():
        return True
    return any(segment == "" for segment in topic.split("/"))


def _is_template(value: str) -> bool:
    """Return True when *value* contains Jinja markers."""
    return any(marker in value for marker in _JINJA_MARKERS)


def _path_location(path: Path) -> str:
    """Return a deterministic POSIX path string for findings."""
    return path.as_posix()
