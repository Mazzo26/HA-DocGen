"""YAML format constants.

Generic filesystem values for the YAML file format.
Contains no parsing logic.
"""

from __future__ import annotations

from typing import Final

EXTENSION_YAML: Final[str] = ".yaml"
EXTENSION_YML: Final[str] = ".yml"

YAML_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {
        EXTENSION_YAML,
        EXTENSION_YML,
    }
)

GLOB_YAML: Final[str] = f"*{EXTENSION_YAML}"
GLOB_YML: Final[str] = f"*{EXTENSION_YML}"
