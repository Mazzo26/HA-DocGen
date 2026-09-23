"""Stateless builder from RelationshipRepository to DependencyGraph."""

from __future__ import annotations

from ..relationships.models import ObjectType, Relationship, RelationshipType
from ..relationships.repository import RelationshipRepository
from .models import DependencyGraph, GraphEdge, GraphNode


class DependencyGraphBuilder:
    """Build an immutable DependencyGraph from a RelationshipRepository.

    Fully stateless: no instance state, no mutation of the repository,
    no analysis and no visualisation.
    """

    def build(self, repository: RelationshipRepository) -> DependencyGraph:
        """Return a deduplicated, deterministically sorted DependencyGraph."""
        nodes: set[GraphNode] = set()
        edges: set[GraphEdge] = set()
        for relationship in repository.relationships:
            source, target, edge = _nodes_and_edge(relationship)
            nodes.add(source)
            nodes.add(target)
            edges.add(edge)
        return DependencyGraph(
            nodes=tuple(sorted(nodes, key=_node_sort_key)),
            edges=tuple(sorted(edges, key=_edge_sort_key)),
        )


def _nodes_and_edge(
    relationship: Relationship,
) -> tuple[GraphNode, GraphNode, GraphEdge]:
    """Map one Relationship to source node, target node and edge."""
    source = GraphNode(relationship.source_type, relationship.source_id)
    target = GraphNode(relationship.target_type, relationship.target_id)
    edge = GraphEdge(source, target, relationship.relationship_type)
    return source, target, edge


def _node_sort_key(node: GraphNode) -> tuple[ObjectType, str]:
    """Deterministic sort key for graph nodes."""
    return (node.object_type, node.object_id)


def _edge_sort_key(
    edge: GraphEdge,
) -> tuple[ObjectType, str, RelationshipType, ObjectType, str]:
    """Deterministic sort key for graph edges."""
    return (
        edge.source.object_type,
        edge.source.object_id,
        edge.relationship_type,
        edge.target.object_type,
        edge.target.object_id,
    )
