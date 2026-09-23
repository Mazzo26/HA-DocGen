"""Report configured Home Assistant folders from a ProjectTree."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ..models import FolderInfo
from ..policy import ScanPolicy
from ..project import (
    ProjectTree,
    discover_project,
    files_under,
    folder_exists,
    project_tree_from_files,
)


class _FolderConfig(Protocol):
    """Configured folders required by folder discovery."""

    packages: Path
    dashboards: Path
    esphome: Path
    themes: Path
    custom_components: Path
    www: Path
    storage: Path


class FolderDiscoveryScanner:
    """Adapt a ProjectTree into configured-folder summaries."""

    def __init__(self, config: _FolderConfig) -> None:
        self.config = config

    def scan(
        self,
        files: tuple[Path, ...] | None = None,
        tree: ProjectTree | None = None,
    ) -> list[FolderInfo]:
        """Describe each configured folder using *tree*."""
        project = tree if tree is not None else self._discover(files)
        selected = _selection(files)
        return [
            self._info(project, name, path, selected, files is None)
            for name, path in self._targets()
        ]

    def _discover(self, files: tuple[Path, ...] | None) -> ProjectTree:
        """Build a complete tree, or project an explicit selection."""
        root = self._root()
        if files is None:
            return discover_project(root, ScanPolicy())
        return project_tree_from_files(root, files)

    def _root(self) -> Path:
        """Return the project root stored on the configuration."""
        root = getattr(self.config, "root", None)
        if isinstance(root, Path):
            return root
        return self.config.packages.parent

    def _targets(self) -> tuple[tuple[str, Path], ...]:
        """Return configured folders in the stable report order."""
        return (
            ("Packages", self.config.packages),
            ("Dashboards", self.config.dashboards),
            ("ESPHome", self.config.esphome),
            ("Themes", self.config.themes),
            ("Custom Components", self.config.custom_components),
            ("WWW", self.config.www),
            ("Storage", self.config.storage),
        )

    @staticmethod
    def _info(
        tree: ProjectTree,
        name: str,
        path: Path,
        selected: frozenset[Path] | None,
        complete: bool,
    ) -> FolderInfo:
        """Build one folder summary from stored files."""
        visible = [
            item
            for item in files_under(tree, path)
            if _is_selected(item.path, selected)
        ]
        return FolderInfo(
            name=name,
            path=path,
            exists=_exists(tree, path, complete),
            file_count=len(visible),
        )


def _selection(files: tuple[Path, ...] | None) -> frozenset[Path] | None:
    """Resolve an explicit selection, or return None for a complete tree."""
    if files is None:
        return None
    return frozenset(path.resolve() for path in files)


def _is_selected(path: Path, selected: frozenset[Path] | None) -> bool:
    """Return whether *path* belongs to the active selection."""
    if selected is None:
        return True
    return path.resolve() in selected


def _exists(tree: ProjectTree, path: Path, complete: bool) -> bool:
    """Read folder presence from the tree.

    A partial selection does not contain every configured folder. Directory
    status then preserves the previous incremental report.
    """
    if folder_exists(tree, path):
        return True
    if complete:
        return False
    return path.is_dir()
