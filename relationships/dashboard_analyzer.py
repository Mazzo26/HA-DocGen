"""Derive dashboard relationships from explicit YAML references.

Reads only ``Dashboard.views``. Produces immutable ``Relationship``
tuples — no card-type interpretation, validation, graph or runtime.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from ..dashboard.models import Dashboard
from ._yaml_traversal import (
    KEY_DEVICE,
    KEY_DEVICE_ID,
    KEY_ENTITIES,
    KEY_ENTITY,
    KEY_ENTITY_ID,
    explicit_id_values,
    iter_mappings,
)
from .models import ObjectType, Relationship, RelationshipType

_ENTITY_KEYS: Final[tuple[str, ...]] = (
    KEY_ENTITY,
    KEY_ENTITIES,
    KEY_ENTITY_ID,
)
_DEVICE_KEYS: Final[tuple[str, ...]] = (KEY_DEVICE, KEY_DEVICE_ID)


class DashboardRelationshipAnalyzer:
    """Stateless analyzer of explicit dashboard YAML references.

    Walks ``Dashboard.views`` recursively and emits ``REFERENCES``
    edges for entity and device targets. Detects only explicit
    identity keys — never card types. Does not mutate inputs.
    """

    def analyze(
        self,
        dashboards: tuple[Dashboard, ...],
    ) -> tuple[Relationship, ...]:
        """Return sorted unique relationships derived from *dashboards*."""
        found: set[Relationship] = set()
        for dashboard in dashboards:
            found.update(self._dashboard_relationships(dashboard))
        return tuple(sorted(found, key=_sort_key))

    def _dashboard_relationships(
        self,
        dashboard: Dashboard,
    ) -> set[Relationship]:
        """Build all REFERENCES relationships for one dashboard."""
        source_id = _source_id(dashboard)
        if source_id is None:
            return set()
        found: set[Relationship] = set()
        for view in dashboard.views:
            for mapping in iter_mappings(view):
                found.update(self._from_mapping(source_id, mapping))
        return found

    def _from_mapping(
        self,
        source_id: str,
        mapping: Mapping[object, object],
    ) -> set[Relationship]:
        """Extract entity and device relationships from one mapping."""
        found: set[Relationship] = set()
        found.update(self._entity_refs(source_id, mapping))
        found.update(self._device_refs(source_id, mapping))
        return found

    def _entity_refs(
        self,
        source_id: str,
        mapping: Mapping[object, object],
    ) -> set[Relationship]:
        """Emit ENTITY refs for explicit entity identity keys."""
        return self._refs_for_keys(
            source_id, ObjectType.ENTITY, mapping, _ENTITY_KEYS
        )

    def _device_refs(
        self,
        source_id: str,
        mapping: Mapping[object, object],
    ) -> set[Relationship]:
        """Emit DEVICE refs for explicit device identity keys."""
        return self._refs_for_keys(
            source_id, ObjectType.DEVICE, mapping, _DEVICE_KEYS
        )

    def _refs_for_keys(
        self,
        source_id: str,
        target_type: ObjectType,
        mapping: Mapping[object, object],
        keys: tuple[str, ...],
    ) -> set[Relationship]:
        """Emit refs for explicit non-template values under *keys*."""
        found: set[Relationship] = set()
        for key in keys:
            for target_id in explicit_id_values(mapping.get(key)):
                found.add(self._references(source_id, target_type, target_id))
        return found

    @staticmethod
    def _references(
        source_id: str,
        target_type: ObjectType,
        target_id: str,
    ) -> Relationship:
        """Create a DASHBOARD REFERENCES relationship to *target_type*."""
        return Relationship(
            source_type=ObjectType.DASHBOARD,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            relationship_type=RelationshipType.REFERENCES,
        )


def _source_id(dashboard: Dashboard) -> str | None:
    """Return a stable dashboard identity, or None when absent."""
    if dashboard.id is not None:
        return dashboard.id
    return dashboard.title


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
