"""Detect top-level Home Assistant sections in a Package.

Inspects ``package.document.data`` only. Does not interpret section
contents; specialised parsers belong in later modules.
"""

from __future__ import annotations

from .models import Package, PackageStructure, Section


class PackageParser:
    """Detect which top-level sections exist in a Package."""

    def parse(self, package: Package) -> PackageStructure:
        """Return a PackageStructure with sorted top-level Sections."""
        sections = self._collect_sections(package.document.data)
        return PackageStructure(package=package, sections=sections)

    @staticmethod
    def _collect_sections(data: object) -> tuple[Section, ...]:
        """Return sorted Sections for every top-level key when *data* is a dict."""
        if not isinstance(data, dict):
            return ()
        return tuple(
            Section(name=str(key), data=data[key])
            for key in sorted(data, key=str)
        )
