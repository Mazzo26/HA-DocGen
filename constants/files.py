"""Generic filesystem file constants.

Extensions, derived glob patterns and default text encoding.
"""

from __future__ import annotations

from typing import Final

from .yaml import EXTENSION_YAML, EXTENSION_YML

DEFAULT_ENCODING: Final[str] = "utf-8"

EXTENSION_JSON: Final[str] = ".json"
EXTENSION_PYTHON: Final[str] = ".py"
EXTENSION_MARKDOWN: Final[str] = ".md"
EXTENSION_TEXT: Final[str] = ".txt"

GLOB_JSON: Final[str] = f"*{EXTENSION_JSON}"
GLOB_PYTHON: Final[str] = f"*{EXTENSION_PYTHON}"
GLOB_MARKDOWN: Final[str] = f"*{EXTENSION_MARKDOWN}"
GLOB_TEXT: Final[str] = f"*{EXTENSION_TEXT}"

TEXT_FILE_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {
        EXTENSION_YAML,
        EXTENSION_YML,
        EXTENSION_JSON,
        EXTENSION_PYTHON,
        EXTENSION_MARKDOWN,
        EXTENSION_TEXT,
    }
)
