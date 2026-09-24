"""Unit tests for AnalysisModel."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ha_docgen.analysis import AnalysisModel
from ha_docgen.registries import HomeAssistantModel
from ha_docgen.relationships import RelationshipRepository
from ha_docgen.yaml import YamlRepository
from tests.support import (
    build_relationship,
    build_sample_home_assistant_model,
    build_sample_yaml_repository,
)


def test_construction_stores_the_supplied_aggregates() -> None:
    registry = build_sample_home_assistant_model()
    yaml_repository = build_sample_yaml_repository()
    relationships = RelationshipRepository((build_relationship(),))
    analysis = AnalysisModel(
        home_assistant_model=registry,
        yaml_repository=yaml_repository,
        relationship_repository=relationships,
    )
    assert analysis.home_assistant_model is registry
    assert analysis.yaml_repository is yaml_repository
    assert analysis.relationship_repository is relationships
    assert analysis.home_assistant_model.entities[0] is registry.entities[0]
    assert analysis.yaml_repository.automations[0] is yaml_repository.automations[0]
    assert analysis.relationship_repository.relationships[0] is relationships.relationships[0]


def test_defaults_are_independent_empty_aggregates() -> None:
    first = AnalysisModel()
    second = AnalysisModel()
    assert first.home_assistant_model == HomeAssistantModel()
    assert first.yaml_repository == YamlRepository()
    assert first.yaml_repository.esphome_devices == ()
    assert first.relationship_repository == RelationshipRepository()
    assert first == second
    assert first.home_assistant_model is not second.home_assistant_model
    assert first.yaml_repository is not second.yaml_repository
    assert first.relationship_repository is not second.relationship_repository


def test_analysis_model_is_immutable() -> None:
    analysis = AnalysisModel()
    with pytest.raises(FrozenInstanceError):
        analysis.home_assistant_model = HomeAssistantModel()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        analysis.yaml_repository = YamlRepository()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        analysis.relationship_repository = RelationshipRepository()  # type: ignore[misc]
