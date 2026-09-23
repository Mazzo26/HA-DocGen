"""Project dashboard context from an AnalysisModel.

Maps dashboards already stored on the YAML aggregate. Views stay the
opaque mappings on the dashboard. Resolves entities and automations
only through existing relationships. Missing targets stay unresolved
ids.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from ..analysis import AnalysisModel
from ..automation import Automation
from ..dashboard.models import Dashboard
from ..registries.models import Entity
from ..relationships import ObjectType, Relationship, RelationshipRepository
from .models import DashboardContext, _dashboard_context_key
from .ordering import relationship_sort_key

_Resolved = TypeVar("_Resolved")

_RELATED = (ObjectType.ENTITY, ObjectType.AUTOMATION)


def project_dashboard_contexts(analysis: AnalysisModel) -> tuple[DashboardContext, ...]:
    """Return one context per dashboard, ordered by identity."""
    contexts = tuple(
        _dashboard_context(dashboard, analysis) for dashboard in analysis.yaml_repository.dashboards
    )
    return tuple(sorted(contexts, key=_dashboard_context_key))


def _dashboard_context(dashboard: Dashboard, analysis: AnalysisModel) -> DashboardContext:
    """Project one dashboard without copying its YAML object."""
    identity = _identity(dashboard)
    relationships = _relationships(analysis.relationship_repository, identity)
    return _assemble(dashboard, analysis, identity, relationships)


def _identity(dashboard: Dashboard) -> str | None:
    """Return the relationship key already used for this dashboard.

    Analysed dashboard edges use ``id`` when it is present and otherwise
    ``title``. This reads that same key. It does not search both.
    """
    if dashboard.id is not None:
        return dashboard.id
    return dashboard.title


def _relationships(
    repository: RelationshipRepository,
    identity: str | None,
) -> tuple[Relationship, ...]:
    """Return unique entity and automation edges for this dashboard."""
    if identity is None:
        return ()
    combined = (
        *repository.by_source(ObjectType.DASHBOARD, identity),
        *repository.by_target(ObjectType.DASHBOARD, identity),
    )
    selected = [item for item in combined if _is_related(item, identity)]
    return tuple(sorted(set(selected), key=relationship_sort_key))


def _is_related(relationship: Relationship, identity: str) -> bool:
    """Return True when the other endpoint is an entity or automation."""
    return _other_endpoint(relationship, identity)[0] in _RELATED


def _other_endpoint(
    relationship: Relationship,
    identity: str,
) -> tuple[ObjectType, str]:
    """Return the endpoint that is not this dashboard."""
    if _outgoing(relationship, identity):
        return (relationship.target_type, relationship.target_id)
    return (relationship.source_type, relationship.source_id)


def _outgoing(relationship: Relationship, identity: str) -> bool:
    """Return True when this dashboard is the relationship source."""
    return relationship.source_type is ObjectType.DASHBOARD and relationship.source_id == identity


def _assemble(
    dashboard: Dashboard,
    analysis: AnalysisModel,
    identity: str | None,
    relationships: tuple[Relationship, ...],
) -> DashboardContext:
    """Build one dashboard context from already selected relationships."""
    entities, missing_entities = _resolve(
        _identifiers(relationships, identity, ObjectType.ENTITY),
        analysis.home_assistant_model.get_entity,
    )
    automations, missing_automations = _resolve(
        _identifiers(relationships, identity, ObjectType.AUTOMATION),
        analysis.yaml_repository.get_automation,
    )
    return _context(
        dashboard,
        relationships,
        entities,
        missing_entities,
        automations,
        missing_automations,
    )


def _context(
    dashboard: Dashboard,
    relationships: tuple[Relationship, ...],
    entities: tuple[Entity, ...],
    missing_entities: tuple[str, ...],
    automations: tuple[Automation, ...],
    missing_automations: tuple[str, ...],
) -> DashboardContext:
    """Attach the original views and resolved references."""
    return DashboardContext(
        dashboard=dashboard,
        views=dashboard.views,
        relationships=relationships,
        referenced_entities=entities,
        unresolved_entity_ids=missing_entities,
        related_automations=automations,
        unresolved_automation_ids=missing_automations,
    )


def _identifiers(
    relationships: tuple[Relationship, ...],
    identity: str | None,
    object_type: ObjectType,
) -> tuple[str, ...]:
    """Return sorted unique ids of *object_type* linked to this dashboard."""
    if identity is None:
        return ()
    found = {
        endpoint[1]
        for relationship in relationships
        if (endpoint := _other_endpoint(relationship, identity))[0] is object_type
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
