"""Read-only queries over an existing ProjectTree."""

from __future__ import annotations

from pathlib import Path

from ..constants import ROOT_RELATIVE, YAML_EXTENSIONS
from .tree import ProjectFile, ProjectTree


def project_files(tree: ProjectTree) -> tuple[ProjectFile, ...]:
    """Return each file once, ordered by relative POSIX path."""
    ordered = sorted(
        (item for folder in tree.folders for item in folder.files),
        key=lambda item: item.relative_path.as_posix(),
    )
    return _unique_files(ordered)


def files_under(tree: ProjectTree, directory: Path) -> tuple[ProjectFile, ...]:
    """Return files stored below *directory*, ordered by relative path."""
    resolved = directory.resolve()
    return tuple(item for item in project_files(tree) if _is_below(item.path, resolved))


def folder_exists(tree: ProjectTree, path: Path) -> bool:
    """Return whether *path* is a folder already stored in *tree*."""
    resolved = path.resolve()
    return any(folder.path.resolve() == resolved for folder in tree.folders)


def root_yaml_files(tree: ProjectTree) -> tuple[ProjectFile, ...]:
    """Return YAML files stored directly at the repository root."""
    return tuple(item for item in project_files(tree) if _is_root_yaml(item))


def _unique_files(ordered: list[ProjectFile]) -> tuple[ProjectFile, ...]:
    """Drop later files that repeat a relative path."""
    unique: list[ProjectFile] = []
    seen: set[str] = set()
    for item in ordered:
        key = item.relative_path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return tuple(unique)


def _is_root_yaml(item: ProjectFile) -> bool:
    """Return whether one stored file is YAML at the repository root."""
    return item.relative_path.parent == ROOT_RELATIVE and item.extension in YAML_EXTENSIONS


def _is_below(path: Path, directory: Path) -> bool:
    """Return whether *path* is strictly inside *directory*."""
    resolved = path.resolve()
    return resolved != directory and resolved.is_relative_to(directory)
