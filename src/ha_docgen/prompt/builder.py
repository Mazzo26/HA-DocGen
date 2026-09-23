"""Build an immutable prompt from an existing AIContext.

Organises context that is already present. Performs no parsing,
relationship discovery, validation, filesystem access or provider-specific
formatting, and does not modify the context.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..context import AIContext
from .models import (
    Prompt,
    PromptSection,
    PromptSectionContent,
    PromptSectionKind,
    PromptType,
)

_SYSTEM_INSTRUCTIONS = (
    "Use only the context supplied in this prompt. "
    "Do not invent facts, relationships or objects that are not present."
)

_TASK_DESCRIPTIONS: Mapping[PromptType, str] = {
    PromptType.GENERIC: "Complete the requested task using the complete AI context.",
    PromptType.PROGRAMMING: (
        "Implement or modify Home Assistant configuration using the supplied "
        "entity, automation and package context."
    ),
    PromptType.REFACTORING: (
        "Improve the existing Home Assistant configuration using the supplied "
        "entity, automation, dashboard and package context."
    ),
    PromptType.DOCUMENTATION: "Document the supplied package and dashboard context.",
}

_TITLES: Mapping[PromptSectionKind, str] = {
    PromptSectionKind.METADATA: "Metadata",
    PromptSectionKind.REGISTRY: "Registry",
    PromptSectionKind.ENTITY: "Entity Context",
    PromptSectionKind.AUTOMATION: "Automation Context",
    PromptSectionKind.DASHBOARD: "Dashboard Context",
    PromptSectionKind.PACKAGE: "Package Context",
}

_SELECTION: Mapping[PromptType, tuple[PromptSectionKind, ...]] = {
    PromptType.GENERIC: (
        PromptSectionKind.METADATA,
        PromptSectionKind.REGISTRY,
        PromptSectionKind.ENTITY,
        PromptSectionKind.AUTOMATION,
        PromptSectionKind.DASHBOARD,
        PromptSectionKind.PACKAGE,
    ),
    PromptType.PROGRAMMING: (
        PromptSectionKind.ENTITY,
        PromptSectionKind.AUTOMATION,
        PromptSectionKind.PACKAGE,
    ),
    PromptType.REFACTORING: (
        PromptSectionKind.ENTITY,
        PromptSectionKind.AUTOMATION,
        PromptSectionKind.DASHBOARD,
        PromptSectionKind.PACKAGE,
    ),
    PromptType.DOCUMENTATION: (
        PromptSectionKind.DASHBOARD,
        PromptSectionKind.PACKAGE,
    ),
}


class PromptBuilder:
    """Organise an ``AIContext`` into an immutable ``Prompt``.

    Fully stateless: no instance state, no caching and no side effects.
    The same context and prompt type always yield an equal prompt.
    """

    def build(self, context: AIContext, prompt_type: PromptType) -> Prompt:
        """Return a prompt that references the selected context parts."""
        return Prompt(
            prompt_type=prompt_type,
            system_instructions=_SYSTEM_INSTRUCTIONS,
            task_description=_TASK_DESCRIPTIONS[prompt_type],
            sections=_sections(context, prompt_type),
        )


def _sections(
    context: AIContext,
    prompt_type: PromptType,
) -> tuple[PromptSection, ...]:
    """Return selected sections in field order, skipping empty collections."""
    selected: list[PromptSection] = []
    for kind in _SELECTION[prompt_type]:
        section = _section(context, kind)
        if section is not None:
            selected.append(section)
    return tuple(selected)


def _section(context: AIContext, kind: PromptSectionKind) -> PromptSection | None:
    """Return one section, or None when the collection is empty."""
    content = _content(context, kind)
    if content == ():
        return None
    return PromptSection(kind=kind, title=_TITLES[kind], content=content)


def _content(context: AIContext, kind: PromptSectionKind) -> PromptSectionContent:
    """Return the original AIContext field for one section kind."""
    contents: Mapping[PromptSectionKind, PromptSectionContent] = {
        PromptSectionKind.METADATA: context.metadata,
        PromptSectionKind.REGISTRY: context.sections,
        PromptSectionKind.ENTITY: context.entity_contexts,
        PromptSectionKind.AUTOMATION: context.automation_contexts,
        PromptSectionKind.DASHBOARD: context.dashboard_contexts,
        PromptSectionKind.PACKAGE: context.package_contexts,
    }
    return contents[kind]
