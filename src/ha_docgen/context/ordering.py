"""Deterministic sort keys for context projections.

Matches the relationship repository identity order. Performs no
lookups and no analysis.
"""

from __future__ import annotations

from ..relationships import ObjectType, Relationship, RelationshipType


def relationship_sort_key(
    relationship: Relationship,
) -> tuple[ObjectType, str, RelationshipType, ObjectType, str]:
    """Sort relationships by source, type and target identity."""
    return (
        relationship.source_type,
        relationship.source_id,
        relationship.relationship_type,
        relationship.target_type,
        relationship.target_id,
    )
