"""Count repository content from an existing ProjectTree."""

from __future__ import annotations

from pathlib import Path

from ..constants import (
    EXTENSION_JSON,
    EXTENSION_PYTHON,
    FOLDER_CUSTOM_COMPONENTS,
    FOLDER_DASHBOARDS,
    FOLDER_ESPHOME,
    FOLDER_PACKAGES,
    FOLDER_THEMES,
    YAML_EXTENSIONS,
)
from ..models import ScanResult
from ..policy import ScanPolicy
from ..project import ProjectTree, discover_project, files_under, project_files, project_tree_from_files


class FilesystemScanner:
    """Adapt a ProjectTree into repository file statistics."""

    def __init__(self, root: Path, policy: ScanPolicy) -> None:
        self.root = root
        self.policy = policy

    def scan(
        self,
        files: tuple[Path, ...] | None = None,
        tree: ProjectTree | None = None,
    ) -> ScanResult:
        """Count files in *tree*, optionally limited to an explicit selection."""
        project = self._project(files, tree)
        return self._result(project, _selection(files))

    def _project(
        self,
        files: tuple[Path, ...] | None,
        tree: ProjectTree | None,
    ) -> ProjectTree:
        """Reuse *tree* or build one without a second repository walk."""
        if tree is not None:
            return tree
        if files is not None:
            return project_tree_from_files(self.root, files)
        return discover_project(self.root, self.policy)

    def _result(
        self,
        tree: ProjectTree,
        selected: frozenset[Path] | None,
    ) -> ScanResult:
        """Fill global totals and configured feature counts from *tree*."""
        result = ScanResult(root=self.root)
        self._count_extensions(result, tree, selected)
        self._count_features(result, tree, selected)
        return result

    def _count_extensions(
        self,
        result: ScanResult,
        tree: ProjectTree,
        selected: frozenset[Path] | None,
    ) -> None:
        """Count included files by extension."""
        for project_file in project_files(tree):
            if not _is_selected(project_file.path, selected):
                continue
            if self.policy.is_excluded(project_file.path):
                continue
            _count_extension(result, project_file.extension)

    def _count_features(
        self,
        result: ScanResult,
        tree: ProjectTree,
        selected: frozenset[Path] | None,
    ) -> None:
        """Count YAML features and immediate custom-component folders."""
        result.package_count = _yaml_count(tree, self.root / FOLDER_PACKAGES, selected)
        result.dashboard_count = _yaml_count(tree, self.root / FOLDER_DASHBOARDS, selected)
        result.esphome_count = _yaml_count(tree, self.root / FOLDER_ESPHOME, selected)
        result.theme_count = _yaml_count(tree, self.root / FOLDER_THEMES, selected)
        result.custom_component_count = _component_count(
            tree,
            self.root / FOLDER_CUSTOM_COMPONENTS,
            selected,
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


def _count_extension(result: ScanResult, extension: str) -> None:
    """Increment the statistic that matches one file extension."""
    if extension in YAML_EXTENSIONS:
        result.yaml_files += 1
    elif extension == EXTENSION_JSON:
        result.json_files += 1
    elif extension == EXTENSION_PYTHON:
        result.python_files += 1


def _yaml_count(
    tree: ProjectTree,
    folder: Path,
    selected: frozenset[Path] | None,
) -> int:
    """Count YAML files stored below *folder*."""
    return sum(
        1
        for item in files_under(tree, folder)
        if item.extension in YAML_EXTENSIONS and _is_selected(item.path, selected)
    )


def _component_count(
    tree: ProjectTree,
    folder: Path,
    selected: frozenset[Path] | None,
) -> int:
    """Count custom components from folders, or from a file selection."""
    if selected is None:
        return _child_folder_count(tree, folder)
    resolved = folder.resolve()
    names = {
        item.path.resolve().relative_to(resolved).parts[0]
        for item in files_under(tree, folder)
        if _is_selected(item.path, selected)
    }
    return len(names)


def _child_folder_count(tree: ProjectTree, folder: Path) -> int:
    """Count immediate child folders already present in *tree*."""
    resolved = folder.resolve()
    return sum(1 for item in tree.folders if item.path.resolve().parent == resolved)
