"""Root YAML is a pure query over an existing ProjectTree."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tools.ha_docgen.project import (
    ProjectFile,
    ProjectTree,
    project_files,
    project_tree_from_files,
    root_yaml_files,
)
from tools.ha_docgen.project.builder import ProjectTreeBuilder
from tools.ha_docgen.project.filesystem_entry import FilesystemEntry
from tools.ha_docgen.project.walker import FilesystemWalker
from tools.ha_docgen.tests.support import write_text_files
from tools.ha_docgen.yaml import YamlLoader

pytestmark = pytest.mark.unit

_ROOT_YAML: tuple[str, ...] = (
    "automations.yaml",
    "configuration.yaml",
    "groups.yaml",
    "scenes.yaml",
    "scripts.yaml",
    "secrets.yaml",
    "ui-lovelace.yml",
)


def test_root_yaml_files_returns_every_root_yaml_file() -> None:
    """Known and additional root YAML files are projected from the tree."""
    tree = _repository_tree()

    assert _names(root_yaml_files(tree)) == _ROOT_YAML


def test_root_yaml_files_excludes_other_yaml_and_root_files() -> None:
    """Packages, dashboards, nested YAML and non-YAML root files stay out."""
    names = set(_names(root_yaml_files(_repository_tree())))

    assert "packages/lighting.yaml" not in names
    assert "dashboards/main.yaml" not in names
    assert "nested/extra.yaml" not in names
    assert "nested/deeper/item.yaml" not in names
    assert "README.md" not in names


def test_root_yaml_files_repeat_the_project_tree_order() -> None:
    """Two queries match, in relative POSIX order, even if storage is reversed."""
    tree = _repository_tree()
    tree.folders[0].files.reverse()
    first = root_yaml_files(tree)
    second = root_yaml_files(tree)

    assert first == second
    assert first is not second
    assert _names(first) == _ROOT_YAML


def test_root_yaml_files_are_the_stored_project_files() -> None:
    """The query returns the original ProjectFile objects and nothing else."""
    tree = _repository_tree()
    stored = {item.relative_path.as_posix(): item for item in project_files(tree)}
    found = root_yaml_files(tree)

    assert isinstance(found, tuple)
    assert all(item is stored[item.relative_path.as_posix()] for item in found)


def test_explicit_selection_returns_only_selected_root_yaml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A projected selection yields its root YAML and does not search further."""
    write_text_files(
        tmp_path,
        {
            "configuration.yaml": "homeassistant:\n",
            "secrets.yaml": "token: secret\n",
            "automations.yaml": "[]\n",
            "packages/lighting.yaml": "light: {}\n",
            "dashboards/main.yaml": "views: []\n",
        },
    )
    selected = (
        tmp_path / "configuration.yaml",
        tmp_path / "packages" / "lighting.yaml",
    )
    tree = project_tree_from_files(tmp_path, selected)
    _reject_filesystem(monkeypatch)

    assert _names(root_yaml_files(tree)) == ("configuration.yaml",)


def test_root_yaml_files_do_not_touch_the_filesystem(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The query reads stored metadata and does not discover or load files."""
    tree = _repository_tree()
    _reject_filesystem(monkeypatch)

    assert _names(root_yaml_files(tree)) == _ROOT_YAML


def _repository_tree() -> ProjectTree:
    """Build a repository tree without reading or writing the filesystem."""
    root = Path("repository")
    relatives = (
        *_ROOT_YAML,
        "README.md",
        "packages",
        "packages/lighting.yaml",
        "dashboards",
        "dashboards/main.yaml",
        "nested",
        "nested/extra.yaml",
        "nested/deeper",
        "nested/deeper/item.yaml",
    )
    directories = {"packages", "dashboards", "nested", "nested/deeper"}
    entries = [
        _entry(root, relative, is_dir=relative in directories) for relative in relatives
    ]
    return ProjectTreeBuilder().build(root, entries)


def _entry(root: Path, relative: str, *, is_dir: bool) -> FilesystemEntry:
    """Build one filesystem entry from stored metadata only."""
    path = root / relative
    return FilesystemEntry(
        path=path,
        relative_path=Path(relative),
        name=path.name,
        is_file=not is_dir,
        is_dir=is_dir,
        extension="" if is_dir else path.suffix.lower(),
        size=0 if is_dir else 1,
        modified=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _names(files: tuple[ProjectFile, ...]) -> tuple[str, ...]:
    """Return relative POSIX paths for one query result."""
    return tuple(item.relative_path.as_posix() for item in files)


def _reject_filesystem(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail when code discovers, stats, opens or loads a file."""

    def rejected(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("root YAML query touched the filesystem")

    for name in (
        "exists",
        "is_file",
        "is_dir",
        "stat",
        "lstat",
        "rglob",
        "iterdir",
        "open",
        "read_text",
        "read_bytes",
    ):
        monkeypatch.setattr(Path, name, rejected)
    monkeypatch.setattr(FilesystemWalker, "walk", rejected)
    monkeypatch.setattr("tools.ha_docgen.project.discovery.discover_project", rejected)
    monkeypatch.setattr(YamlLoader, "load", rejected)
