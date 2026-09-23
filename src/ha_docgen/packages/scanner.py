"""Discover and load Home Assistant package YAML files.

Reads package files from a ProjectTree and loads each via YamlLoader.
Performs no domain interpretation.
"""

from __future__ import annotations

from pathlib import Path

from ..constants import YAML_EXTENSIONS
from ..policy import ScanPolicy
from ..project import ProjectTree, discover_project, files_under
from ..yaml import YamlDocument, YamlLoader


class PackageScanner:
    """Load package YAML files discovered in a ProjectTree."""

    def __init__(self, loader: YamlLoader) -> None:
        self._loader = loader

    def scan(
        self,
        path: Path,
        tree: ProjectTree | None = None,
    ) -> tuple[YamlDocument, ...]:
        """Load every YAML file under *path* into YamlDocuments."""
        project = tree if tree is not None else self._tree(path)
        return tuple(
            self._loader.load(item.path)
            for item in files_under(project, path)
            if item.extension in YAML_EXTENSIONS
        )

    @staticmethod
    def _tree(path: Path) -> ProjectTree:
        """Discover *path* when the caller has no ProjectTree yet."""
        if not path.is_dir():
            return ProjectTree(root=path)
        return discover_project(path, ScanPolicy())
