"""Derive script relationships from explicit YAML references.

Reads only ``Script.raw``. Produces immutable ``Relationship``
tuples — no validation, graph, Jinja evaluation or aggregation.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Final

from ..script.models import Script
from ._yaml_traversal import (
    KEY_ENTITY_ID,
    SERVICE_SCENE_TURN_ON,
    SERVICE_SCRIPT_TURN_ON,
    explicit_id_values,
    explicit_service_name,
    iter_mappings,
    target_entity_ids,
)
from .models import ObjectType, Relationship, RelationshipType

_SCRIPT_PREFIX: Final[str] = "script."
_SCENE_PREFIX: Final[str] = "scene."


class ScriptRelationshipAnalyzer:
    """Stateless analyzer of explicit script YAML references.

    Walks ``Script.raw`` recursively and emits ``REFERENCES`` edges
    for entity, script and scene targets. Does not mutate inputs.
    """

    def analyze(
        self,
        scripts: tuple[Script, ...],
    ) -> tuple[Relationship, ...]:
        """Return sorted unique relationships derived from *scripts*."""
        found: set[Relationship] = set()
        for script in scripts:
            found.update(self._script_relationships(script))
        return tuple(sorted(found, key=_sort_key))

    def _script_relationships(
        self,
        script: Script,
    ) -> set[Relationship]:
        """Build all REFERENCES relationships for one script."""
        source_id = _source_id(script)
        if source_id is None:
            return set()
        found: set[Relationship] = set()
        for mapping in iter_mappings(script.raw):
            found.update(self._from_mapping(source_id, mapping))
        return found

    def _from_mapping(
        self,
        source_id: str,
        mapping: Mapping[object, object],
    ) -> set[Relationship]:
        """Extract entity and service relationships from one mapping."""
        found: set[Relationship] = set()
        found.update(self._entity_refs(source_id, mapping))
        found.update(self._service_refs(source_id, mapping))
        return found

    def _entity_refs(
        self,
        source_id: str,
        mapping: Mapping[object, object],
    ) -> set[Relationship]:
        """Emit ENTITY refs for explicit ``entity_id`` keys."""
        return {
            self._references(source_id, ObjectType.ENTITY, target_id)
            for target_id in explicit_id_values(mapping.get(KEY_ENTITY_ID))
        }

    def _service_refs(
        self,
        source_id: str,
        mapping: Mapping[object, object],
    ) -> set[Relationship]:
        """Emit SCRIPT/SCENE refs for known service calls."""
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
        """Create a SCRIPT REFERENCES relationship to *target_type*."""
        return Relationship(
            source_type=ObjectType.SCRIPT,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            relationship_type=RelationshipType.REFERENCES,
        )


def _source_id(script: Script) -> str | None:
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
