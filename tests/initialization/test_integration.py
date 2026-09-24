"""Integration tests for ha-docgen init first-run workflow."""

from __future__ import annotations

from pathlib import Path

import pytest

from ha_docgen import main as cli
from ha_docgen.config import load_config
from ha_docgen.initialization import ConfigRenderer

pytestmark = pytest.mark.integration


def test_init_creates_valid_config_in_temporary_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """End-to-end init writes a loadable configuration and keeps help working."""
    monkeypatch.chdir(tmp_path)

    assert cli.main(("init",)) == cli.EXIT_SUCCESS
    assert "✓ config.yaml created" in capsys.readouterr().out

    config_file = tmp_path / "config.yaml"
    assert config_file.is_file()
    assert config_file.read_text(encoding="utf-8") == ConfigRenderer().render()

    config = load_config(config_file)
    assert config.project_name == "Your Project"
    assert config.root == Path("/path/to/homeassistant/config")
    assert config.cache == tmp_path / ".cache/ha-docgen.json"

    assert cli.main(("help",)) == cli.EXIT_SUCCESS
    help_output = capsys.readouterr().out
    assert "ha-docgen init" in help_output
    assert "ha-docgen validate" in help_output
    assert "ha-docgen report" in help_output


def test_init_then_existing_cli_version_still_works(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Initialization does not alter unrelated CLI command behaviour."""
    monkeypatch.chdir(tmp_path)

    assert cli.main(("init",)) == cli.EXIT_SUCCESS
    capsys.readouterr()

    assert cli.main(("version",)) == cli.EXIT_SUCCESS
    assert capsys.readouterr().out == cli._version_text()

    assert cli.main(("init",)) == cli.EXIT_CONFIG_ERROR
    assert "Configuration already exists." in capsys.readouterr().out
