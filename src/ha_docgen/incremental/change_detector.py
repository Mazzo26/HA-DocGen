"""Comparison and existing-graph invalidation for incremental execution."""

from __future__ import annotations

from pathlib import PurePosixPath

from ..graph import DependencyGraph, GraphNode
from .models import CacheReadResult, CacheStatus, ChangeSet, FileFingerprint


class ChangeDetector:
    """Compare current fingerprints with a previously read cache."""

    def detect(
        self,
        current: tuple[FileFingerprint, ...],
        cached: CacheReadResult,
        project_fingerprint: str,
        dependencies: DependencyGraph | None = None,
    ) -> ChangeSet:
        """Return deterministic file changes and dependent invalidations."""
        current_by_path = {item.relative_path: item.file_hash for item in current}
        if self._requires_full_scan(cached, project_fingerprint):
            return ChangeSet(
                added=tuple(current_by_path),
                full_scan_required=True,
            )
        previous_by_path = {item.relative_path: item.file_hash for item in cached.cache.files}
        changes = self._compare(current_by_path, previous_by_path)
        invalidated = self._invalidate(changes, dependencies, frozenset(current_by_path))
        return ChangeSet(
            changed=changes.changed,
            added=changes.added,
            deleted=changes.deleted,
            unchanged=changes.unchanged,
            invalidated=invalidated,
        )

    @staticmethod
    def _requires_full_scan(cached: CacheReadResult, fingerprint: str) -> bool:
        """Return whether cache state cannot support an incremental scan."""
        return (
            cached.status is not CacheStatus.FOUND
            or cached.cache.project_fingerprint.value != fingerprint
        )

    @staticmethod
    def _compare(
        current: dict[str, str],
        previous: dict[str, str],
    ) -> ChangeSet:
        """Compare two path-to-hash mappings."""
        shared = current.keys() & previous.keys()
        return ChangeSet(
            changed=tuple(path for path in shared if current[path] != previous[path]),
            added=tuple(current.keys() - previous.keys()),
            deleted=tuple(previous.keys() - current.keys()),
            unchanged=tuple(path for path in shared if current[path] == previous[path]),
        )

    def _invalidate(
        self,
        changes: ChangeSet,
        graph: DependencyGraph | None,
        current_paths: frozenset[str],
    ) -> tuple[str, ...]:
        """Use incoming edges from the existing graph to find dependents."""
        if graph is None:
            return ()
        changed_paths = frozenset((*changes.changed, *changes.added, *changes.deleted))
        pending = [node for node in graph.nodes if _normalized_node_path(node) in changed_paths]
        invalidated: set[str] = set()
        visited: set[GraphNode] = set(pending)
        while pending:
            node = pending.pop()
            for edge in graph.incoming(node):
                dependent = edge.source
                path = _normalized_node_path(dependent)
                if path in current_paths and path not in changed_paths:
                    invalidated.add(path)
                if dependent not in visited:
                    visited.add(dependent)
                    pending.append(dependent)
        return tuple(sorted(invalidated))


def _normalized_node_path(node: GraphNode) -> str:
    """Normalize an existing graph node identifier as a relative path."""
    return PurePosixPath(node.object_id.replace("\\", "/")).as_posix()
