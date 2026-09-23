"""Generic filesystem folder constants.

Directory names used across the repository walk.
Contains no ignore-rule evaluation logic.
"""

from __future__ import annotations

from typing import Final

DIR_GIT: Final[str] = ".git"
DIR_VENV: Final[str] = ".venv"
DIR_PYCACHE: Final[str] = "__pycache__"
DIR_PYTEST_CACHE: Final[str] = ".pytest_cache"
DIR_RUFF_CACHE: Final[str] = ".ruff_cache"
DIR_NODE_MODULES: Final[str] = "node_modules"

IGNORE_DIRS: Final[frozenset[str]] = frozenset(
    {
        DIR_GIT,
        DIR_VENV,
        DIR_PYCACHE,
        DIR_PYTEST_CACHE,
        DIR_RUFF_CACHE,
        DIR_NODE_MODULES,
    }
)
