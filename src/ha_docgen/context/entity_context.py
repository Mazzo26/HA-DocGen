"""Project entity context from an AnalysisModel.

Maps registry entities and relationships already stored for each
entity id. Resolves package membership only when a relationship names
a package that already exists. Does not discover relationships.
"""

from __future__ import annotations

from ..analysis import AnalysisModel
from ..packages import Package
from ..registries.models import Entity
from ..relationships import ObjectType, Relationship, RelationshipRepository
from ..yaml import YamlRepository
from .models import EntityContext, _entity_context_key
from .ordering import relationship_sort_key


def project_entity_contexts(analysis: AnalysisModel) -> tuple[EntityContext, ...]:
    """Return one context per registry entity, ordered by identity."""
    contexts = tuple(
        _entity_context(entity, analysis) for entity in analysis.home_assistant_model.entities
    )
    return tuple(sorted(contexts, key=_entity_context_key))


def _entity_context(entity: Entity, analysis: AnalysisModel) -> EntityContext:
    """Project one entity without copying the registry object."""
    relationships = _relationships(analysis.relationship_repository, entity.entity_id)
    return EntityContext(
        entity=entity,
        relationships=relationships,
        packages=_packages(analysis.yaml_repository, relationships, entity.entity_id),
    )


def _relationships(
    repository: RelationshipRepository,
    entity_id: str,
) -> tuple[Relationship, ...]:
    """Return unique edges that already name this entity id."""
    combined = (
        *repository.by_source(ObjectType.ENTITY, entity_id),
        *repository.by_target(ObjectType.ENTITY, entity_id),
    )
    return tuple(sorted(set(combined), key=relationship_sort_key))


def _packages(
    repository: YamlRepository,
    relationships: tuple[Relationship, ...],
    entity_id: str,
) -> tuple[Package, ...]:
    """Return packages already named by this entity's relationships."""
    packages = [
        package
        for package_id in _package_ids(relationships, entity_id)
        if (package := repository.get_package(package_id)) is not None
    ]
    return tuple(packages)


def _package_ids(
    relationships: tuple[Relationship, ...],
    entity_id: str,
) -> tuple[str, ...]:
    """Return sorted package ids linked to this entity."""
    identifiers = {
        package_id
        for relationship in relationships
        if (package_id := _package_id(relationship, entity_id)) is not None
    }
    return tuple(sorted(identifiers))


def _package_id(relationship: Relationship, entity_id: str) -> str | None:
    """Return the package id when this edge links the entity to a package."""
    if _entity_to_package(relationship, entity_id):
        return relationship.target_id
    if _package_to_entity(relationship, entity_id):
        return relationship.source_id
    return None


def _entity_to_package(relationship: Relationship, entity_id: str) -> bool:
    """Return True when the entity is the source and the target is a package."""
    return (
        relationship.source_type is ObjectType.ENTITY
        and relationship.source_id == entity_id
        and relationship.target_type is ObjectType.PACKAGE
    )


def _package_to_entity(relationship: Relationship, entity_id: str) -> bool:
    """Return True when a package is the source and the entity is the target."""
    return (
        relationship.source_type is ObjectType.PACKAGE
        and relationship.target_type is ObjectType.ENTITY
        and relationship.target_id == entity_id
    )

