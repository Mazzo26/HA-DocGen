"""Derive device relationships from Home Assistant registry data.

Reads only explicit device fields on ``HomeAssistantModel``.
Produces immutable ``Relationship`` tuples — no YAML, graph,
validation or aggregation.
"""

from __future__ import annotations

from ..registries.home_assistant_model import HomeAssistantModel
from ..registries.models import Device
from .models import ObjectType, Relationship, RelationshipType


class DeviceRelationshipAnalyzer:
    """Stateless analyzer of explicit device registry relationships.

    Emits one ``Relationship`` per non-null area link, one per config
    entry id, and one per label id. Does not mutate inputs.
    """

    def analyze(
        self,
        model: HomeAssistantModel,
    ) -> tuple[Relationship, ...]:
        """Return device relationships derived from *model* registry data."""
        relationships: list[Relationship] = []
        for device in model.devices:
            relationships.extend(self._device_relationships(device))
        return tuple(relationships)

    def _device_relationships(
        self,
        device: Device,
    ) -> tuple[Relationship, ...]:
        """Build all BELONGS_TO relationships for one device."""
        items: list[Relationship] = []
        if device.area_id is not None:
            items.append(
                self._belongs_to(device.registry_id, ObjectType.AREA, device.area_id)
            )
        items.extend(
            self._belongs_to(
                device.registry_id,
                ObjectType.CONFIG_ENTRY,
                entry_id,
            )
            for entry_id in device.config_entries
        )
        items.extend(
            self._belongs_to(device.registry_id, ObjectType.LABEL, label_id)
            for label_id in device.labels
        )
        return tuple(items)

    @staticmethod
    def _belongs_to(
        source_id: str,
        target_type: ObjectType,
        target_id: str,
    ) -> Relationship:
        """Create a DEVICE BELONGS_TO relationship to *target_type*."""
        return Relationship(
            source_type=ObjectType.DEVICE,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            relationship_type=RelationshipType.BELONGS_TO,
        )
