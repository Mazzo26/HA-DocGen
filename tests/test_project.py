"""Unit tests for project filesystem models, walking and tree construction."""

from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path

from ha_docgen.policy import ScanPolicy
from ha_docgen.project import (
    ProjectFile,
    ProjectFolder,
    ProjectTree,
    discover_project,
    project_files,
)
from ha_docgen.project.builder import ProjectTreeBuilder
from ha_docgen.project.filesystem_entry import FilesystemEntry
from ha_docgen.project.walker import FilesystemWalker


def test_project_models_use_slots_and_value_equality(tmp_path: Path) -> None:
    """Project data objects compare by value and do not expose instance dictionaries."""
    modified = datetime(2026, 1, 1, tzinfo=UTC)
    values = {
        "name": "configuration.yaml",
        "path": tmp_path / "configuration.yaml",
        "relative_path": Path("configuration.yaml"),
        "extension": ".yaml",
        "size": 12,
        "modified": modified,
    }

    first = ProjectFile(**values)
    second = ProjectFile(**values)

    assert first == second
    assert not hasattr(first, "__dict__")
    assert {field.name for field in fields(first)} == set(values)


def test_project_folder_collections_are_not_shared(tmp_path: Path) -> None:
    """Every folder receives independent file and subfolder collections."""
    first = ProjectFolder("first", tmp_path / "first", Path("first"))
    second = ProjectFolder("second", tmp_path / "second", Path("second"))
    first.files.append(
        ProjectFile(
            "one.yaml",
            tmp_path / "first/one.yaml",
            Path("first/one.yaml"),
            ".yaml",
            1,
            datetime(2026, 1, 1, tzinfo=UTC),
        )
    )

    assert second.files == []
    assert second.subfolders == []


def test_filesystem_walker_collects_file_and_folder_metadata(tmp_path: Path) -> None:
    """The walker returns relative metadata for every item below its root."""
    nested = tmp_path / "Packages"
    nested.mkdir()
    source = nested / "LIGHT.YAML"
    source.write_text("light: {}", encoding="utf-8")

    entries = FilesystemWalker().walk(tmp_path)
    by_relative = {entry.relative_path: entry for entry in entries}

    assert set(by_relative) == {Path("Packages"), Path("Packages/LIGHT.YAML")}
    assert by_relative[Path("Packages")].is_dir is True
    assert by_relative[Path("Packages/LIGHT.YAML")].is_file is True
    assert by_relative[Path("Packages/LIGHT.YAML")].extension == ".yaml"
    assert by_relative[Path("Packages/LIGHT.YAML")].size == len("light: {}")


def test_project_tree_builder_links_and_orders_tree(tmp_path: Path) -> None:
    """The builder creates root, parent links and deterministic folder ordering."""
    (tmp_path / "z").mkdir()
    (tmp_path / "a/nested").mkdir(parents=True)
    (tmp_path / "root.yaml").write_text("root", encoding="utf-8")
    (tmp_path / "a/item.json").write_text("{}", encoding="utf-8")
    entries = FilesystemWalker().walk(tmp_path)

    tree = ProjectTreeBuilder().build(tmp_path, entries)
    root, area, nested, last = tree.folders

    assert tree.root == tmp_path
    assert [folder.relative_path for folder in tree.folders] == [
        Path("."),
        Path("a"),
        Path("a/nested"),
        Path("z"),
    ]
    assert root.parent is None
    assert area.parent is root
    assert nested.parent is area
    assert last.parent is root
    assert {folder.name for folder in root.subfolders} == {"a", "z"}
    assert [file.relative_path for file in root.files] == [Path("root.yaml")]
    assert [file.relative_path for file in area.files] == [Path("a/item.json")]


def test_project_tree_builder_orders_entries_independently_of_input(tmp_path: Path) -> None:
    """Folders and files are ordered by relative path, not insertion order."""
    entries = [
        _entry(tmp_path, "z.yaml"),
        _entry(tmp_path, "b", is_dir=True),
        _entry(tmp_path, "a", is_dir=True),
        _entry(tmp_path, "a/m.yaml"),
        _entry(tmp_path, "a/b.yaml"),
    ]

    tree = ProjectTreeBuilder().build(tmp_path, entries)
    root, area, last = tree.folders

    assert [folder.relative_path.as_posix() for folder in tree.folders] == [".", "a", "b"]
    assert [folder.name for folder in root.subfolders] == ["a", "b"]
    assert [file.relative_path.as_posix() for file in root.files] == ["z.yaml"]
    assert [file.relative_path.as_posix() for file in area.files] == ["a/b.yaml", "a/m.yaml"]
    assert last.files == []


def test_project_files_drops_duplicate_relative_paths(tmp_path: Path) -> None:
    """Querying a tree keeps the first file when a relative path repeats."""
    folder = ProjectFolder("root", tmp_path, Path("."))
    first = ProjectFile(
        "item.yaml",
        tmp_path / "item.yaml",
        Path("item.yaml"),
        ".yaml",
        4,
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    duplicate = ProjectFile(
        "item.yaml",
        tmp_path / "item.yaml",
        Path("item.yaml"),
        ".yaml",
        9,
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    folder.files.extend((first, duplicate))
    tree = ProjectTree(root=tmp_path, folders=[folder])

    assert [item.size for item in project_files(tree)] == [4]


def test_project_tree_builder_keeps_first_duplicate_path(tmp_path: Path) -> None:
    """A repeated relative path contributes one folder and one file."""
    first = _entry(tmp_path, "item.yaml", size=4)
    duplicate = _entry(tmp_path, "item.yaml", size=9)
    directory = _entry(tmp_path, "nested", is_dir=True)
    repeated = _entry(tmp_path, "nested", is_dir=True)

    tree = ProjectTreeBuilder().build(tmp_path, [first, duplicate, repeated, directory])
    root, nested = tree.folders

    assert [folder.relative_path.as_posix() for folder in tree.folders] == [".", "nested"]
    assert [folder.relative_path.as_posix() for folder in root.subfolders] == ["nested"]
    assert [file.size for file in root.files] == [4]
    assert project_files(tree)[0].size == 4


def test_project_discovery_is_deterministic_and_policy_filtered(tmp_path: Path) -> None:
    """Two discoveries share one order and omit ignored directories."""
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "cache.yaml").write_text("cached: true\n", encoding="utf-8")
    (tmp_path / "z").mkdir()
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "one.yaml").write_text("one: 1\n", encoding="utf-8")
    (tmp_path / "z" / "two.yaml").write_text("two: 2\n", encoding="utf-8")

    first = discover_project(tmp_path, ScanPolicy())
    second = discover_project(tmp_path, ScanPolicy())

    assert _shape(first) == _shape(second)
    assert _shape(first) == (
        (".", "a", "z"),
        ((".", ()), ("a", ("a/one.yaml",)), ("z", ("z/two.yaml",))),
    )
    assert "__pycache__/cache.yaml" not in {
        item.relative_path.as_posix() for item in project_files(first)
    }


def test_project_tree_builder_handles_empty_project(tmp_path: Path) -> None:
    """An empty entry collection still produces the repository root folder."""
    tree = ProjectTreeBuilder().build(tmp_path, [])

    assert len(tree.folders) == 1
    assert tree.folders[0] == ProjectFolder(tmp_path.name, tmp_path, Path("."))


def _entry(
    root: Path,
    relative: str,
    *,
    is_dir: bool = False,
    size: int = 1,
) -> FilesystemEntry:
    """Build one filesystem entry without touching the disk."""
    path = root / relative
    return FilesystemEntry(
        path=path,
        relative_path=Path(relative),
        name=path.name,
        is_file=not is_dir,
        is_dir=is_dir,
        extension="" if is_dir else path.suffix.lower(),
        size=0 if is_dir else size,
        modified=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _shape(
    tree: ProjectTree,
) -> tuple[tuple[str, ...], tuple[tuple[str, tuple[str, ...]], ...]]:
    """Return folder order and the files stored in each folder."""
    folders = tree.folders
    return (
        tuple(folder.relative_path.as_posix() for folder in folders),
        tuple(
            (
                folder.relative_path.as_posix(),
                tuple(item.relative_path.as_posix() for item in folder.files),
            )
            for folder in folders
        ),
    )
