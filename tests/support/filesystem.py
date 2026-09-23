"""Temporary project files and in-memory project trees for tests."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Final

from tools.ha_docgen.constants import DEFAULT_ENCODING, FOLDER_PACKAGES
from tools.ha_docgen.project import ProjectFile, ProjectFolder, ProjectTree

from .builders import _DEFAULT_PACKAGE_TEXT
from .paths import require_relative_path

_MODIFIED: Final[datetime] = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIGURATION: Final[str] = "homeassistant:\n  name: Sample\n"
_PACKAGE: Final[str] = _DEFAULT_PACKAGE_TEXT


def sample_project_files() -> Mapping[str, str]:
    """Return the shared sample project as relative path to UTF-8 text."""
    package = f"{FOLDER_PACKAGES}/sample.yaml"
    return MappingProxyType(
        {
            "configuration.yaml": _CONFIGURATION,
            package: _PACKAGE,
        }
    )


def write_text_files(root: Path, files: Mapping[str, str]) -> Path:
    """Write UTF-8 files under ``root`` in sorted relative-path order."""
    root.mkdir(parents=True, exist_ok=True)
    for relative in sorted(files):
        _write_text_file(root, relative, files[relative])
    return root


def create_sample_project(root: Path) -> Path:
    """Write the shared sample Home Assistant project and return its root."""
    return write_text_files(root, sample_project_files())


def create_output_directory(path: Path) -> Path:
    """Create an empty directory and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_project_tree(root: Path) -> ProjectTree:
    """Build a deterministic ``ProjectTree`` from an existing directory."""
    folders = _index_folders(root)
    _attach_files(root, folders)
    return ProjectTree(root=root, folders=_ordered_folders(folders))


def _write_text_file(root: Path, relative: str, content: str) -> None:
    """Write one relative UTF-8 file, creating parent directories."""
    path = root / require_relative_path(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding=DEFAULT_ENCODING, newline="\n")


def _index_folders(root: Path) -> dict[Path, ProjectFolder]:
    """Create folders in POSIX path order and link each one to its parent."""
    folders = {Path("."): _folder(root, Path("."))}
    for path in _sorted_paths(root, directories=True):
        relative = path.relative_to(root)
        folder = _folder(path, relative)
        folder.parent = folders[relative.parent]
        folder.parent.subfolders.append(folder)
        folders[relative] = folder
    return folders


def _attach_files(root: Path, folders: Mapping[Path, ProjectFolder]) -> None:
    """Attach files in POSIX path order using a fixed modification time."""
    for path in _sorted_paths(root, directories=False):
        relative = path.relative_to(root)
        folders[relative.parent].files.append(_project_file(path, relative))


def _sorted_paths(root: Path, *, directories: bool) -> tuple[Path, ...]:
    """Return files or directories under ``root``, sorted by relative path."""
    if not root.is_dir():
        raise ValueError(f"Directory required: {root}")
    paths = [path for path in root.rglob("*") if path.is_dir() == directories]
    return tuple(sorted(paths, key=lambda item: item.relative_to(root).as_posix()))


def _ordered_folders(folders: Mapping[Path, ProjectFolder]) -> list[ProjectFolder]:
    """Return folders with the root first, then sorted relative paths."""
    ordered = sorted(folders, key=lambda path: path.as_posix())
    return [folders[path] for path in ordered]


def _folder(path: Path, relative: Path) -> ProjectFolder:
    """Create one project folder."""
    return ProjectFolder(name=path.name, path=path, relative_path=relative)


def _project_file(path: Path, relative: Path) -> ProjectFile:
    """Create one project file with a fixed modification time."""
    return ProjectFile(
        name=path.name,
        path=path,
        relative_path=relative,
        extension=path.suffix,
        size=path.stat().st_size,
        modified=_MODIFIED,
    )
