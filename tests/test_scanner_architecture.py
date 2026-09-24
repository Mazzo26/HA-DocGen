"""Scanner architecture: one ProjectTree is the repository source."""

from __future__ import annotations

from pathlib import Path

import pytest

from ha_docgen.config import ProjectConfig
from ha_docgen.constants import YAML_EXTENSIONS
from ha_docgen.packages import PackageScanner
from ha_docgen.policy import ScanPolicy
from ha_docgen.project import ProjectTree, discover_project, files_under
from ha_docgen.project.filesystem_entry import FilesystemEntry
from ha_docgen.project.walker import FilesystemWalker
from ha_docgen.scanner import Scanner
from ha_docgen.storage import StorageScanner
from ha_docgen.yaml import YamlLoader
from tests.support import write_text_files

pytestmark = pytest.mark.unit


def test_scanner_walks_the_repository_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A complete scan discovers the repository with one walker call."""
    _write_repository(tmp_path)
    calls = _count_walks(monkeypatch)

    Scanner(_config(tmp_path)).scan()

    assert calls["walk"] == 1


def test_scanner_selection_does_not_walk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """An explicit selection is projected into a ProjectTree without walking."""
    selected = tmp_path / "packages" / "lighting.yaml"
    _write_repository(tmp_path)
    calls = _count_walks(monkeypatch)

    model = Scanner(_config(tmp_path)).scan((selected,))

    assert calls["walk"] == 0
    assert model.scan.yaml_files == 1
    assert model.scan.package_count == 1
    assert model.scan.dashboard_count == 0
    assert {folder.name: folder.file_count for folder in model.folders}["Packages"] == 1


def test_scanner_counts_match_the_project_tree(tmp_path: Path) -> None:
    """Package, dashboard and storage totals come from the same ProjectTree."""
    _write_repository(tmp_path)
    config = _config(tmp_path)
    tree = discover_project(config.root, ScanPolicy())

    model = Scanner(config).scan()
    inventory = StorageScanner(config.storage).scan_from_tree(tree)

    assert model.scan.package_count == _yaml_count(tree, config.packages)
    assert model.scan.dashboard_count == _yaml_count(tree, config.dashboards)
    assert model.scan.yaml_files == _yaml_count(tree, config.root)
    storage = files_under(tree, config.storage)
    assert tuple(item.relative_path for item in inventory) == tuple(
        item.relative_path for item in storage
    )
    folders = {folder.name: folder for folder in model.folders}
    assert folders["Packages"].exists is True
    assert folders["Packages"].file_count == len(files_under(tree, config.packages))
    assert folders["Storage"].file_count == len(storage)
    assert folders["ESPHome"].exists is False


def test_package_scanner_reads_a_supplied_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Package loading uses the supplied tree and does not walk again."""
    _write_repository(tmp_path)
    packages = tmp_path / "packages"
    tree = discover_project(tmp_path, ScanPolicy())
    _reject_walks(monkeypatch)

    documents = PackageScanner(YamlLoader()).scan(packages, tree)

    assert tuple(document.path.relative_to(packages).as_posix() for document in documents) == (
        "lighting.yaml",
    )


def test_storage_scanner_reads_a_supplied_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Storage inventory uses the supplied tree and does not walk again."""
    _write_repository(tmp_path)
    tree = discover_project(tmp_path, ScanPolicy())
    _reject_walks(monkeypatch)

    inventory = StorageScanner(tmp_path / ".storage").scan_from_tree(tree)

    assert [item.name for item in inventory] == ["core.entity_registry"]


def _write_repository(root: Path) -> None:
    """Write one small repository with packages, a dashboard and storage."""
    write_text_files(
        root,
        {
            "packages/lighting.yaml": "light: {}\n",
            "dashboards/main.yaml": "views: []\n",
            ".storage/core.entity_registry": "{}\n",
            "__pycache__/cache.yaml": "cached: true\n",
        },
    )


def _config(root: Path) -> ProjectConfig:
    """Return a complete configuration for an isolated project."""
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


def _yaml_count(tree: ProjectTree, directory: Path) -> int:
    """Count YAML files stored below *directory*."""
    return sum(
        1 for item in files_under(tree, directory) if item.extension in YAML_EXTENSIONS
    )


def _count_walks(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Count FilesystemWalker.walk calls made during a scan."""
    calls = {"walk": 0}
    original = FilesystemWalker.walk

    def counting(self: FilesystemWalker, root: Path) -> list[FilesystemEntry]:
        calls["walk"] += 1
        return original(self, root)

    monkeypatch.setattr(FilesystemWalker, "walk", counting)
    return calls


def _reject_walks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail the test when discovery walks after a tree already exists."""

    def rejected(self: FilesystemWalker, root: Path) -> list[FilesystemEntry]:
        raise AssertionError(f"unexpected walk of {root}")

    monkeypatch.setattr(FilesystemWalker, "walk", rejected)
