"""Tests for deterministic incremental cache persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.ha_docgen.incremental import (
    CACHE_FORMAT_VERSION,
    CacheStatus,
    CacheStore,
    FileFingerprint,
    IncrementalCache,
    ProjectFingerprint,
)


def _cache(*files: FileFingerprint) -> IncrementalCache:
    """Build a cache with a stable project fingerprint."""
    return IncrementalCache(ProjectFingerprint("project"), files)


def test_cache_store_reads_and_writes_deterministically(tmp_path: Path) -> None:
    """Equivalent cache data produces identical sorted JSON."""
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    store = CacheStore()
    a = FileFingerprint("a.yaml", "a")
    b = FileFingerprint("nested/b.yaml", "b")

    store.write(first, _cache(b, a))
    store.write(second, _cache(a, b))

    assert first.read_bytes() == second.read_bytes()
    result = store.read(first)
    assert result.status is CacheStatus.FOUND
    assert result.cache == _cache(a, b)


def test_cache_store_reports_missing_corrupt_and_unsupported_cache(
    tmp_path: Path,
) -> None:
    """Unreadable cache states never leak partial payloads."""
    store = CacheStore()
    path = tmp_path / "cache.json"

    assert store.read(path).status is CacheStatus.MISSING
    path.write_text("{", encoding="utf-8")
    assert store.read(path).status is CacheStatus.CORRUPT
    path.write_text(
        f'{{"version": {CACHE_FORMAT_VERSION + 1}}}',
        encoding="utf-8",
    )
    assert store.read(path).status is CacheStatus.CORRUPT


@pytest.mark.parametrize(
    "contents",
    (
        "[]",
        '{"version":1,"project_fingerprint":1,"files":[]}',
        '{"version":1,"project_fingerprint":"x","files":[1]}',
        ('{"version":1,"project_fingerprint":"x","files":[{"relative_path":"a","file_hash":1}]}'),
    ),
)
def test_cache_store_rejects_invalid_file_fields(
    tmp_path: Path,
    contents: str,
) -> None:
    """Structurally invalid cached files are reported as corrupt."""
    path = tmp_path / "cache.json"
    path.write_text(contents, encoding="utf-8")

    assert CacheStore().read(path).status is CacheStatus.CORRUPT


def test_cache_store_wraps_read_errors_as_corrupt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expected cache read failures have a stable status."""
    path = tmp_path / "cache.json"
    path.touch()
    monkeypatch.setattr(
        Path, "read_text", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError())
    )

    assert CacheStore().read(path).status is CacheStatus.CORRUPT


def test_cache_store_clean_is_idempotent(tmp_path: Path) -> None:
    """Cleaning existing and missing cache files succeeds."""
    path = tmp_path / "cache.json"
    path.touch()

    CacheStore().clean(path)
    CacheStore().clean(path)

    assert not path.exists()


@pytest.mark.parametrize(
    ("path", "file_hash"),
    (("", "hash"), ("../secret", "hash"), ("/absolute", "hash"), ("a\\b", "hash"), ("a", "")),
)
def test_file_fingerprint_rejects_invalid_values(path: str, file_hash: str) -> None:
    """Cache entries contain only safe relative POSIX paths and hashes."""
    with pytest.raises(ValueError):
        FileFingerprint(path, file_hash)


def test_cache_models_reject_invalid_payload_combinations() -> None:
    """Immutable cache models enforce their invariants."""
    with pytest.raises(ValueError):
        ProjectFingerprint("")
    duplicate = FileFingerprint("same.yaml", "hash")
    with pytest.raises(ValueError, match="duplicate"):
        IncrementalCache(ProjectFingerprint("project"), (duplicate, duplicate))
