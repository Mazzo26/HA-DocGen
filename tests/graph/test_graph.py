"""Unit tests for dependency graph models and builder."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ha_docgen.graph import (
    DependencyGraph,
    DependencyGraphBuilder,
    GraphEdge,
    GraphNode,
)
from ha_docgen.relationships import (
    ObjectType,
    RelationshipRepository,
    RelationshipType,
)
from tests.support.builders import (
    build_relationship,
    build_sample_dependency_graph,
)


def test_graph_leaf_models_are_hashable_and_immutable() -> None:
    node = GraphNode(ObjectType.ENTITY, "light.desk")
    edge = GraphEdge(node, node, RelationshipType.REFERENCES)

    assert {node, GraphNode(ObjectType.ENTITY, "light.desk")} == {node}
    assert {edge, GraphEdge(node, node, RelationshipType.REFERENCES)} == {edge}
    with pytest.raises(FrozenInstanceError):
        node.object_id = "light.changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        edge.relationship_type = RelationshipType.USES  # type: ignore[misc]


def test_dependency_graph_indexes_outgoing_incoming_and_contains() -> None:
    graph = build_sample_dependency_graph()
    source = GraphNode(ObjectType.AUTOMATION, "sample_automation")
    target = GraphNode(ObjectType.ENTITY, "light.sample")
    edge = graph.edges[0]

    assert graph.contains(source)
    assert graph.contains(target)
    assert graph.outgoing(source) == (edge,)
    assert graph.incoming(target) == (edge,)
    assert graph.outgoing(target) == ()
    assert not graph.contains(GraphNode(ObjectType.ENTITY, "missing"))


def test_dependency_graph_coerces_collections_without_mutating_input() -> None:
    node = GraphNode(ObjectType.ENTITY, "light.desk")
    nodes = [node]
    edges: list[GraphEdge] = []

    graph = DependencyGraph(nodes=nodes, edges=edges)  # type: ignore[arg-type]
    nodes.append(GraphNode(ObjectType.ENTITY, "light.other"))

    assert graph.nodes == (node,)
    assert graph.edges == ()
    assert isinstance(graph.nodes, tuple)


def test_dependency_graph_is_immutable() -> None:
    graph = build_sample_dependency_graph()

    with pytest.raises(FrozenInstanceError):
        graph.nodes = ()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        graph.edges.append(graph.edges[0])  # type: ignore[attr-defined]


def test_builder_deduplicates_and_sorts_nodes_and_edges() -> None:
    first = build_relationship(source_id="z-last", target_id="light.z")
    second = build_relationship(
        source_id="a-first",
        target_id="office",
        target_type=ObjectType.AREA,
        relationship_type=RelationshipType.USES,
    )
    repository = RelationshipRepository((first, second, first))

    graph = DependencyGraphBuilder().build(repository)

    assert graph.nodes == (
        GraphNode(ObjectType.AREA, "office"),
        GraphNode(ObjectType.AUTOMATION, "a-first"),
        GraphNode(ObjectType.AUTOMATION, "z-last"),
        GraphNode(ObjectType.ENTITY, "light.z"),
    )
    assert graph.edges == (
        GraphEdge(
            GraphNode(ObjectType.AUTOMATION, "a-first"),
            GraphNode(ObjectType.AREA, "office"),
            RelationshipType.USES,
        ),
        GraphEdge(
            GraphNode(ObjectType.AUTOMATION, "z-last"),
            GraphNode(ObjectType.ENTITY, "light.z"),
            RelationshipType.REFERENCES,
        ),
    )


def test_builder_empty_behavior_and_input_immutability() -> None:
    repository = RelationshipRepository()
    before = repository.relationships

    graph = DependencyGraphBuilder().build(repository)

    assert graph == DependencyGraph()
    assert repository.relationships == before


def test_builder_is_stateless_and_repeatable() -> None:
    repository = RelationshipRepository(
        (build_relationship(source_id="one", target_id="light.desk"),)
    )
    builder = DependencyGraphBuilder()

    assert vars(builder) == {}
    assert builder.build(repository) == builder.build(repository)
