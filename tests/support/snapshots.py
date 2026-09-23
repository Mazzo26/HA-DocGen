"""Snapshot helper infrastructure.

Stores and compares normalised text. This module does not define snapshot
tests and does not ship golden files.
"""

from __future__ import annotations

from pathlib import Path

from tools.ha_docgen.constants import DEFAULT_ENCODING

from .assertions import assert_text_equal
from .compare import normalise_text
from .paths import require_relative_path


def snapshot_path(directory: Path, name: str) -> Path:
    """Return the snapshot file for a relative name inside ``directory``."""
    return directory / require_relative_path(name)


def read_snapshot(path: Path) -> str:
    """Read a snapshot file as UTF-8 text."""
    return path.read_text(encoding=DEFAULT_ENCODING)


def write_snapshot(path: Path, content: str) -> None:
    """Write normalised snapshot text using LF newlines."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(normalise_text(content), encoding=DEFAULT_ENCODING, newline="\n")


def assert_snapshot(directory: Path, name: str, actual: str) -> None:
    """Compare ``actual`` with a stored snapshot.

    This function only reads and compares. Call ``write_snapshot()`` to
    update a snapshot explicitly.
    """
    path = snapshot_path(directory, name)
    _require_snapshot(path)
    assert_text_equal(actual, read_snapshot(path))


def _require_snapshot(path: Path) -> None:
    """Fail when the expected snapshot file is absent."""
    if not path.is_file():
        raise AssertionError(f"Missing snapshot: {path.as_posix()}")
