"""Immutable dependency-graph data models.

Pure nodes and edges only — no visualisation, traversal algorithms,
dependency analysis or Home Assistant domain coupling.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from ..relationships.models import ObjectType, RelationshipType


@dataclass(frozen=True, slots=True)
class GraphNode:
    """Immutable identity of one graph node.

    Represented solely by object type and id — no labels or metadata.
    """

    object_type: ObjectType
    object_id: str


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """Immutable directed edge between two graph nodes."""

    source: GraphNode
    target: GraphNode
    relationship_type: RelationshipType


@dataclass(frozen=True, slots=True)
class DependencyGraph:
    """Immutable graph of nodes and edges with read-only lookups.

    Knows only ``GraphNode`` and ``GraphEdge``. Builds MappingProxyType
    indexes in ``__post_init__``. Provides no traversal or analysis.
    """

    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()

    _outgoing: Mapping[GraphNode, tuple[GraphEdge, ...]] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _incoming: Mapping[GraphNode, tuple[GraphEdge, ...]] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _node_index: Mapping[GraphNode, bool] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """Freeze collections and build immutable lookup indexes."""
        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))
        self._build_indexes()

    def _build_indexes(self) -> None:
        """Populate MappingProxyType outgoing, incoming and node indexes."""
        outgoing: dict[GraphNode, list[GraphEdge]] = defaultdict(list)
        incoming: dict[GraphNode, list[GraphEdge]] = defaultdict(list)
        for edge in self.edges:
            outgoing[edge.source].append(edge)
            incoming[edge.target].append(edge)
        object.__setattr__(self, "_outgoing", _freeze_edge_index(outgoing))
        object.__setattr__(self, "_incoming", _freeze_edge_index(incoming))
        object.__setattr__(
            self,
            "_node_index",
            MappingProxyType({node: True for node in self.nodes}),
        )

    def outgoing(self, node: GraphNode) -> tuple[GraphEdge, ...]:
        """Return edges originating from *node*."""
        return self._outgoing.get(node, ())

    def incoming(self, node: GraphNode) -> tuple[GraphEdge, ...]:
        """Return edges targeting *node*."""
        return self._incoming.get(node, ())

    def contains(self, node: GraphNode) -> bool:
        """Return True when *node* is present in the graph."""
        return node in self._node_index


def _freeze_edge_index(
    index: dict[GraphNode, list[GraphEdge]],
) -> Mapping[GraphNode, tuple[GraphEdge, ...]]:
    """Convert a mutable edge list index into MappingProxyType."""
    return MappingProxyType({key: tuple(items) for key, items in index.items()})
