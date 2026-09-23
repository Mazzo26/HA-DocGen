"""Canonical repository discovery.

FilesystemWalker is the only production walk. ScanPolicy filters those
entries. ProjectTreeBuilder returns the ProjectTree every consumer reads.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ..policy import ScanPolicy
from .builder import ProjectTreeBuilder
from .filesystem_entry import FilesystemEntry
from .tree import ProjectTree
from .walker import FilesystemWalker


def discover_project(
    root: Path,
    policy: ScanPolicy | None = None,
    walker: FilesystemWalker | None = None,
) -> ProjectTree:
    """Walk *root* once and return the policy-filtered ProjectTree."""
    active_policy = ScanPolicy() if policy is None else policy
    active_walker = walker if walker is not None else FilesystemWalker()
    entries = active_walker.walk(root)
    included = [entry for entry in entries if active_policy.is_included(entry.path)]
    return ProjectTreeBuilder().build(root, included)


def project_tree_from_files(root: Path, files: tuple[Path, ...]) -> ProjectTree:
    """Project an explicit file selection into a ProjectTree without walking."""
    entries = [entry for path in files for entry in _entries_for_path(root, path)]
    return ProjectTreeBuilder().build(root, entries)


def _entries_for_path(root: Path, path: Path) -> tuple[FilesystemEntry, ...]:
    """Return metadata for one file and its parent folders below *root*."""
    if not path.is_file() or not path.is_relative_to(root):
        return ()
    return tuple(_entry(root, candidate) for candidate in _chain(root, path))


def _chain(root: Path, path: Path) -> tuple[Path, ...]:
    """Return *path* and each parent strictly below *root*."""
    chain = [path]
    current = path.parent
    while current != root:
        chain.append(current)
        current = current.parent
    return tuple(chain)


def _entry(root: Path, path: Path) -> FilesystemEntry:
    """Read metadata for one already-known path."""
    stat = path.stat()
    return FilesystemEntry(
        path=path,
        relative_path=path.relative_to(root),
        name=path.name,
        is_file=path.is_file(),
        is_dir=path.is_dir(),
        extension=path.suffix.lower(),
        size=stat.st_size,
        modified=datetime.fromtimestamp(stat.st_mtime),
    )
