"""Generic YAML loading and domain aggregate for HA-DocGen.

``YamlLoader`` is the only component that reads YAML files.
``YamlDocument`` holds the result. ``resolve_includes`` maps include
directives in that document onto ``ProjectTree`` files. Domain
interpretation belongs in later modules. ``YamlRepository`` aggregates
already-parsed YAML domain objects for read-only lookup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .include import IncludeDirective, IncludeNode, IncludeReference, resolve_includes
from .loader import YamlLoader, YamlLoadError
from .models import YamlDocument

if TYPE_CHECKING:
    from .repository import YamlRepository

__all__ = [
    "IncludeDirective",
    "IncludeNode",
    "IncludeReference",
    "YamlDocument",
    "YamlLoadError",
    "YamlLoader",
    "YamlRepository",
    "resolve_includes",
]


def __getattr__(name: str) -> object:
    """Lazy-load YamlRepository to avoid import cycles with domain parsers."""
    if name == "YamlRepository":
        from .repository import YamlRepository as _YamlRepository

        return _YamlRepository
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
