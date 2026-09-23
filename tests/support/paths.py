"""Repository path helpers for tests.

These resolve locations relative to the standalone repository layout
(``src/ha_docgen``, ``tests/`` at the repository root).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_SOURCE_ROOT = REPOSITORY_ROOT / "src" / "ha_docgen"
_SRC_PATH = REPOSITORY_ROOT / "src"


def require_relative_path(value: str) -> Path:
    """Return a relative path, rejecting absolute paths and parent segments."""
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Relative path required: {value}")
    return path


def module_subprocess_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return an environment that can resolve ``ha_docgen`` without packaging.

    Pytest injects ``src`` via ``pytest.ini``; child processes do not inherit
    that setting, so subprocess module entrypoints need ``PYTHONPATH``.
    """
    env = dict(os.environ if base is None else base)
    src = str(_SRC_PATH)
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src if not existing else f"{src}{os.pathsep}{existing}"
    return env
