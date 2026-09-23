"""Template models and YAML collection for HA-DocGen.

``Template`` is the immutable representation of one found template
string. ``TemplateParser`` collects templates from a ``PackageStructure``
(with ``package`` provenance) without Jinja interpretation or
relationship analysis.
"""

from __future__ import annotations

from .models import Template
from .parser import TemplateParser

__all__ = [
    "Template",
    "TemplateParser",
]
