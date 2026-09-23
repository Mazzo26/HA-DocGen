"""Package YAML discovery, models and structural parsing for HA-DocGen.

``PackageScanner`` discovers and loads package files as ``YamlDocument``
instances. ``Package`` is the immutable public representation of one
package. ``PackageParser`` detects top-level sections as ``Section``
objects without interpreting their contents.
"""

from __future__ import annotations

from .models import Package, PackageStructure, Section
from .parser import PackageParser
from .scanner import PackageScanner

__all__ = [
    "Package",
    "PackageParser",
    "PackageScanner",
    "PackageStructure",
    "Section",
]
