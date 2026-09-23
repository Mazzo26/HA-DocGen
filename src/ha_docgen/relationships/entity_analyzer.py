"""Derive entity relationships from Home Assistant registry data.

Reads only explicit entity fields on ``HomeAssistantModel``.
Produces immutable ``Relationship`` tuples — no YAML, graph,
validation or aggregation.
"""

from __future__ import annotations

from ..registries.home_assistant_model import HomeAssistantModel
from ..registries.models import Entity
from .models import ObjectType, Relationship, RelationshipType


class EntityRelationshipAnalyzer:
    """Stateless analyzer of explicit entity registry relationships.

    Emits one ``Relationship`` per non-null device, area or config
    entry link, and one per label id. Does not mutate inputs.
    """

    def analyze(
        self,
        model: HomeAssistantModel,
    ) -> tuple[Relationship, ...]:
        """Return entity relationships derived from *model* registry data."""
        relationships: list[Relationship] = []
        for entity in model.entities:
            relationships.extend(self._entity_relationships(entity))
        return tuple(relationships)

    def _entity_relationships(
        self,
        entity: Entity,
    ) -> tuple[Relationship, ...]:
        """Build all BELONGS_TO relationships for one entity."""
        optional = (
            (ObjectType.DEVICE, entity.device_id),
            (ObjectType.AREA, entity.area_id),
            (ObjectType.CONFIG_ENTRY, entity.config_entry_id),
        )
        items = [
            self._belongs_to(entity.entity_id, target_type, target_id)
            for target_type, target_id in optional
            if target_id is not None
        ]
        items.extend(
            self._belongs_to(entity.entity_id, ObjectType.LABEL, label_id)
            for label_id in entity.labels
        )
        return tuple(items)

    @staticmethod
    def _belongs_to(
        source_id: str,
        target_type: ObjectType,
        target_id: str,
    ) -> Relationship:
        """Create an ENTITY BELONGS_TO relationship to *target_type*."""
        return Relationship(
            source_type=ObjectType.ENTITY,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            relationship_type=RelationshipType.BELONGS_TO,
        )
