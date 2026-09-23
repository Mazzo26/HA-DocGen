"""Platform-independent content hashing for project files."""

from __future__ import annotations

import hashlib
from pathlib import Path


class FileHasher:
    """Calculate a SHA-256 digest without retaining state."""

    def hash(self, path: Path) -> str:
        """Return the SHA-256 digest of the file's exact bytes."""
        digest = hashlib.sha256()
        with path.open("rb") as file:
            while chunk := file.read(64 * 1024):
                digest.update(chunk)
        return digest.hexdigest()
