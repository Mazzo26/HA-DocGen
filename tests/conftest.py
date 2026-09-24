"""Shared pytest fixtures for HA-DocGen.

Each fixture is opt-in. Nothing here changes tests that do not request it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ha_docgen import ProjectConfig, load_config
from ha_docgen.graph import DependencyGraph
from ha_docgen.project import ProjectTree
from ha_docgen.registries import HomeAssistantModel
from ha_docgen.yaml import YamlRepository
from tests.support.builders import (
    build_sample_dependency_graph,
    build_sample_home_assistant_model,
    build_sample_yaml_repository,
)
from tests.support.filesystem import (
    build_project_tree,
    create_output_directory,
    create_sample_project,
    write_text_files,
)
from tests.support.integration import (
    IntegrationPipeline,
    build_integration_pipeline,
)
from tests.support.project_data import (
    integration_project_files,
    runtime_config_text,
)


@pytest.fixture
def temporary_home_assistant_project(tmp_path: Path) -> Path:
    """Return a minimal Home Assistant project in its own temporary directory."""
    return create_sample_project(tmp_path / "project")


@pytest.fixture
def temporary_output_directory(tmp_path: Path) -> Path:
    """Return an empty temporary output directory."""
    return create_output_directory(tmp_path / "output")


@pytest.fixture
def integration_home_assistant_project(tmp_path: Path) -> Path:
    """Return a representative deterministic Home Assistant project."""
    return write_text_files(tmp_path / "integration", integration_project_files())


@pytest.fixture
def integration_project_config(
    tmp_path: Path,
    integration_home_assistant_project: Path,
) -> ProjectConfig:
    """Return production configuration for the representative project."""
    path = tmp_path / "integration-config.yaml"
    path.write_text(
        runtime_config_text(integration_home_assistant_project),
        encoding="utf-8",
        newline="\n",
    )
    return load_config(path)


@pytest.fixture
def integration_pipeline(
    integration_project_config: ProjectConfig,
) -> IntegrationPipeline:
    """Return complete analysis and generation outputs for the sample project."""
    return build_integration_pipeline(integration_project_config)


@pytest.fixture
def sample_home_assistant_model() -> HomeAssistantModel:
    """Return a deterministic in-memory Home Assistant model."""
    return build_sample_home_assistant_model()


@pytest.fixture
def sample_yaml_repository() -> YamlRepository:
    """Return a deterministic in-memory YAML repository."""
    return build_sample_yaml_repository()


@pytest.fixture
def sample_project_tree(tmp_path: Path) -> ProjectTree:
    """Return a project tree for an isolated copy of the sample project."""
    return build_project_tree(create_sample_project(tmp_path / "tree"))


@pytest.fixture
def sample_dependency_graph() -> DependencyGraph:
    """Return a deterministic two-node dependency graph."""
    return build_sample_dependency_graph()
