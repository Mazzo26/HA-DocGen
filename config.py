from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial
from pathlib import Path

import yaml

from .constants import DEFAULT_ENCODING


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Immutable HA-DocGen runtime configuration."""

    project_name: str
    version: str

    root: Path

    configuration: Path
    packages: Path
    dashboards: Path
    esphome: Path
    docs: Path
    themes: Path
    custom_components: Path
    www: Path
    storage: Path

    entity_registry: Path
    device_registry: Path
    area_registry: Path
    floor_registry: Path
    config_entries: Path

    readme: Path
    ai_context: Path
    entity_map: Path
    output_docs: Path
    cache: Path


class ConfigError(Exception):
    """Expected runtime configuration failure."""


def load_config(config_file: Path) -> ProjectConfig:
    """Load and parse one HA-DocGen runtime configuration file."""
    if not config_file.exists():
        raise ConfigError(f"Configuration file not found: {config_file}")
    raw = _load_yaml(config_file)
    project = _section(raw, "project")
    paths = _section(raw, "paths")
    files = _section(raw, "files")
    output = _section(raw, "output")
    cache = _section(raw, "cache")
    root = Path(_text(paths, "root", "paths"))
    cache_path = _cache_path(config_file, cache)
    return _build_config(project, paths, files, output, root, cache_path)


def _load_yaml(config_file: Path) -> Mapping[str, object]:
    """Read YAML and require a mapping at the document root."""
    try:
        with config_file.open("r", encoding=DEFAULT_ENCODING) as file:
            raw = yaml.safe_load(file)
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in configuration file: {config_file}") from exc
    except OSError as exc:
        raise ConfigError(f"Unable to read configuration file: {config_file}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("Configuration root must be a mapping.")
    return raw


def _section(config: Mapping[str, object], name: str) -> Mapping[str, object]:
    """Return one required mapping section."""
    value = config.get(name)
    if not isinstance(value, dict):
        raise ConfigError(f"Missing configuration section: {name}.")
    return value


def _text(section: Mapping[str, object], key: str, section_name: str) -> str:
    """Return one required non-empty string value."""
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Configuration value {section_name}.{key} must be a non-empty string.")
    return value


def _configured_path(
    root: Path,
    section: Mapping[str, object],
    key: str,
    section_name: str,
) -> Path:
    """Resolve one configured path below the project root."""
    return root / _text(section, key, section_name)


def _cache_path(config_file: Path, section: Mapping[str, object]) -> Path:
    """Resolve the configured cache outside or beside the tool config."""
    configured = Path(_text(section, "path", "cache")).expanduser()
    if configured.is_absolute():
        return configured
    return config_file.parent / configured


def _build_config(
    project: Mapping[str, object],
    paths: Mapping[str, object],
    files: Mapping[str, object],
    output: Mapping[str, object],
    root: Path,
    cache_path: Path,
) -> ProjectConfig:
    """Build the immutable public configuration model."""
    path = partial(_configured_path, root)
    return ProjectConfig(
        project_name=_text(project, "name", "project"),
        version=_text(project, "version", "project"),
        root=root,
        configuration=path(paths, "configuration", "paths"),
        packages=path(paths, "packages", "paths"),
        dashboards=path(paths, "dashboards", "paths"),
        esphome=path(paths, "esphome", "paths"),
        docs=path(paths, "docs", "paths"),
        themes=path(paths, "themes", "paths"),
        custom_components=path(paths, "custom_components", "paths"),
        www=path(paths, "www", "paths"),
        storage=path(paths, "storage", "paths"),
        entity_registry=path(files, "entity_registry", "files"),
        device_registry=path(files, "device_registry", "files"),
        area_registry=path(files, "area_registry", "files"),
        floor_registry=path(files, "floor_registry", "files"),
        config_entries=path(files, "config_entries", "files"),
        readme=path(output, "readme", "output"),
        ai_context=path(output, "ai_context", "output"),
        entity_map=path(output, "entity_map", "output"),
        output_docs=path(output, "docs", "output"),
        cache=cache_path,
    )
