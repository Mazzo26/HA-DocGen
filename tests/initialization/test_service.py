"""Unit tests for project initialization filesystem orchestration."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from ha_docgen.config import load_config
from ha_docgen.initialization import (
    CONFIG_FILE_NAME,
    ConfigRenderer,
    ConfigurationExistsError,
    InitializationError,
    InitializationService,
)


def test_initialize_creates_config_yaml(tmp_path: Path) -> None:
    """A missing configuration is created from the renderer output."""
    created = InitializationService().initialize(tmp_path)

    assert created == tmp_path / CONFIG_FILE_NAME
    assert created.is_file()
    assert created.read_text(encoding="utf-8") == ConfigRenderer().render()
    assert load_config(created).project_name == "Your Project"


def test_initialize_detects_existing_config(tmp_path: Path) -> None:
    """An existing configuration is reported without modification."""
    config_file = tmp_path / CONFIG_FILE_NAME
    config_file.write_text("existing\n", encoding="utf-8")

    with pytest.raises(ConfigurationExistsError, match="Configuration already exists"):
        InitializationService().initialize(tmp_path)

    assert config_file.read_text(encoding="utf-8") == "existing\n"


def test_initialize_never_overwrites_existing_config(tmp_path: Path) -> None:
    """Overwrite protection leaves permissions and contents untouched."""
    config_file = tmp_path / CONFIG_FILE_NAME
    config_file.write_text("keep-me\n", encoding="utf-8")
    original_stat = config_file.stat()

    with pytest.raises(ConfigurationExistsError):
        InitializationService().initialize(tmp_path)

    assert config_file.read_text(encoding="utf-8") == "keep-me\n"
    assert config_file.stat().st_mtime_ns == original_stat.st_mtime_ns
    assert config_file.stat().st_size == original_stat.st_size


def test_initialize_reports_permission_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Permission errors become initialization failures."""
    monkeypatch.setattr(
        Path,
        "write_text",
        Mock(side_effect=PermissionError("Permission denied")),
    )

    with pytest.raises(InitializationError, match="Permission denied"):
        InitializationService().initialize(tmp_path)

    assert not (tmp_path / CONFIG_FILE_NAME).exists()
    assert list(tmp_path.glob(".*tmp")) == []


def test_initialize_reports_filesystem_failure_and_cleans_temporary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replace failures remove temporary files and leave no config behind."""
    monkeypatch.setattr(
        "ha_docgen.initialization.service.os.replace",
        Mock(side_effect=OSError("disk full")),
    )

    with pytest.raises(InitializationError, match="disk full"):
        InitializationService().initialize(tmp_path)

    assert not (tmp_path / CONFIG_FILE_NAME).exists()
    assert list(tmp_path.iterdir()) == []


def test_initialize_accepts_injected_renderer(tmp_path: Path) -> None:
    """The service writes whatever the injected renderer produces."""
    renderer = Mock()
    renderer.render.return_value = "custom: true\n"

    created = InitializationService().initialize(tmp_path, renderer=renderer)

    renderer.render.assert_called_once_with()
    assert created.read_text(encoding="utf-8") == "custom: true\n"
