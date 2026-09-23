"""Tests for incremental change detection and dependency invalidation."""

from __future__ import annotations

import pytest

from ha_docgen.graph import DependencyGraph, GraphEdge, GraphNode
from ha_docgen.incremental import (
    CacheReadResult,
    CacheStatus,
    ChangeDetector,
    FileFingerprint,
    IncrementalCache,
    ProjectFingerprint,
)
from ha_docgen.relationships import ObjectType, RelationshipType


def _found(*files: FileFingerprint, fingerprint: str = "project") -> CacheReadResult:
    """Return a valid cache read result."""
    cache = IncrementalCache(ProjectFingerprint(fingerprint), files)
    return CacheReadResult(CacheStatus.FOUND, cache)


def test_change_detector_classifies_hash_path_and_deletion_changes() -> None:
    """Changed, added, deleted and unchanged paths are separated."""
    detector = ChangeDetector()
    current = (
        FileFingerprint("changed.yaml", "new"),
        FileFingerprint("new.yaml", "new"),
        FileFingerprint("same.yaml", "same"),
    )
    cached = _found(
        FileFingerprint("changed.yaml", "old"),
        FileFingerprint("deleted.yaml", "old"),
        FileFingerprint("same.yaml", "same"),
    )

    changes = detector.detect(current, cached, "project")

    assert changes.changed == ("changed.yaml",)
    assert changes.added == ("new.yaml",)
    assert changes.deleted == ("deleted.yaml",)
    assert changes.unchanged == ("same.yaml",)
    assert changes.files_to_process == ("changed.yaml", "new.yaml")
    assert changes.skipped == ("same.yaml",)
    assert changes.full_scan_required is False


@pytest.mark.parametrize(
    "cache",
    (
        CacheReadResult(CacheStatus.MISSING),
        CacheReadResult(CacheStatus.CORRUPT),
        _found(fingerprint="old"),
    ),
)
def test_change_detector_requires_full_scan_for_unusable_cache(
    cache: CacheReadResult,
) -> None:
    """Missing, corrupt and fingerprint-mismatched caches select all files."""
    current = (FileFingerprint("b.yaml", "b"), FileFingerprint("a.yaml", "a"))

    changes = ChangeDetector().detect(current, cache, "project")

    assert changes.full_scan_required is True
    assert changes.added == ("a.yaml", "b.yaml")
    assert changes.files_to_process == ("a.yaml", "b.yaml")


def test_change_detector_invalidates_transitive_dependents_from_existing_graph() -> None:
    """Incoming existing graph edges invalidate current dependent files."""
    changed = GraphNode(ObjectType.PACKAGE, "base.yaml")
    direct = GraphNode(ObjectType.PACKAGE, "direct.yaml")
    transitive = GraphNode(ObjectType.PACKAGE, "nested\\transitive.yaml")
    graph = DependencyGraph(
        nodes=(changed, direct, transitive),
        edges=(
            GraphEdge(direct, changed, RelationshipType.REFERENCES),
            GraphEdge(transitive, direct, RelationshipType.REFERENCES),
        ),
    )
    current = (
        FileFingerprint("base.yaml", "new"),
        FileFingerprint("direct.yaml", "same"),
        FileFingerprint("nested/transitive.yaml", "same"),
    )
    cached = _found(
        FileFingerprint("base.yaml", "old"),
        FileFingerprint("direct.yaml", "same"),
        FileFingerprint("nested/transitive.yaml", "same"),
    )

    changes = ChangeDetector().detect(current, cached, "project", graph)

    assert changes.invalidated == ("direct.yaml", "nested/transitive.yaml")
    assert changes.files_to_process == (
        "base.yaml",
        "direct.yaml",
        "nested/transitive.yaml",
    )
    assert changes.skipped == ()


def test_cache_read_result_requires_consistent_status_and_payload() -> None:
    """Only a found cache can carry cache data."""
    cache = IncrementalCache(ProjectFingerprint("project"))

    with pytest.raises(ValueError):
        CacheReadResult(CacheStatus.FOUND)
    with pytest.raises(ValueError):
        CacheReadResult(CacheStatus.MISSING, cache)
