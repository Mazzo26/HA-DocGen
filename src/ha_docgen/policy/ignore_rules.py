"""Default and configurable filesystem ignore rules.

Owns the rule sets that ScanPolicy evaluates. Does not parse .gitignore,
apply include rules, or load user configuration (later modules).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path

from ..constants import IGNORE_DIRS

DEFAULT_IGNORED_DIRECTORIES: frozenset[str] = IGNORE_DIRS
DEFAULT_IGNORED_FILENAMES: frozenset[str] = frozenset()
DEFAULT_IGNORED_FILENAME_PATTERNS: frozenset[str] = frozenset()


@dataclass(slots=True, frozen=True)
class IgnoreRules:
    """Filesystem paths and names that should be excluded from a scan.

    Read-only: rule sets are immutable after construction.
    """

    directories: frozenset[str] = field(
        default_factory=lambda: DEFAULT_IGNORED_DIRECTORIES
    )
    filenames: frozenset[str] = field(
        default_factory=lambda: DEFAULT_IGNORED_FILENAMES
    )
    filename_patterns: frozenset[str] = field(
        default_factory=lambda: DEFAULT_IGNORED_FILENAME_PATTERNS
    )

    def matches(self, path: Path) -> bool:
        """Return True when the path matches any ignore rule."""
        if any(part in self.directories for part in path.parts):
            return True

        name = path.name
        if name in self.filenames:
            return True

        return any(fnmatch(name, pattern) for pattern in self.filename_patterns)
