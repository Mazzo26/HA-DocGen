"""Central read-only relationship repository.

Holds already-analysed ``Relationship`` objects and provides O(1)
lookups. Performs no analysis, graph construction or validation.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TypeVar

from .models import ObjectType, Relationship, RelationshipType

_IndexKey = TypeVar("_IndexKey")


@dataclass(frozen=True, slots=True)
class RelationshipRepository:
    """Immutable store of relationships with read-only identity lookups.

    Accepts only already-computed ``Relationship`` objects. Deduplicates
    and sorts deterministically during construction. Analyzer-agnostic:
    callers merge analyzer outputs before construction.
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
    _by_relationship: Mapping[RelationshipType, tuple[Relationship, ...]] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _by_between: Mapping[
        tuple[ObjectType, str, ObjectType],
        tuple[Relationship, ...],
    ] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """Deduplicate, sort and build immutable lookup indexes."""
        object.__setattr__(
            self,
            "relationships",
            _deduplicate_and_sort(self.relationships),
        )
        self._build_indexes()

    def _build_indexes(self) -> None:
        """Populate MappingProxyType indexes for identity lookups."""
        by_source, by_target, by_relationship, by_between = _empty_indexes()
        for relationship in self.relationships:
            _index_relationship(
                relationship,
                by_source,
                by_target,
                by_relationship,
                by_between,
            )
        object.__setattr__(self, "_by_source", _freeze_index(by_source))
        object.__setattr__(self, "_by_target", _freeze_index(by_target))
        object.__setattr__(
            self,
            "_by_relationship",
            _freeze_index(by_relationship),
        )
        object.__setattr__(self, "_by_between", _freeze_index(by_between))

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

    def by_relationship(
        self,
        relationship_type: RelationshipType,
    ) -> tuple[Relationship, ...]:
        """Return relationships of the given relationship type."""
        return self._by_relationship.get(relationship_type, ())

    def between(
        self,
        source_type: ObjectType,
        source_id: str,
        target_type: ObjectType,
    ) -> tuple[Relationship, ...]:
        """Return relationships from source identity to any target of type."""
        return self._by_between.get((source_type, source_id, target_type), ())


def _empty_indexes() -> tuple[
    dict[tuple[ObjectType, str], list[Relationship]],
    dict[tuple[ObjectType, str], list[Relationship]],
    dict[RelationshipType, list[Relationship]],
    dict[tuple[ObjectType, str, ObjectType], list[Relationship]],
]:
    """Create empty mutable buckets for all lookup indexes."""
    return defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)


def _index_relationship(
    relationship: Relationship,
    by_source: dict[tuple[ObjectType, str], list[Relationship]],
    by_target: dict[tuple[ObjectType, str], list[Relationship]],
    by_relationship: dict[RelationshipType, list[Relationship]],
    by_between: dict[tuple[ObjectType, str, ObjectType], list[Relationship]],
) -> None:
    """Append *relationship* to every mutable lookup bucket."""
    by_source[(relationship.source_type, relationship.source_id)].append(
        relationship
    )
    by_target[(relationship.target_type, relationship.target_id)].append(
        relationship
    )
    by_relationship[relationship.relationship_type].append(relationship)
    by_between[
        (
            relationship.source_type,
            relationship.source_id,
            relationship.target_type,
        )
    ].append(relationship)


def _relationship_sort_key(
    relationship: Relationship,
) -> tuple[
    ObjectType,
    str,
    RelationshipType,
    ObjectType,
    str,
]:
    """Deterministic sort key for reproducible repository contents."""
    return (
        relationship.source_type,
        relationship.source_id,
        relationship.relationship_type,
        relationship.target_type,
        relationship.target_id,
    )


def _deduplicate_and_sort(
    relationships: Iterable[Relationship],
) -> tuple[Relationship, ...]:
    """Remove duplicate relationships and return a sorted immutable tuple."""
    return tuple(sorted(set(relationships), key=_relationship_sort_key))


def _freeze_index(  # noqa: UP047
    index: dict[_IndexKey, list[Relationship]],
) -> Mapping[_IndexKey, tuple[Relationship, ...]]:
    """Convert a mutable list index into a read-only MappingProxyType."""
    return MappingProxyType({key: tuple(items) for key, items in index.items()})
