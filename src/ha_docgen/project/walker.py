"""
Filesystem Walker.

Leest de volledige Home Assistant configuratie en zet alle bestanden
en mappen om naar FilesystemEntry objecten.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from .filesystem_entry import FilesystemEntry


class FilesystemWalker:
    """Leest de volledige projectstructuur."""

    def walk(self, root: Path) -> list[FilesystemEntry]:

        entries: list[FilesystemEntry] = []

        for path in root.rglob("*"):

            stat = path.stat()

            entries.append(
                FilesystemEntry(
                    path=path,
                    relative_path=path.relative_to(root),
                    name=path.name,
                    is_file=path.is_file(),
                    is_dir=path.is_dir(),
                    extension=path.suffix.lower(),
                    size=stat.st_size,
                    modified=datetime.fromtimestamp(stat.st_mtime, UTC),
                )
            )

        return entries