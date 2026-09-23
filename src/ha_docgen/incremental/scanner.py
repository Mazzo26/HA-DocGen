"""Incremental project file selection."""

from __future__ import annotations

from ..config import ProjectConfig
from ..graph import DependencyGraph
from ..policy import ScanPolicy
from .cache_store import CacheStore
from .change_detector import ChangeDetector
from .fingerprint import build_project_fingerprint
from .hasher import FileHasher
from .models import (
    CacheReadResult,
    CacheStatus,
    FileFingerprint,
    IncrementalCache,
    IncrementalScanResult,
)


class IncrementalScanner:
    """Determine which project files require processing."""

    def scan(
        self,
        config: ProjectConfig,
        *,
        force: bool = False,
        clean_cache: bool = False,
        dependencies: DependencyGraph | None = None,
    ) -> IncrementalScanResult:
        """Hash current files, compare cache and persist the new state."""
        cache_store = CacheStore()
        if clean_cache:
            cache_store.clean(config.cache)
        cache_read = cache_store.read(config.cache)
        current = self._fingerprints(config)
        project_fingerprint = build_project_fingerprint(config)
        comparison_cache = CacheReadResult(CacheStatus.MISSING) if force else cache_read
        changes = ChangeDetector().detect(
            current,
            comparison_cache,
            project_fingerprint.value,
            dependencies,
        )
        cache_store.write(
            config.cache,
            IncrementalCache(project_fingerprint, current),
        )
        return IncrementalScanResult(current, changes, cache_read.status)

    @staticmethod
    def _fingerprints(config: ProjectConfig) -> tuple[FileFingerprint, ...]:
        """Discover included files once and hash them in path order."""
        policy = ScanPolicy()
        cache_path = config.cache.resolve()
        paths = (
            path
            for path in config.root.rglob("*")
            if path.is_file() and path.resolve() != cache_path and policy.is_included(path)
        )
        ordered = sorted(paths, key=lambda path: path.relative_to(config.root).as_posix())
        hasher = FileHasher()
        return tuple(
            FileFingerprint(
                path.relative_to(config.root).as_posix(),
                hasher.hash(path),
            )
            for path in ordered
        )
