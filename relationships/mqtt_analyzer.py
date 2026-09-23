"""Derive MQTT relationships from explicit YAML topic references.

Reads automations, scripts, helpers and package ``mqtt`` sections.
Produces immutable ``Relationship`` tuples — no broker, wildcards,
normalisation, validation, graph or runtime.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from ..automation.models import Automation
from ..helper.models import Helper
from ..packages.models import PackageStructure
from ..script.models import Script
from ._yaml_traversal import (
    KEY_ENTITY_ID,
    explicit_id_values,
    explicit_service_name,
    is_jinja_template,
    iter_mappings,
)
from .models import ObjectType, Relationship, RelationshipType

_SERVICE_MQTT_PUBLISH: Final[str] = "mqtt.publish"
_SECTION_MQTT: Final[str] = "mqtt"
_KEY_TOPIC: Final[str] = "topic"
_KEY_DATA: Final[str] = "data"

_SUBSCRIBE_TOPIC_KEYS: Final[frozenset[str]] = frozenset(
    {
        "state_topic",
        "command_topic",
        "availability_topic",
        "json_attributes_topic",
        "topic",
    }
)


class MQTTRelationshipAnalyzer:
    """Stateless analyzer of explicit MQTT topic references.

    Emits ``PUBLISHES`` from ``mqtt.publish`` service calls and
    ``SUBSCRIBES`` from package ``mqtt`` section topic fields.
    Does not mutate inputs.
    """

    def analyze(
        self,
        automations: tuple[Automation, ...] = (),
        scripts: tuple[Script, ...] = (),
        helpers: tuple[Helper, ...] = (),
        package_structures: tuple[PackageStructure, ...] = (),
    ) -> tuple[Relationship, ...]:
        """Return sorted unique MQTT relationships from the given objects."""
        found: set[Relationship] = set()
        found.update(self._publishes_from_sources(automations, scripts, helpers))
        for structure in package_structures:
            found.update(self._subscribe_from_package(structure))
        return tuple(sorted(found, key=_sort_key))

    def _publishes_from_sources(
        self,
        automations: tuple[Automation, ...],
        scripts: tuple[Script, ...],
        helpers: tuple[Helper, ...],
    ) -> set[Relationship]:
        """Collect PUBLISHES edges from automations, scripts and helpers."""
        found: set[Relationship] = set()
        for automation in automations:
            found.update(self._automation_publishes(automation))
        for script in scripts:
            found.update(self._script_publishes(script))
        for helper in helpers:
            found.update(self._helper_publishes(helper))
        return found

    def _automation_publishes(
        self,
        automation: Automation,
    ) -> set[Relationship]:
        """Emit PUBLISHES relationships for one automation."""
        return self._publish_from_raw(
            ObjectType.AUTOMATION,
            _automation_source_id(automation),
            automation.raw,
        )

    def _script_publishes(self, script: Script) -> set[Relationship]:
        """Emit PUBLISHES relationships for one script."""
        return self._publish_from_raw(
            ObjectType.SCRIPT,
            _script_source_id(script),
            script.raw,
        )

    def _helper_publishes(self, helper: Helper) -> set[Relationship]:
        """Emit PUBLISHES relationships for one helper."""
        return self._publish_from_raw(
            ObjectType.HELPER,
            helper.id,
            helper.raw,
        )

    def _publish_from_raw(
        self,
        source_type: ObjectType,
        source_id: str | None,
        raw: Mapping[str, object],
    ) -> set[Relationship]:
        """Emit PUBLISHES for explicit ``mqtt.publish`` calls in *raw*."""
        if source_id is None:
            return set()
        found: set[Relationship] = set()
        for mapping in iter_mappings(raw):
            topic = _publish_topic(mapping)
            if topic is not None:
                found.add(self._publishes(source_type, source_id, topic))
        return found

    def _subscribe_from_package(
        self,
        structure: PackageStructure,
    ) -> set[Relationship]:
        """Emit SUBSCRIBES for explicit topics under the ``mqtt`` section."""
        section = structure.get_section(_SECTION_MQTT)
        if section is None:
            return set()
        package_id = structure.package.name
        found: set[Relationship] = set()
        for mapping in iter_mappings(section.data):
            found.update(self._subscribe_from_mapping(package_id, mapping))
        return found

    def _subscribe_from_mapping(
        self,
        package_id: str,
        mapping: Mapping[object, object],
    ) -> set[Relationship]:
        """Emit SUBSCRIBES for subscribe-topic keys on one mapping."""
        topics = _subscribe_topics(mapping)
        if not topics:
            return set()
        sources = _subscribe_sources(package_id, mapping)
        return {
            self._subscribes(source_type, source_id, topic)
            for source_type, source_id in sources
            for topic in topics
        }

    @staticmethod
    def _publishes(
        source_type: ObjectType,
        source_id: str,
        topic: str,
    ) -> Relationship:
        """Create a PUBLISHES relationship to an MQTT topic."""
        return Relationship(
            source_type=source_type,
            source_id=source_id,
            target_type=ObjectType.MQTT_TOPIC,
            target_id=topic,
            relationship_type=RelationshipType.PUBLISHES,
        )

    @staticmethod
    def _subscribes(
        source_type: ObjectType,
        source_id: str,
        topic: str,
    ) -> Relationship:
        """Create a SUBSCRIBES relationship to an MQTT topic."""
        return Relationship(
            source_type=source_type,
            source_id=source_id,
            target_type=ObjectType.MQTT_TOPIC,
            target_id=topic,
            relationship_type=RelationshipType.SUBSCRIBES,
        )


def _publish_topic(mapping: Mapping[object, object]) -> str | None:
    """Return the literal publish topic when *mapping* is mqtt.publish."""
    if explicit_service_name(mapping) != _SERVICE_MQTT_PUBLISH:
        return None
    return _explicit_topic_string(mapping)


def _explicit_topic_string(mapping: Mapping[object, object]) -> str | None:
    """Return an explicit topic from ``data.topic`` or ``topic``."""
    data = mapping.get(_KEY_DATA)
    if isinstance(data, Mapping):
        topic = _literal_topic(data.get(_KEY_TOPIC))
        if topic is not None:
            return topic
    return _literal_topic(mapping.get(_KEY_TOPIC))


def _subscribe_topics(mapping: Mapping[object, object]) -> tuple[str, ...]:
    """Return explicit subscribe-topic strings present on *mapping*."""
    return tuple(
        topic
        for key in _SUBSCRIBE_TOPIC_KEYS
        if (topic := _literal_topic(mapping.get(key))) is not None
    )


def _subscribe_sources(
    package_id: str,
    mapping: Mapping[object, object],
) -> tuple[tuple[ObjectType, str], ...]:
    """Return ENTITY sources when ``entity_id`` is present, else PACKAGE."""
    entity_ids = explicit_id_values(mapping.get(KEY_ENTITY_ID))
    if entity_ids:
        return tuple((ObjectType.ENTITY, entity_id) for entity_id in entity_ids)
    return ((ObjectType.PACKAGE, package_id),)


def _literal_topic(value: object) -> str | None:
    """Return a non-empty non-Jinja topic string, or None."""
    if isinstance(value, str) and value and not is_jinja_template(value):
        return value
    return None


def _automation_source_id(automation: Automation) -> str | None:
    """Return a stable automation identity, or None when absent."""
    if automation.id is not None:
        return automation.id
    return automation.alias


def _script_source_id(script: Script) -> str | None:
    """Return a stable script identity, or None when absent."""
    if script.id is not None:
        return script.id
    return script.alias


def _sort_key(
    relationship: Relationship,
) -> tuple[str, str, str, str]:
    """Deterministic sort key for relationship tuples."""
    return (
        relationship.source_id,
        relationship.relationship_type,
        relationship.target_type,
        relationship.target_id,
    )
