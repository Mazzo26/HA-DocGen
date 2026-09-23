"""Tests for HA-DocGen runtime configuration validators."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest

from tools.ha_docgen import configuration_validation as validation
from tools.ha_docgen.config import ProjectConfig
from tools.ha_docgen.configuration_validation import (
    ConfigurationValidator,
    EnvironmentValidator,
    OutputValidator,
    PathValidator,
    validate_runtime_configuration,
)


def _config(root: Path) -> ProjectConfig:
    """Return a complete project configuration rooted below ``root``."""
    return ProjectConfig(
        project_name="Test",
        version="1.0",
        root=root,
        configuration=root / "configuration.yaml",
        packages=root / "packages",
        dashboards=root / "dashboards",
        esphome=root / "esphome",
        docs=root / "docs",
        themes=root / "themes",
        custom_components=root / "custom_components",
        www=root / "www",
        storage=root / ".storage",
        entity_registry=root / ".storage/core.entity_registry",
        device_registry=root / ".storage/core.device_registry",
        area_registry=root / ".storage/core.area_registry",
        floor_registry=root / ".storage/core.floor_registry",
        config_entries=root / ".storage/core.config_entries",
        readme=root / "README.md",
        ai_context=root / "AI_CONTEXT.md",
        entity_map=root / "ENTITY_MAP.md",
        output_docs=root / "docs/generated",
        cache=root / ".cache/ha-docgen.json",
    )


def test_configuration_validator_accepts_complete_values(tmp_path: Path) -> None:
    """Required model values pass semantic validation."""
    assert ConfigurationValidator().validate(_config(tmp_path)) == ()


def test_configuration_validator_sorts_and_deduplicates_errors(tmp_path: Path) -> None:
    """Semantic errors have deterministic immutable output."""
    config = replace(_config(tmp_path), project_name=" ", version="")

    assert ConfigurationValidator().validate(config) == (
        "Project name must not be empty.",
        "Project version must not be empty.",
    )


def test_path_validator_requires_root_and_configuration_file(tmp_path: Path) -> None:
    """Execution inputs must exist before scanning starts."""
    config = _config(tmp_path / "missing")

    assert PathValidator().validate(config) == (
        f"Configuration file does not exist: {config.configuration}",
        f"Project root does not exist: {config.root}",
    )


def test_path_validator_allows_missing_optional_paths(tmp_path: Path) -> None:
    """Optional project folders and registries need not exist."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "configuration.yaml").touch()

    assert PathValidator().validate(_config(root)) == ()


def test_path_validator_rejects_existing_paths_of_wrong_type(tmp_path: Path) -> None:
    """Configured directories and files must have the expected type."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "configuration.yaml").touch()
    (root / "packages").touch()
    registry = root / ".storage/core.entity_registry"
    registry.mkdir(parents=True)

    assert PathValidator().validate(_config(root)) == (
        f"Project directory is not a directory: {root / 'packages'}",
        f"Registry path is not a file: {registry}",
    )


def test_path_validator_rejects_required_paths_of_wrong_type(tmp_path: Path) -> None:
    """Required root and configuration paths retain their expected types."""
    root = tmp_path / "project"
    root.touch()
    config = replace(_config(root), configuration=tmp_path)

    assert PathValidator().validate(config) == (
        f"Configuration path is not a file: {tmp_path}",
        f"Project root is not a directory: {root}",
    )


def test_output_validator_accepts_creatable_outputs(tmp_path: Path) -> None:
    """Non-existing outputs pass when an existing parent is writable."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "README.md").touch()

    assert OutputValidator().validate(_config(root)) == ()


def test_output_validator_rejects_wrong_existing_types(tmp_path: Path) -> None:
    """File and directory output targets cannot exchange roles."""
    root = tmp_path / "project"
    root.mkdir()
    (root / "README.md").mkdir()
    output_docs = root / "docs/generated"
    output_docs.parent.mkdir()
    output_docs.touch()

    assert OutputValidator().validate(_config(root)) == (
        f"Output directory is not a directory: {output_docs}",
        f"Output file is not a file: {root / 'README.md'}",
    )


def test_output_validator_reports_unwritable_locations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every output kind reports an objectively unwritable location."""
    config = _config(tmp_path)
    monkeypatch.setattr(validation, "_has_writable_location", Mock(return_value=False))

    expected = (
        f"Output location is not writable: {config.ai_context}",
        f"Output location is not writable: {config.entity_map}",
        f"Output location is not writable: {config.cache}",
        f"Output location is not writable: {config.readme}",
        f"Output location is not writable: {config.output_docs}",
    )
    assert OutputValidator().validate(config) == tuple(sorted(expected))


def test_environment_validator_enforces_python_314() -> None:
    """The documented minimum Python runtime is enforced explicitly."""
    validator = EnvironmentValidator()

    assert validator.validate((3, 14)) == ()
    assert validator.validate((3, 13)) == ("Python 3.14 or newer is required; found 3.13.",)


def test_runtime_validation_aggregates_all_validators(tmp_path: Path) -> None:
    """The public validation operation returns one sorted immutable result."""
    config = replace(_config(tmp_path / "missing"), project_name="")

    errors = validate_runtime_configuration(config, (3, 13))

    assert errors == tuple(sorted(set(errors)))
    assert "Project name must not be empty." in errors
    assert "Python 3.14 or newer is required; found 3.13." in errors
    assert f"Project root does not exist: {config.root}" in errors


def test_writable_location_rejects_path_without_existing_ancestor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An output path without an accessible ancestor is not writable."""
    monkeypatch.setattr(Path, "exists", Mock(return_value=False))

    assert validation._has_writable_location(Path("missing/output")) is False
