"""Build a Document for exactly one Home Assistant package.

Transforms package domain objects into an immutable ``Document`` tree.
Produces document models only — no Markdown, filesystem, repository
or Home Assistant aggregate coupling.
"""

from __future__ import annotations

from ..automation.models import Automation
from ..helper.models import Helper
from ..packages.models import Package, PackageStructure
from ..scene.models import Scene
from ..script.models import Script
from ..template.models import Template
from .models import BulletList, Document, Paragraph, Section


class PackageDocumentGenerator:
    """Generate a Document for one Package.

    Fully stateless: no instance state, no caching, no filesystem and
    no side effects. Callers supply already-parsed domain objects.
    """

    def generate(
        self,
        package: Package,
        structure: PackageStructure,
        automations: tuple[Automation, ...],
        scripts: tuple[Script, ...],
        scenes: tuple[Scene, ...],
        helpers: tuple[Helper, ...],
        templates: tuple[Template, ...],
    ) -> Document:
        """Return a Document describing *package* and its filtered objects."""
        return Document(
            title=f"Package: {package.name}",
            sections=(
                _overview_section(package),
                _sections_section(structure),
                _helpers_section(package, helpers),
                _automations_section(package, automations),
                _scripts_section(package, scripts),
                _scenes_section(package, scenes),
                _templates_section(package, templates),
            ),
        )


def _overview_section(package: Package) -> Section:
    """Build the Overview section with package name and path."""
    text = f"Name: {package.name}\nPath: {package.path}"
    return Section(heading="Overview", content=(Paragraph(text),))


def _sections_section(structure: PackageStructure) -> Section:
    """Build the Sections section from PackageStructure section names."""
    items = tuple(section.name for section in structure.sections)
    return Section(heading="Sections", content=(BulletList(items),))


def _helpers_section(
    package: Package,
    helpers: tuple[Helper, ...],
) -> Section:
    """Build the Helpers section listing helper ids for *package*."""
    items = tuple(
        helper.id for helper in helpers if helper.package == package
    )
    return Section(heading="Helpers", content=(BulletList(items),))


def _automations_section(
    package: Package,
    automations: tuple[Automation, ...],
) -> Section:
    """Build the Automations section for objects belonging to *package*."""
    items: list[str] = []
    for automation in automations:
        if automation.package != package:
            continue
        label = _automation_label(automation)
        if label is not None:
            items.append(label)
    return Section(heading="Automations", content=(BulletList(tuple(items)),))


def _scripts_section(
    package: Package,
    scripts: tuple[Script, ...],
) -> Section:
    """Build the Scripts section for objects belonging to *package*."""
    items: list[str] = []
    for script in scripts:
        if script.package != package:
            continue
        label = _script_label(script)
        if label is not None:
            items.append(label)
    return Section(heading="Scripts", content=(BulletList(tuple(items)),))


def _scenes_section(
    package: Package,
    scenes: tuple[Scene, ...],
) -> Section:
    """Build the Scenes section listing scene names for *package*."""
    items = tuple(
        scene.name
        for scene in scenes
        if scene.package == package and scene.name is not None
    )
    return Section(heading="Scenes", content=(BulletList(items),))


def _templates_section(
    package: Package,
    templates: tuple[Template, ...],
) -> Section:
    """Build the Templates section listing template kinds for *package*."""
    items = tuple(
        template.kind
        for template in templates
        if template.package == package
    )
    return Section(heading="Templates", content=(BulletList(items),))


def _automation_label(automation: Automation) -> str | None:
    """Return alias when set, otherwise id; None when both are absent."""
    if automation.alias is not None:
        return automation.alias
    return automation.id


def _script_label(script: Script) -> str | None:
    """Return alias when set, otherwise id; None when both are absent."""
    if script.alias is not None:
        return script.alias
    return script.id
