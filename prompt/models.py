"""Immutable prompt models.

Pure prompt structure only. No provider instructions, export formats,
parsers or filesystem access.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..context import (
    AutomationContext,
    ContextMetadata,
    ContextSection,
    DashboardContext,
    EntityContext,
    PackageContext,
)

PromptSectionContent = (
    ContextMetadata
    | tuple[ContextSection, ...]
    | tuple[EntityContext, ...]
    | tuple[AutomationContext, ...]
    | tuple[DashboardContext, ...]
    | tuple[PackageContext, ...]
)


class PromptType(StrEnum):
    """Task label for one prompt.

    Values identify the task. They do not select a language-model provider.
    """

    GENERIC = "generic"
    PROGRAMMING = "programming"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"


class PromptSectionKind(StrEnum):
    """One part of ``AIContext`` that a prompt can hold by reference.

    Member order matches the field order on ``AIContext``.
    """

    METADATA = "metadata"
    REGISTRY = "registry"
    ENTITY = "entity"
    AUTOMATION = "automation"
    DASHBOARD = "dashboard"
    PACKAGE = "package"


@dataclass(frozen=True, slots=True)
class PromptSection:
    """One selected part of an existing ``AIContext``.

    ``content`` is the original metadata object or the original collection
    tuple. Domain objects are not copied.
    """

    kind: PromptSectionKind
    title: str
    content: PromptSectionContent

    def __post_init__(self) -> None:
        """Freeze sequence content without copying an existing tuple."""
        content = self.content
        if isinstance(content, tuple | ContextMetadata):
            return
        object.__setattr__(self, "content", tuple(content))


@dataclass(frozen=True, slots=True)
class Prompt:
    """Immutable, provider-neutral prompt.

    Holds fixed instructions, a task description and selected context
    sections. ``formatting_hints`` stays empty unless a caller supplies
    hints. Nothing in this model names a language-model provider.
    """

    prompt_type: PromptType
    system_instructions: str
    task_description: str
    sections: tuple[PromptSection, ...] = ()
    formatting_hints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Freeze section and hint sequences."""
        object.__setattr__(self, "sections", tuple(self.sections))
        object.__setattr__(self, "formatting_hints", tuple(self.formatting_hints))
