"""Storage inventory access layer.

Central read-only API over discovered storage files. Future registry
parsers must query this inventory instead of scanning the filesystem.

Does not parse JSON or interpret Home Assistant semantics.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from .models import StorageFile


@dataclass(slots=True)
class StorageInventory:
    """Read-only inventory of files under the storage root.

    Built by ``StorageScanner``. Provides O(1) lookup by filename and
    iteration over the discovered collection.
    """

    storage_root: Path
    files: Sequence[StorageFile] = ()
    _by_name: Mapping[str, StorageFile] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """Freeze the file list and build the filename index."""
        files = tuple(self.files)
        self.files = files
        self._by_name = MappingProxyType(
            {storage_file.name: storage_file for storage_file in files}
        )

    def get(self, name: str) -> StorageFile | None:
        """Return the storage file with the given filename, if present."""
        return self._by_name.get(name)

    def has(self, name: str) -> bool:
        """Return True when a storage file with the given filename exists."""
        return name in self._by_name

    def all_files(self) -> tuple[StorageFile, ...]:
        """Return every discovered storage file."""
        return tuple(self.files)

    def __iter__(self) -> Iterator[StorageFile]:
        """Iterate over all discovered storage files."""
        return iter(self.files)

    def __len__(self) -> int:
        """Return the number of discovered storage files."""
        return len(self.files)

    def __contains__(self, name: str) -> bool:
        """Return True when *name* is a known storage filename."""
        return name in self._by_name
