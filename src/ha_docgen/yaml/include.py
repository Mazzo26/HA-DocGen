"""Resolve Home Assistant include directives against a ProjectTree.

The resolver reads one loaded document and the files already stored in
the tree. It does not walk the repository, merge YAML, or open included
paths.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..constants import ROOT_RELATIVE, YAML_EXTENSIONS
from ..project import ProjectFile, ProjectTree, project_files
from .models import YamlDocument


class IncludeDirective(Enum):
    """Home Assistant include tag recognised in a YAML document."""

    INCLUDE = "include"
    INCLUDE_DIR_LIST = "include_dir_list"
    INCLUDE_DIR_NAMED = "include_dir_named"
    INCLUDE_DIR_MERGE_LIST = "include_dir_merge_list"
    INCLUDE_DIR_MERGE_NAMED = "include_dir_merge_named"


@dataclass(frozen=True, slots=True)
class IncludeNode:
    """One include directive stored in parsed YAML.

    The referenced path is not loaded and its contents are not merged.
    """

    directive: IncludeDirective
    raw_path: str


@dataclass(frozen=True, slots=True)
class IncludeReference:
    """Filesystem location referenced by one include directive."""

    directive: IncludeDirective
    source: Path
    raw_path: str
    target: Path
    files: tuple[ProjectFile, ...]
    resolved: bool


def resolve_includes(
    tree: ProjectTree,
    document: YamlDocument,
) -> tuple[IncludeReference, ...]:
    """Resolve include directives in *document* against files stored in *tree*.

    Relative paths are joined to the document's parent directory.
    Included documents are not loaded or walked.
    """
    stored = project_files(tree)
    nodes = _collect(document.data)
    return tuple(_resolve(tree, stored, document.path, node) for node in nodes)


def _collect(data: object) -> tuple[IncludeNode, ...]:
    """Return include nodes in document order."""
    found: list[IncludeNode] = []
    _walk(data, found)
    return tuple(found)


def _walk(data: object, found: list[IncludeNode]) -> None:
    """Append include nodes without following their targets."""
    if isinstance(data, IncludeNode):
        found.append(data)
        return
    if isinstance(data, dict):
        for key, value in data.items():
            _walk(key, found)
            _walk(value, found)
        return
    if isinstance(data, list):
        for value in data:
            _walk(value, found)


def _resolve(
    tree: ProjectTree,
    stored: tuple[ProjectFile, ...],
    source: Path,
    node: IncludeNode,
) -> IncludeReference:
    """Resolve one directive to stored files, or mark it unresolved."""
    target = _located(source, node.raw_path)
    relative = _inside_root(tree.root, target, node.raw_path)
    if relative is None:
        return _reference(node, source, target, (), False)
    if node.directive is IncludeDirective.INCLUDE:
        return _resolve_file(node, source, target, relative, stored)
    return _resolve_directory(tree, node, source, target, relative, stored)


def _resolve_file(
    node: IncludeNode,
    source: Path,
    target: Path,
    relative: Path,
    stored: tuple[ProjectFile, ...],
) -> IncludeReference:
    """Match one file path to a single stored ProjectFile."""
    match = _find_file(stored, relative)
    files = () if match is None else (match,)
    return _reference(node, source, target, files, match is not None)


def _resolve_directory(
    tree: ProjectTree,
    node: IncludeNode,
    source: Path,
    target: Path,
    relative: Path,
    stored: tuple[ProjectFile, ...],
) -> IncludeReference:
    """Match a directory directive to direct YAML children in the tree."""
    if not _folder_known(tree, relative):
        return _reference(node, source, target, (), False)
    return _reference(node, source, target, _directory_files(stored, relative), True)


def _reference(
    node: IncludeNode,
    source: Path,
    target: Path,
    files: tuple[ProjectFile, ...],
    resolved: bool,
) -> IncludeReference:
    """Build one immutable include reference."""
    return IncludeReference(
        directive=node.directive,
        source=source,
        raw_path=node.raw_path,
        target=target,
        files=files,
        resolved=resolved,
    )


def _located(source: Path, raw_path: str) -> Path:
    """Join *raw_path* to the document directory without touching disk."""
    return Path(os.path.normpath(source.parent / raw_path))


def _inside_root(root: Path, target: Path, raw_path: str) -> Path | None:
    """Return *target* relative to *root*, or None when it cannot be used."""
    if raw_path.strip() == "":
        return None
    base = Path(os.path.normpath(root))
    try:
        relative = target.relative_to(base)
    except ValueError:
        return None
    if relative.as_posix() == ".":
        return ROOT_RELATIVE
    return relative


def _find_file(
    stored: tuple[ProjectFile, ...],
    relative: Path,
) -> ProjectFile | None:
    """Return the stored file with this relative path."""
    key = relative.as_posix()
    for item in stored:
        if item.relative_path.as_posix() == key:
            return item
    return None


def _folder_known(tree: ProjectTree, relative: Path) -> bool:
    """Return whether *relative* is a folder already stored in *tree*."""
    key = relative.as_posix()
    return any(folder.relative_path.as_posix() == key for folder in tree.folders)


def _directory_files(
    stored: tuple[ProjectFile, ...],
    relative: Path,
) -> tuple[ProjectFile, ...]:
    """Return direct YAML children in stored relative-path order."""
    parent = relative.as_posix()
    return tuple(
        item
        for item in stored
        if item.relative_path.parent.as_posix() == parent
        if item.extension in YAML_EXTENSIONS
    )
