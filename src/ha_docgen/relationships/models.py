"""Immutable relationship data models.

Pure identity only — no object references, graph construction,
filtering, analysis or Home Assistant coupling.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType


class ObjectType(StrEnum):
    """Canonical object kinds that may appear in a relationship."""

    ENTITY = "entity"
    DEVICE = "device"
    AREA = "area"
    LABEL = "label"
    FLOOR = "floor"
    CONFIG_ENTRY = "config_entry"
    PACKAGE = "package"
    AUTOMATION = "automation"
    SCRIPT = "script"
    SCENE = "scene"
    HELPER = "helper"
    DASHBOARD = "dashboard"
    BLUEPRINT = "blueprint"
    TEMPLATE = "template"
    MQTT_TOPIC = "mqtt_topic"
    ESPHOME_DEVICE = "esphome_device"
    ESPHOME_SENSOR = "esphome_sensor"
    ESPHOME_BINARY_SENSOR = "esphome_binary_sensor"
    ESPHOME_SWITCH = "esphome_switch"


class RelationshipType(StrEnum):
    """Canonical directed relationship kinds between objects."""

    REFERENCES = "references"
    CONTAINS = "contains"
    BELONGS_TO = "belongs_to"
    USES = "uses"
    PUBLISHES = "publishes"
    SUBSCRIBES = "subscribes"


@dataclass(frozen=True, slots=True)
class Relationship:
    """Immutable identity of one directed relationship.

    Holds source and target type/id pairs plus a relationship type.
    Contains no object references and no graph semantics.
    """

    source_type: ObjectType
    source_id: str
    target_type: ObjectType
    target_id: str
    relationship_type: RelationshipType


@dataclass(frozen=True, slots=True)
class RelationshipCollection:
    """Immutable collection of relationships with O(1) identity lookups.

    Builds read-only source and target indexes in ``__post_init__``.
    Provides no filtering, graph traversal or analysis.
    """

    relationships: tuple[Relationship, ...] = ()
    _by_source: Mapping[tuple[ObjectType, str], tuple[Relationship, ...]] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _by_target: Mapping[tuple[ObjectType, str], tuple[Relationship, ...]] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """Freeze the collection and build immutable lookup indexes."""
        object.__setattr__(self, "relationships", tuple(self.relationships))
        self._build_indexes()

    def _build_indexes(self) -> None:
        """Populate MappingProxyType source and target indexes."""
        by_source: dict[tuple[ObjectType, str], list[Relationship]] = defaultdict(
            list
        )
        by_target: dict[tuple[ObjectType, str], list[Relationship]] = defaultdict(
            list
        )
        for relationship in self.relationships:
            by_source[
                (relationship.source_type, relationship.source_id)
            ].append(relationship)
            by_target[
                (relationship.target_type, relationship.target_id)
            ].append(relationship)
        object.__setattr__(
            self,
            "_by_source",
            MappingProxyType(
                {key: tuple(items) for key, items in by_source.items()}
            ),
        )
        object.__setattr__(
            self,
            "_by_target",
            MappingProxyType(
                {key: tuple(items) for key, items in by_target.items()}
            ),
        )

    def by_source(
        self,
        source_type: ObjectType,
        source_id: str,
    ) -> tuple[Relationship, ...]:
        """Return relationships originating from the given identity."""
        return self._by_source.get((source_type, source_id), ())

    def by_target(
        self,
        target_type: ObjectType,
        target_id: str,
    ) -> tuple[Relationship, ...]:
        """Return relationships targeting the given identity."""
        return self._by_target.get((target_type, target_id), ())
