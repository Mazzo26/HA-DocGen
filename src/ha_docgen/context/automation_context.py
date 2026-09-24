"""Project automation context from an AnalysisModel.

Maps automations already stored on the YAML aggregate. Resolves
entities, scripts and scenes only through existing relationships.
Missing targets stay unresolved ids.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from ..analysis import AnalysisModel
from ..automation import Automation
from ..registries.models import Entity
from ..relationships import ObjectType, Relationship, RelationshipRepository
from ..scene import Scene
from ..script import Script
from .models import AutomationContext, _automation_context_key
from .ordering import relationship_sort_key

_Resolved = TypeVar("_Resolved")

_RELATED = (ObjectType.ENTITY, ObjectType.SCRIPT, ObjectType.SCENE)


def project_automation_contexts(analysis: AnalysisModel) -> tuple[AutomationContext, ...]:
    """Return one context per automation, ordered by identity."""
    contexts = tuple(
        _automation_context(automation, analysis)
        for automation in analysis.yaml_repository.automations
    )
    return tuple(sorted(contexts, key=_automation_context_key))


def _automation_context(automation: Automation, analysis: AnalysisModel) -> AutomationContext:
    """Project one automation without copying its YAML object."""
    identity = _identity(automation)
    relationships = _relationships(analysis.relationship_repository, identity)
    return _assemble(automation, analysis, identity, relationships)


def _identity(automation: Automation) -> str | None:
    """Return the relationship key already used for this automation.

    Analyzed automation edges use ``id`` when it is present and
    otherwise ``alias``. This reads that same key. It does not search
    both and it does not parse YAML.
    """
    if automation.id is not None:
        return automation.id
    return automation.alias


def _relationships(
    repository: RelationshipRepository,
    identity: str | None,
) -> tuple[Relationship, ...]:
    """Return unique entity, script and scene edges for this automation."""
    if identity is None:
        return ()
    combined = (
        *repository.by_source(ObjectType.AUTOMATION, identity),
        *repository.by_target(ObjectType.AUTOMATION, identity),
    )
    selected = [item for item in combined if _is_related(item, identity)]
    return tuple(sorted(set(selected), key=relationship_sort_key))


def _is_related(relationship: Relationship, identity: str) -> bool:
    """Return True when the other endpoint is an entity, script or scene."""
    return _other_endpoint(relationship, identity)[0] in _RELATED


def _other_endpoint(
    relationship: Relationship,
    identity: str,
) -> tuple[ObjectType, str]:
    """Return the endpoint that is not this automation.

    Callers pass edges from this automation's source or target index.
    """
    if _outgoing(relationship, identity):
        return (relationship.target_type, relationship.target_id)
    return (relationship.source_type, relationship.source_id)


def _outgoing(relationship: Relationship, identity: str) -> bool:
    """Return True when this automation is the relationship source."""
    return (
        relationship.source_type is ObjectType.AUTOMATION and relationship.source_id == identity
    )


def _assemble(
    automation: Automation,
    analysis: AnalysisModel,
    identity: str | None,
    relationships: tuple[Relationship, ...],
) -> AutomationContext:
    """Build one automation context from already selected relationships."""
    entities, missing_entities = _resolve(
        _identifiers(relationships, identity, ObjectType.ENTITY),
        analysis.home_assistant_model.get_entity,
    )
    scripts, missing_scripts = _resolve(
        _identifiers(relationships, identity, ObjectType.SCRIPT),
        analysis.yaml_repository.get_script,
    )
    scenes, missing_scenes = _resolve(
        _identifiers(relationships, identity, ObjectType.SCENE),
        analysis.yaml_repository.get_scene,
    )
    return _context(
        automation,
        relationships,
        entities,
        missing_entities,
        scripts,
        missing_scripts,
        scenes,
        missing_scenes,
    )


def _context(
    automation: Automation,
    relationships: tuple[Relationship, ...],
    entities: tuple[Entity, ...],
    missing_entities: tuple[str, ...],
    scripts: tuple[Script, ...],
    missing_scripts: tuple[str, ...],
    scenes: tuple[Scene, ...],
    missing_scenes: tuple[str, ...],
) -> AutomationContext:
    """Attach resolved objects and unresolved ids to the original automation."""
    return AutomationContext(
        automation=automation,
        package=automation.package,
        relationships=relationships,
        referenced_entities=entities,
        unresolved_entity_ids=missing_entities,
        related_scripts=scripts,
        unresolved_script_ids=missing_scripts,
        related_scenes=scenes,
        unresolved_scene_ids=missing_scenes,
    )


def _identifiers(
    relationships: tuple[Relationship, ...],
    identity: str | None,
    object_type: ObjectType,
) -> tuple[str, ...]:
    """Return sorted unique ids of *object_type* linked to this automation."""
    if identity is None:
        return ()
    found: set[str] = set()
    for relationship in relationships:
        endpoint = _other_endpoint(relationship, identity)
        if endpoint is not None and endpoint[0] is object_type:
            found.add(endpoint[1])
    return tuple(sorted(found))


def _resolve(  # noqa: UP047
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
