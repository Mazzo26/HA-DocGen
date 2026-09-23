"""Deterministic JSON persistence for incremental cache data."""

from __future__ import annotations

import json
from pathlib import Path

from ..constants import DEFAULT_ENCODING
from .models import (
    CACHE_FORMAT_VERSION,
    CacheReadResult,
    CacheStatus,
    FileFingerprint,
    IncrementalCache,
    ProjectFingerprint,
)


class CacheStore:
    """Read, write and remove one configured cache file."""

    def read(self, path: Path) -> CacheReadResult:
        """Return a valid cache or a deterministic missing/corrupt status."""
        if not path.exists():
            return CacheReadResult(CacheStatus.MISSING)
        try:
            raw = json.loads(path.read_text(encoding=DEFAULT_ENCODING))
            cache = self._decode(raw)
        except (OSError, ValueError, TypeError, KeyError):
            return CacheReadResult(CacheStatus.CORRUPT)
        return CacheReadResult(CacheStatus.FOUND, cache)

    def write(self, path: Path, cache: IncrementalCache) -> None:
        """Write cache JSON with stable ordering and formatting."""
        path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(
            self._encode(cache),
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        path.write_text(f"{serialized}\n", encoding=DEFAULT_ENCODING, newline="\n")

    def clean(self, path: Path) -> None:
        """Remove a cache when present."""
        path.unlink(missing_ok=True)

    @staticmethod
    def _encode(cache: IncrementalCache) -> dict[str, object]:
        """Convert a cache model to JSON-compatible primitives."""
        return {
            "files": [
                {
                    "file_hash": item.file_hash,
                    "relative_path": item.relative_path,
                }
                for item in cache.files
            ],
            "project_fingerprint": cache.project_fingerprint.value,
            "version": cache.version,
        }

    @staticmethod
    def _decode(raw: object) -> IncrementalCache:
        """Validate primitives and build an immutable cache model."""
        if not isinstance(raw, dict) or raw["version"] != CACHE_FORMAT_VERSION:
            raise ValueError("Unsupported cache format.")
        fingerprint = raw["project_fingerprint"]
        files = raw["files"]
        if not isinstance(fingerprint, str) or not isinstance(files, list):
            raise TypeError("Invalid cache fields.")
        return IncrementalCache(
            project_fingerprint=ProjectFingerprint(fingerprint),
            files=tuple(CacheStore._decode_file(item) for item in files),
            version=CACHE_FORMAT_VERSION,
        )

    @staticmethod
    def _decode_file(raw: object) -> FileFingerprint:
        """Validate and decode one cached file."""
        if not isinstance(raw, dict):
            raise TypeError("Invalid cached file.")
        relative_path = raw["relative_path"]
        file_hash = raw["file_hash"]
        if not isinstance(relative_path, str) or not isinstance(file_hash, str):
            raise TypeError("Invalid cached file fields.")
        return FileFingerprint(relative_path, file_hash)
