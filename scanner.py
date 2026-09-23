from pathlib import Path

from .config import ProjectConfig
from .models import HomeAssistantModel
from .policy import ScanPolicy
from .project import ProjectTree, discover_project, project_tree_from_files
from .scanners.filesystem import FilesystemScanner
from .scanners.folder_discovery import FolderDiscoveryScanner


class Scanner:
    """Project one ProjectTree into the legacy scan model."""

    def __init__(self, config: ProjectConfig) -> None:
        self.config = config

    def scan(self, files: tuple[Path, ...] | None = None) -> HomeAssistantModel:
        """Build one ProjectTree and read every scanner result from it."""
        policy = ScanPolicy()
        tree = self._tree(policy, files)
        filesystem = FilesystemScanner(self.config.root, policy).scan(files, tree)
        model = HomeAssistantModel(scan=filesystem)
        model.folders = FolderDiscoveryScanner(self.config).scan(files, tree)
        return model

    def _tree(
        self,
        policy: ScanPolicy,
        files: tuple[Path, ...] | None,
    ) -> ProjectTree:
        """Walk once, or project an explicit selection without walking."""
        if files is None:
            return discover_project(self.config.root, policy)
        return project_tree_from_files(self.config.root, files)
