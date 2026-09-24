"""Tests for loading HA-DocGen runtime configuration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from ha_docgen.config import ConfigError, load_config


def _write_config(
    path: Path,
    root: Path,
    cache_path: str = ".cache/ha-docgen.json",
) -> None:
    """Write a complete minimal runtime configuration."""
    path.write_text(
        f"""
project:
  name: Test Project
  version: "1.0"
paths:
  root: "{root.as_posix()}"
  configuration: configuration.yaml
  packages: packages
  dashboards: dashboards
  esphome: esphome
  docs: docs
  themes: themes
  custom_components: custom_components
  www: www
  storage: .storage
files:
  entity_registry: .storage/core.entity_registry
  device_registry: .storage/core.device_registry
  area_registry: .storage/core.area_registry
  floor_registry: .storage/core.floor_registry
  config_entries: .storage/core.config_entries
output:
  readme: README.md
  ai_context: AI_CONTEXT.md
  entity_map: ENTITY_MAP.md
  docs: docs/generated
cache:
  path: {cache_path}
""".lstrip(),
        encoding="utf-8",
    )


def test_load_config_builds_all_paths_from_root(tmp_path: Path) -> None:
    """A complete file is loaded into one immutable project configuration."""
    config_file = tmp_path / "config.yaml"
    project_root = tmp_path / "project"
    _write_config(config_file, project_root)

    config = load_config(config_file)

    assert config.project_name == "Test Project"
    assert config.version == "1.0"
    assert config.root == project_root
    assert config.configuration == project_root / "configuration.yaml"
    assert config.floor_registry == project_root / ".storage/core.floor_registry"
    assert config.output_docs == project_root / "docs/generated"
    assert config.cache == config_file.parent / ".cache/ha-docgen.json"


def test_load_config_preserves_absolute_cache_location(tmp_path: Path) -> None:
    """A configured absolute cache path remains outside the project root."""
    config_file = tmp_path / "config.yaml"
    cache = tmp_path.parent / "cache/ha-docgen.json"
    _write_config(config_file, tmp_path / "project", cache.as_posix())

    assert load_config(config_file).cache == cache


@pytest.mark.parametrize(
    ("contents", "expected"),
    (
        ("project: [", "Invalid YAML"),
        ("project: {}\n", "Missing configuration section"),
        (
            (
                "project:\n  name: Test\n  version: 1\npaths: {}\nfiles: {}\n"
                "output: {}\ncache: {}\n"
            ),
            "must be a non-empty string",
        ),
    ),
)
def test_load_config_reports_invalid_content_as_config_error(
    tmp_path: Path,
    contents: str,
    expected: str,
) -> None:
    """Malformed schemas receive a stable configuration error."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(contents, encoding="utf-8")

    with pytest.raises(ConfigError, match=expected):
        load_config(config_file)


def test_example_config_loads_successfully() -> None:
    """The shipped example configuration parses into a complete ProjectConfig."""
    config = load_config(Path("examples/config.yaml"))

    assert config.project_name == "Home Assistant"
    assert config.version == "1.0"
    assert config.root == Path("/path/to/homeassistant/config")
    assert config.configuration.name == "configuration.yaml"
    assert config.output_docs.name == "generated"
    assert config.cache.name == "ha-docgen.json"


def test_load_config_reports_unreadable_or_missing_file(tmp_path: Path) -> None:
    """A missing configuration file is an expected configuration failure."""
    config_file = tmp_path / "missing.yaml"

    with pytest.raises(ConfigError, match="Configuration file not found") as raised:
        load_config(config_file)

    message = str(raised.value)
    assert str(config_file) in message
    assert "Create a configuration file based on the example configuration" in message
    assert "ha-docgen --config path/to/config.yaml" in message


def test_load_config_requires_mapping_root(tmp_path: Path) -> None:
    """A YAML sequence cannot serve as runtime configuration."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("[]\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="root must be a mapping"):
        load_config(config_file)


def test_load_config_wraps_file_read_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expected file I/O failures are exposed as configuration errors."""
    config_file = tmp_path / "config.yaml"
    config_file.touch()
    monkeypatch.setattr(Path, "open", Mock(side_effect=OSError("denied")))

    with pytest.raises(ConfigError, match="Unable to read configuration file"):
        load_config(config_file)
