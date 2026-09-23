"""Validation of HA-DocGen runtime configuration."""

from __future__ import annotations

import os
from pathlib import Path

from .config import ProjectConfig

MINIMUM_PYTHON_VERSION = (3, 14)


class ConfigurationValidator:
    """Validate semantic values in a runtime configuration."""

    def validate(self, config: ProjectConfig) -> tuple[str, ...]:
        """Return deterministic semantic configuration errors."""
        errors: set[str] = set()
        if not config.project_name.strip():
            errors.add("Project name must not be empty.")
        if not config.version.strip():
            errors.add("Project version must not be empty.")
        return tuple(sorted(errors))


class PathValidator:
    """Validate configured project input paths without modifying them."""

    def validate(self, config: ProjectConfig) -> tuple[str, ...]:
        """Return deterministic project path errors."""
        errors = self._required_errors(config)
        errors.update(self._directory_errors(config))
        errors.update(self._registry_errors(config))
        return tuple(sorted(errors))

    def _required_errors(self, config: ProjectConfig) -> set[str]:
        """Validate inputs required for every execution."""
        errors: set[str] = set()
        if not config.root.exists():
            errors.add(f"Project root does not exist: {config.root}")
        elif not config.root.is_dir():
            errors.add(f"Project root is not a directory: {config.root}")
        if not config.configuration.exists():
            errors.add(f"Configuration file does not exist: {config.configuration}")
        elif not config.configuration.is_file():
            errors.add(f"Configuration path is not a file: {config.configuration}")
        return errors

    def _directory_errors(self, config: ProjectConfig) -> set[str]:
        """Validate existing optional project directories."""
        paths = (
            config.packages,
            config.dashboards,
            config.esphome,
            config.docs,
            config.themes,
            config.custom_components,
            config.www,
            config.storage,
        )
        return {
            f"Project directory is not a directory: {path}"
            for path in paths
            if path.exists() and not path.is_dir()
        }

    def _registry_errors(self, config: ProjectConfig) -> set[str]:
        """Validate existing optional registry files."""
        paths = (
            config.entity_registry,
            config.device_registry,
            config.area_registry,
            config.floor_registry,
            config.config_entries,
        )
        return {
            f"Registry path is not a file: {path}"
            for path in paths
            if path.exists() and not path.is_file()
        }


class OutputValidator:
    """Validate output targets without creating or writing files."""

    def validate(self, config: ProjectConfig) -> tuple[str, ...]:
        """Return deterministic output target errors."""
        errors = self._file_errors(
            (config.readme, config.ai_context, config.entity_map, config.cache)
        )
        errors.update(self._directory_errors((config.output_docs,)))
        return tuple(sorted(errors))

    def _file_errors(self, paths: tuple[Path, ...]) -> set[str]:
        """Validate output file targets and their writable locations."""
        errors: set[str] = set()
        for path in paths:
            if path.exists() and not path.is_file():
                errors.add(f"Output file is not a file: {path}")
            elif not _has_writable_location(path):
                errors.add(f"Output location is not writable: {path}")
        return errors

    def _directory_errors(self, paths: tuple[Path, ...]) -> set[str]:
        """Validate output directory targets and writable locations."""
        errors: set[str] = set()
        for path in paths:
            if path.exists() and not path.is_dir():
                errors.add(f"Output directory is not a directory: {path}")
            elif not _has_writable_location(path):
                errors.add(f"Output location is not writable: {path}")
        return errors


class EnvironmentValidator:
    """Validate the Python runtime required by HA-DocGen."""

    def validate(self, python_version: tuple[int, int]) -> tuple[str, ...]:
        """Return an error when the Python runtime is unsupported."""
        if python_version >= MINIMUM_PYTHON_VERSION:
            return ()
        actual = ".".join(str(part) for part in python_version)
        required = ".".join(str(part) for part in MINIMUM_PYTHON_VERSION)
        return (f"Python {required} or newer is required; found {actual}.",)


def validate_runtime_configuration(
    config: ProjectConfig,
    python_version: tuple[int, int],
) -> tuple[str, ...]:
    """Run all runtime validators and return deterministic errors."""
    errors = (
        *ConfigurationValidator().validate(config),
        *PathValidator().validate(config),
        *OutputValidator().validate(config),
        *EnvironmentValidator().validate(python_version),
    )
    return tuple(sorted(set(errors)))


def _has_writable_location(path: Path) -> bool:
    """Return whether an output target or its nearest parent is writable."""
    candidate = path if path.exists() else path.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    if not candidate.exists():
        return False
    target = candidate if candidate.is_dir() else candidate.parent
    return target.is_dir() and os.access(target, os.W_OK)
