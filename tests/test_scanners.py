"""Unit tests for the generic filesystem and folder scanners."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from tools.ha_docgen.policy import IgnoreRules, ScanPolicy
from tools.ha_docgen.project import discover_project
from tools.ha_docgen.scanners.filesystem import FilesystemScanner
from tools.ha_docgen.scanners.folder_discovery import FolderDiscoveryScanner
from tools.ha_docgen.tests.support import write_text_files


def test_filesystem_scanner_counts_supported_project_content(tmp_path: Path) -> None:
    """A full scan counts supported files and Home Assistant subtrees."""
    write_text_files(
        tmp_path,
        {
            "configuration.yaml": "homeassistant:",
            "packages/one.yaml": "one:",
            "packages/nested/two.YML": "two:",
            "dashboards/main.yml": "views: []",
            "esphome/node.yaml": "esphome:",
            "themes/default.yaml": "Default:",
            "custom_components/alpha/manifest.json": "{}",
            "custom_components/beta/__init__.py": "",
            "notes.txt": "ignored",
        },
    )

    result = FilesystemScanner(tmp_path, ScanPolicy()).scan()

    assert (result.yaml_files, result.json_files, result.python_files) == (6, 1, 1)
    assert result.package_count == 2
    assert result.dashboard_count == 1
    assert result.esphome_count == 1
    assert result.theme_count == 1
    assert result.custom_component_count == 2


def test_filesystem_scanner_applies_policy_and_explicit_selection(tmp_path: Path) -> None:
    """Policy exclusions and incremental selections constrain global counts."""
    selected = tmp_path / "packages/selected.yaml"
    excluded = tmp_path / "packages/skip.yaml"
    other = tmp_path / "dashboards/other.yaml"
    write_text_files(
        tmp_path,
        {
            "packages/selected.yaml": "selected:",
            "packages/skip.yaml": "skip:",
            "dashboards/other.yaml": "other:",
        },
    )
    policy = ScanPolicy(
        IgnoreRules(
            directories=frozenset(),
            filenames=frozenset({"skip.yaml"}),
            filename_patterns=frozenset(),
        )
    )

    result = FilesystemScanner(tmp_path, policy).scan((selected, excluded, other))

    assert result.yaml_files == 2
    assert result.package_count == 2
    assert result.dashboard_count == 1


def test_filesystem_scanner_limits_a_supplied_tree_to_the_selection(
    tmp_path: Path,
) -> None:
    """A supplied ProjectTree is filtered by the explicit file selection."""
    selected = tmp_path / "packages" / "selected.yaml"
    write_text_files(
        tmp_path,
        {
            "packages/selected.yaml": "selected:",
            "packages/other.yaml": "other:",
        },
    )
    tree = discover_project(tmp_path, ScanPolicy())

    result = FilesystemScanner(tmp_path, ScanPolicy()).scan((selected,), tree)

    assert result.yaml_files == 1
    assert result.package_count == 1


def test_filesystem_scanner_returns_zero_for_absent_feature_folders(
    tmp_path: Path,
) -> None:
    """Optional project folders contribute zero when they do not exist."""
    result = FilesystemScanner(tmp_path, ScanPolicy()).scan()

    assert result.yaml_files == 0
    assert result.package_count == 0
    assert result.custom_component_count == 0


def test_folder_discovery_reports_all_configured_folders(tmp_path: Path) -> None:
    """Folder discovery preserves configured labels, existence and file totals."""
    packages = tmp_path / "packages"
    storage = tmp_path / ".storage"
    write_text_files(
        tmp_path,
        {
            "packages/one.yaml": "one:",
            "packages/nested/two.yaml": "two:",
            ".storage/core.entity_registry": "{}",
        },
    )
    config = SimpleNamespace(
        packages=packages,
        dashboards=tmp_path / "dashboards",
        esphome=tmp_path / "esphome",
        themes=tmp_path / "themes",
        custom_components=tmp_path / "custom_components",
        www=tmp_path / "www",
        storage=storage,
    )

    folders = FolderDiscoveryScanner(config).scan()
    by_name = {folder.name: folder for folder in folders}

    assert tuple(by_name) == (
        "Packages",
        "Dashboards",
        "ESPHome",
        "Themes",
        "Custom Components",
        "WWW",
        "Storage",
    )
    assert by_name["Packages"].exists is True
    assert by_name["Packages"].file_count == 2
    assert by_name["Storage"].file_count == 1
    assert by_name["Dashboards"].exists is False
    assert by_name["Dashboards"].file_count == 0


def test_folder_discovery_uses_the_configured_project_root(tmp_path: Path) -> None:
    """Discovery uses ``config.root`` when the caller does not supply a tree."""
    write_text_files(tmp_path, {"packages/one.yaml": "one:"})
    missing = tmp_path / "missing"
    config = SimpleNamespace(
        root=tmp_path,
        packages=tmp_path / "packages",
        dashboards=missing,
        esphome=missing,
        themes=missing,
        custom_components=missing,
        www=missing,
        storage=missing,
    )

    folders = FolderDiscoveryScanner(config).scan()

    assert folders[0].exists is True
    assert folders[0].file_count == 1


def test_folder_discovery_honours_explicit_file_selection(tmp_path: Path) -> None:
    """Incremental folder counts include only selected files under each folder."""
    first = tmp_path / "packages/first.yaml"
    second = tmp_path / "packages/second.yaml"
    write_text_files(
        tmp_path,
        {
            "packages/first.yaml": "first:",
            "packages/second.yaml": "second:",
        },
    )
    missing = tmp_path / "missing"
    config = SimpleNamespace(
        packages=tmp_path / "packages",
        dashboards=missing,
        esphome=missing,
        themes=missing,
        custom_components=missing,
        www=missing,
        storage=missing,
    )

    folders = FolderDiscoveryScanner(config).scan((second, tmp_path / "outside.yaml"))

    assert folders[0].file_count == 1
    assert first.exists()
