"""Relative path checks for test filesystem helpers."""

from __future__ import annotations

from pathlib import Path


def require_relative_path(value: str) -> Path:
    """Return a relative path, rejecting absolute paths and parent segments."""
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Relative path required: {value}")
    return path
