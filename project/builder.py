"""
ProjectTree Builder.
"""

from __future__ import annotations

from pathlib import Path

from ..constants import ROOT_RELATIVE

from .filesystem_entry import FilesystemEntry
from .tree import ProjectFile, ProjectFolder, ProjectTree


class ProjectTreeBuilder:
    """Bouwt een ProjectTree vanuit FilesystemEntry-objecten."""

    def build(
        self,
        root: Path,
        entries: list[FilesystemEntry],
    ) -> ProjectTree:
        """Zet filesystem-entries om naar een volledig gevulde ProjectTree."""
        tree = ProjectTree(root=root)
        unique = self._unique_entries(entries)
        folders_by_path = self._create_folders(root, unique)
        self._link_folders(folders_by_path)
        self._attach_files(unique, folders_by_path)
        self._sort_children(folders_by_path)
        tree.folders = self._ordered_folders(folders_by_path)
        return tree

    @staticmethod
    def _unique_entries(entries: list[FilesystemEntry]) -> list[FilesystemEntry]:
        """Bewaar de eerste entry per relatief pad, in padvolgorde."""
        ordered = sorted(entries, key=lambda entry: entry.relative_path.as_posix())
        seen: set[str] = set()
        unique: list[FilesystemEntry] = []
        for entry in ordered:
            key = entry.relative_path.as_posix()
            if key in seen:
                continue
            seen.add(key)
            unique.append(entry)
        return unique

    def _create_folders(
        self,
        root: Path,
        entries: list[FilesystemEntry],
    ) -> dict[Path, ProjectFolder]:
        """Maakt alle ProjectFolder-objecten inclusief de repository-root."""
        folders: dict[Path, ProjectFolder] = {
            ROOT_RELATIVE: self._create_root_folder(root),
        }

        for entry in entries:
            if not entry.is_dir:
                continue

            folders[entry.relative_path] = ProjectFolder(
                name=entry.name,
                path=entry.path,
                relative_path=entry.relative_path,
            )

        return folders

    @staticmethod
    def _create_root_folder(root: Path) -> ProjectFolder:
        """Maakt de ProjectFolder voor de repository-root."""
        return ProjectFolder(
            name=root.name,
            path=root,
            relative_path=ROOT_RELATIVE,
        )

    def _link_folders(
        self,
        folders_by_path: dict[Path, ProjectFolder],
    ) -> None:
        """Koppelt parent- en childrelaties tussen folders."""
        for relative_path, folder in folders_by_path.items():
            if relative_path == ROOT_RELATIVE:
                continue

            parent = folders_by_path[relative_path.parent]
            folder.parent = parent
            parent.subfolders.append(folder)

    def _attach_files(
        self,
        entries: list[FilesystemEntry],
        folders_by_path: dict[Path, ProjectFolder],
    ) -> None:
        """Maakt ProjectFile-objecten en koppelt ze aan hun parent-folder."""
        for entry in entries:
            if not entry.is_file:
                continue

            parent = folders_by_path[entry.relative_path.parent]
            parent.files.append(self._to_project_file(entry))

    @staticmethod
    def _to_project_file(entry: FilesystemEntry) -> ProjectFile:
        """Converteert één FilesystemEntry naar een ProjectFile."""
        return ProjectFile(
            name=entry.name,
            path=entry.path,
            relative_path=entry.relative_path,
            extension=entry.extension,
            size=entry.size,
            modified=entry.modified,
        )

    @staticmethod
    def _sort_children(folders_by_path: dict[Path, ProjectFolder]) -> None:
        """Sorteer bestanden en submappen op relatief POSIX-pad."""
        for folder in folders_by_path.values():
            folder.files.sort(key=lambda item: item.relative_path.as_posix())
            folder.subfolders.sort(key=lambda item: item.relative_path.as_posix())

    @staticmethod
    def _ordered_folders(
        folders_by_path: dict[Path, ProjectFolder],
    ) -> list[ProjectFolder]:
        """Geeft alle folders terug, root eerst, daarna op relatief pad."""
        root_folder = folders_by_path[ROOT_RELATIVE]
        child_folders = [
            folder
            for path, folder in folders_by_path.items()
            if path != ROOT_RELATIVE
        ]
        child_folders.sort(key=lambda item: item.relative_path.as_posix())
        return [root_folder, *child_folders]
