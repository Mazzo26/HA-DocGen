"""Generic, deterministic comparison helpers for tests."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

from tools.ha_docgen.constants import DEFAULT_ENCODING


def normalise_text(value: str) -> str:
    """Convert CRLF and CR to LF and remove trailing whitespace from each line.

    Leading blank lines, trailing blank lines and a missing final newline are
    preserved.
    """
    unix = value.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in unix.split("\n"))


def ordered[T](
    items: Iterable[T],
    key: Callable[[T], object] | None = None,
) -> tuple[T, ...]:
    """Return items sorted by ``key``, or by ``str`` when no key is given."""
    if key is None:
        return tuple(sorted(items, key=str))
    return tuple(sorted(items, key=key))


def read_text(path: Path) -> str:
    """Read a UTF-8 text file."""
    return path.read_text(encoding=DEFAULT_ENCODING)


def files_equal(left: Path, right: Path) -> bool:
    """Return True when two files match after text normalisation."""
    return normalise_text(read_text(left)) == normalise_text(read_text(right))


def relative_files(root: Path) -> tuple[str, ...]:
    """Return sorted POSIX paths of files under ``root``."""
    files = [path.relative_to(root).as_posix() for path in _files(root)]
    return tuple(sorted(files))


def directories_equal(left: Path, right: Path) -> bool:
    """Return True when both trees contain the same normalised files."""
    left_files = relative_files(left)
    if left_files != relative_files(right):
        return False
    return _same_files(left, right, left_files)


def _files(root: Path) -> tuple[Path, ...]:
    """Return files under ``root``."""
    if not root.is_dir():
        raise ValueError(f"Directory required: {root}")
    return tuple(path for path in root.rglob("*") if path.is_file())


def _same_files(left: Path, right: Path, names: Sequence[str]) -> bool:
    """Return True when every named file matches after normalisation."""
    return all(files_equal(left / name, right / name) for name in names)
