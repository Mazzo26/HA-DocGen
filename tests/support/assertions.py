"""Reusable assertions built on the generic comparison helpers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from .compare import directories_equal, files_equal, normalise_text, ordered


def assert_text_equal(actual: str, expected: str) -> None:
    """Fail when two strings differ after normalisation."""
    if normalise_text(actual) != normalise_text(expected):
        raise AssertionError("Normalised text differs")


def assert_files_equal(left: Path, right: Path) -> None:
    """Fail when two UTF-8 files differ after normalisation."""
    if not files_equal(left, right):
        raise AssertionError(f"Files differ: {left.as_posix()} and {right.as_posix()}")


def assert_directories_equal(left: Path, right: Path) -> None:
    """Fail when two directory trees differ after normalisation."""
    if not directories_equal(left, right):
        raise AssertionError(f"Directories differ: {left.as_posix()} and {right.as_posix()}")


def assert_ordered[T](
    items: Sequence[T],
    key: Callable[[T], object] | None = None,
) -> None:
    """Fail when ``items`` is not already in deterministic order."""
    actual = tuple(items)
    if actual != ordered(actual, key):
        raise AssertionError("Sequence is not in deterministic order")
