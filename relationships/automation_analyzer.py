"""Derive automation relationships from explicit YAML references.

Reads only ``Automation.raw``. Produces immutable ``Relationship``
tuples — no validation, graph, Jinja evaluation or aggregation.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Final

from ..automation.models import Automation
from ._yaml_traversal import (
    KEY_AREA_ID,
    KEY_DEVICE_ID,
    KEY_ENTITY_ID,
    SERVICE_SCENE_TURN_ON,
    SERVICE_SCRIPT_TURN_ON,
    explicit_id_values,
    explicit_service_name,
    iter_mappings,
    target_entity_ids,
)
from .models import ObjectType, Relationship, RelationshipType

_SERVICE_AUTOMATION_TRIGGER: Final[str] = "automation.trigger"
_SERVICE_AUTOMATION_TURN_ON: Final[str] = "automation.turn_on"
_SERVICE_AUTOMATION_TURN_OFF: Final[str] = "automation.turn_off"

_AUTOMATION_SERVICES: Final[frozenset[str]] = frozenset(
    {
        _SERVICE_AUTOMATION_TRIGGER,
        _SERVICE_AUTOMATION_TURN_ON,
        _SERVICE_AUTOMATION_TURN_OFF,
    }
)

_SCRIPT_PREFIX: Final[str] = "script."
_SCENE_PREFIX: Final[str] = "scene."
_AUTOMATION_PREFIX: Final[str] = "automation."


class AutomationRelationshipAnalyzer:
    """Stateless analyzer of explicit automation YAML references.

    Walks ``Automation.raw`` recursively and emits ``REFERENCES``
    edges for entity, device, area, script, scene and automation
    targets. Does not mutate inputs.
    """

    def analyze(
        self,
        automations: tuple[Automation, ...],
    ) -> tuple[Relationship, ...]:
        """Return sorted unique relationships derived from *automations*."""
        found: set[Relationship] = set()
        for automation in automations:
            found.update(self._automation_relationships(automation))
        return tuple(sorted(found, key=_sort_key))

    def _automation_relationships(
        self,
        automation: Automation,
    ) -> set[Relationship]:
        """Build all REFERENCES relationships for one automation."""
        source_id = _source_id(automation)
        if source_id is None:
            return set()
        found: set[Relationship] = set()
        for mapping in iter_mappings(automation.raw):
            found.update(self._from_mapping(source_id, mapping))
        return found

    def _from_mapping(
        self,
        source_id: str,
        mapping: Mapping[object, object],
    ) -> set[Relationship]:
        """Extract identity and service relationships from one mapping."""
        found: set[Relationship] = set()
        found.update(self._identity_refs(source_id, mapping))
        found.update(self._service_refs(source_id, mapping))
        return found

    def _identity_refs(
        self,
        source_id: str,
        mapping: Mapping[object, object],
    ) -> set[Relationship]:
        """Emit ENTITY/DEVICE/AREA refs for explicit id keys."""
        found: set[Relationship] = set()
        for target_id in explicit_id_values(mapping.get(KEY_ENTITY_ID)):
            found.add(
                self._references(source_id, ObjectType.ENTITY, target_id)
            )
        for target_id in explicit_id_values(mapping.get(KEY_DEVICE_ID)):
            found.add(
                self._references(source_id, ObjectType.DEVICE, target_id)
            )
        for target_id in explicit_id_values(mapping.get(KEY_AREA_ID)):
            found.add(
                self._references(source_id, ObjectType.AREA, target_id)
            )
        return found

    def _service_refs(
        self,
        source_id: str,
        mapping: Mapping[object, object],
    ) -> set[Relationship]:
        """Emit SCRIPT/SCENE/AUTOMATION refs for known service calls."""
        service = explicit_service_name(mapping)
        if service is None:
            return set()
        targets = target_entity_ids(mapping)
        if service == SERVICE_SCRIPT_TURN_ON:
            return self._prefixed_refs(
                source_id, ObjectType.SCRIPT, _SCRIPT_PREFIX, targets
            )
        if service == SERVICE_SCENE_TURN_ON:
            return self._prefixed_refs(
                source_id, ObjectType.SCENE, _SCENE_PREFIX, targets
            )
        if service in _AUTOMATION_SERVICES:
            return self._prefixed_refs(
                source_id,
                ObjectType.AUTOMATION,
                _AUTOMATION_PREFIX,
                targets,
            )
        return set()

    def _prefixed_refs(
        self,
        source_id: str,
        target_type: ObjectType,
        prefix: str,
        target_ids: Iterable[str],
    ) -> set[Relationship]:
        """Emit refs for *target_ids* that start with *prefix*."""
        return {
            self._references(source_id, target_type, target_id)
            for target_id in target_ids
            if target_id.startswith(prefix)
        }

    @staticmethod
    def _references(
        source_id: str,
        target_type: ObjectType,
        target_id: str,
    ) -> Relationship:
        """Create an AUTOMATION REFERENCES relationship to *target_type*."""
        return Relationship(
            source_type=ObjectType.AUTOMATION,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            relationship_type=RelationshipType.REFERENCES,
        )


def _source_id(automation: Automation) -> str | None:
    """Return a stable automation identity, or None when absent."""
    if automation.id is not None:
        return automation.id
    return automation.alias


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
