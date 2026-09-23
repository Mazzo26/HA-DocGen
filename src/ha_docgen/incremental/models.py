"""Immutable models for deterministic incremental execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

CACHE_FORMAT_VERSION = 1


class CacheStatus(StrEnum):
    """Outcome of reading an incremental cache."""

    FOUND = "found"
    MISSING = "missing"
    CORRUPT = "corrupt"


@dataclass(frozen=True, slots=True)
class ProjectFingerprint:
    """Hash representing configuration relevant to project processing."""

    value: str

    def __post_init__(self) -> None:
        """Require a non-empty fingerprint."""
        if not self.value:
            raise ValueError("Project fingerprint cannot be empty.")


@dataclass(frozen=True, slots=True)
class FileFingerprint:
    """Hash and normalized relative path for one project file."""

    relative_path: str
    file_hash: str

    def __post_init__(self) -> None:
        """Require a safe POSIX-relative path and non-empty hash."""
        path = PurePosixPath(self.relative_path)
        if path.is_absolute() or ".." in path.parts or self.relative_path in ("", "."):
            raise ValueError("File fingerprint path must be relative.")
        if "\\" in self.relative_path:
            raise ValueError("File fingerprint path must use POSIX separators.")
        if not self.file_hash:
            raise ValueError("File hash cannot be empty.")


@dataclass(frozen=True, slots=True)
class IncrementalCache:
    """Versioned deterministic cache payload."""

    project_fingerprint: ProjectFingerprint
    files: tuple[FileFingerprint, ...] = ()
    version: int = CACHE_FORMAT_VERSION

    def __post_init__(self) -> None:
        """Sort and reject duplicate file paths."""
        ordered = tuple(sorted(self.files, key=lambda item: item.relative_path))
        if len({item.relative_path for item in ordered}) != len(ordered):
            raise ValueError("Cache contains duplicate file paths.")
        object.__setattr__(self, "files", ordered)


@dataclass(frozen=True, slots=True)
class CacheReadResult:
    """Cache read status and optional valid payload."""

    status: CacheStatus
    cache: IncrementalCache | None = None

    def __post_init__(self) -> None:
        """Keep status and payload consistent."""
        if (self.status is CacheStatus.FOUND) != (self.cache is not None):
            raise ValueError("Only a found cache may contain a payload.")


@dataclass(frozen=True, slots=True)
class ChangeSet:
    """Deterministic comparison between current files and cached files."""

    changed: tuple[str, ...] = ()
    added: tuple[str, ...] = ()
    deleted: tuple[str, ...] = ()
    unchanged: tuple[str, ...] = ()
    invalidated: tuple[str, ...] = ()
    full_scan_required: bool = False

    def __post_init__(self) -> None:
        """Sort and deduplicate every path collection."""
        for name in ("changed", "added", "deleted", "unchanged", "invalidated"):
            values = tuple(sorted(set(getattr(self, name))))
            object.__setattr__(self, name, values)

    @property
    def files_to_process(self) -> tuple[str, ...]:
        """Return changed, added and dependent current files."""
        return tuple(sorted({*self.changed, *self.added, *self.invalidated}))

    @property
    def skipped(self) -> tuple[str, ...]:
        """Return unchanged files not invalidated by dependencies."""
        return tuple(path for path in self.unchanged if path not in self.invalidated)


@dataclass(frozen=True, slots=True)
class IncrementalScanResult:
    """Current fingerprints and the resulting incremental work selection."""

    files: tuple[FileFingerprint, ...]
    changes: ChangeSet
    cache_status: CacheStatus

    def __post_init__(self) -> None:
        """Store current files in deterministic path order."""
        object.__setattr__(
            self,
            "files",
            tuple(sorted(self.files, key=lambda item: item.relative_path)),
        )
