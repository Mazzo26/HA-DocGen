"""Immutable dependency-graph models and builder for HA-DocGen.

``DependencyGraph`` is a pure node/edge representation of a
``RelationshipRepository``. ``DependencyGraphBuilder`` is a
stateless converter. No visualisation, traversal algorithms,
dependency analysis or Home Assistant domain coupling.
"""

from __future__ import annotations

from .builder import DependencyGraphBuilder
from .models import DependencyGraph, GraphEdge, GraphNode

__all__ = [
    "DependencyGraph",
    "DependencyGraphBuilder",
    "GraphEdge",
    "GraphNode",
]
