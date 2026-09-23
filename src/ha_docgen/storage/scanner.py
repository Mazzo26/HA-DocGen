"""Read-only storage filesystem scanner.

Discovers every file under the configured storage root and builds a
StorageInventory. Reuses ProjectTree / FilesystemEntry metadata when
available so the filesystem is not walked again.

Performs no JSON parsing and no Home Assistant registry logic.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

from ..constants import FOLDER_STORAGE
from ..logging import Logger, get_logger
from ..policy import ScanPolicy
from ..project import (
    FilesystemEntry,
    ProjectFile,
    ProjectTree,
    discover_project,
    project_files,
)
from ..project.walker import FilesystemWalker
from .inventory import StorageInventory
from .models import StorageFile


class StorageScanner:
    """Discover storage files and build a StorageInventory.

    Read-only: never mutates the filesystem or parses file contents.
    """

    def __init__(
        self,
        storage_root: Path,
        policy: ScanPolicy | None = None,
        logger: Logger | None = None,
        walker: FilesystemWalker | None = None,
    ) -> None:
        self.storage_root = storage_root
        self.policy = policy if policy is not None else ScanPolicy()
        self.logger = logger if logger is not None else get_logger()
        self.walker = walker if walker is not None else FilesystemWalker()

    def scan(self) -> StorageInventory:
        """Discover storage files through the canonical ProjectTree."""
        if not self.storage_root.is_dir():
            self.logger.warning(f"Storage root missing: {self.storage_root}")
            return StorageInventory(storage_root=self.storage_root)

        tree = discover_project(self.storage_root, self.policy, self.walker)
        files = [self._from_storage_tree_file(item) for item in project_files(tree)]
        return self._inventory(files)

    def scan_from_tree(self, tree: ProjectTree) -> StorageInventory:
        """Build an inventory from ProjectTree without filesystem I/O."""
        files = [
            self._from_project_file(project_file)
            for project_file in self._iter_tree_storage_files(tree)
            if self.policy.is_included(project_file.path)
        ]
        return self._inventory(files)

    def scan_from_entries(
        self,
        entries: Sequence[FilesystemEntry],
        *,
        root: Path | None = None,
    ) -> StorageInventory:
        """Build an inventory from FilesystemEntry objects.

        When *root* is the storage directory itself (walker scoped to
        storage), every file entry is a storage file. Otherwise entries
        are filtered to paths under ``FOLDER_STORAGE``.
        """
        storage_files = [
            self._from_entry(entry, root=root)
            for entry in entries
            if self._is_storage_file_entry(entry, root=root)
            and self.policy.is_included(entry.path)
        ]
        return self._inventory(storage_files)

    def _inventory(self, files: list[StorageFile]) -> StorageInventory:
        """Sort files and wrap them in a StorageInventory."""
        files.sort(key=lambda item: item.relative_path.as_posix())
        self.logger.debug(
            f"Storage inventory: {len(files)} file(s) under {self.storage_root}"
        )
        return StorageInventory(storage_root=self.storage_root, files=files)

    def _iter_tree_storage_files(
        self,
        tree: ProjectTree,
    ) -> Iterable[ProjectFile]:
        """Yield ProjectFile objects that live under the storage root."""
        for folder in tree.folders:
            if not self._is_under_storage(folder.relative_path):
                continue
            yield from folder.files

    def _is_storage_file_entry(
        self,
        entry: FilesystemEntry,
        *,
        root: Path | None,
    ) -> bool:
        """Return True when the entry is a file inside storage scope."""
        if not entry.is_file:
            return False
        if root is not None and root == self.storage_root:
            return True
        return self._is_under_storage(entry.relative_path)

    @staticmethod
    def _is_under_storage(relative_path: Path) -> bool:
        """Return True when relative_path is under ``.storage``."""
        parts = relative_path.parts
        return bool(parts) and parts[0] == FOLDER_STORAGE

    def _from_entry(
        self,
        entry: FilesystemEntry,
        *,
        root: Path | None,
    ) -> StorageFile:
        """Convert a FilesystemEntry into a StorageFile."""
        relative_path = self._relative_for_entry(entry, root=root)
        return StorageFile(
            name=entry.name,
            path=entry.path,
            relative_path=relative_path,
            size=entry.size,
            modified=entry.modified,
        )

    def _relative_for_entry(
        self,
        entry: FilesystemEntry,
        *,
        root: Path | None,
    ) -> Path:
        """Resolve StorageFile.relative_path relative to the project root."""
        if root is not None and root == self.storage_root:
            return Path(self.storage_root.name) / entry.relative_path
        return entry.relative_path

    def _from_storage_tree_file(self, project_file: ProjectFile) -> StorageFile:
        """Convert a storage-rooted ProjectFile into a StorageFile."""
        return StorageFile(
            name=project_file.name,
            path=project_file.path,
            relative_path=Path(self.storage_root.name) / project_file.relative_path,
            size=project_file.size,
            modified=project_file.modified,
        )

    @staticmethod
    def _from_project_file(project_file: ProjectFile) -> StorageFile:
        """Convert a ProjectFile into a StorageFile."""
        return StorageFile(
            name=project_file.name,
            path=project_file.path,
            relative_path=project_file.relative_path,
            size=project_file.size,
            modified=project_file.modified,
        )
