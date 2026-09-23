"""Stateless Markdown rendering for an immutable Prompt.

Knows only ``Prompt``. No repositories, analysis, filesystem access or
provider-specific formatting.
"""

from __future__ import annotations

from ..prompt import Prompt, PromptSection
from ._payload import to_data
from ._text import prompt_title, render_data


class MarkdownExporter:
    """Render a ``Prompt`` as deterministic Markdown."""

    def export(self, prompt: Prompt) -> str:
        """Return Markdown for ``prompt`` without changing it."""
        chunks = _header(prompt)
        chunks.extend(_hints(prompt.formatting_hints))
        for section in prompt.sections:
            chunks.extend(_section(section))
        return "\n".join(chunks).rstrip("\n") + "\n"


def _header(prompt: Prompt) -> list[str]:
    """Return title, type, instructions and task."""
    return [
        f"# {prompt_title(prompt)}",
        "",
        f"Prompt type: {prompt.prompt_type.value}",
        "",
        "## System instructions",
        "",
        prompt.system_instructions,
        "",
        "## Task description",
        "",
        prompt.task_description,
        "",
    ]


def _hints(hints: tuple[str, ...]) -> list[str]:
    """Return formatting hints when the prompt stores any."""
    if not hints:
        return []
    return ["## Formatting hints", "", *hints, ""]


def _section(section: PromptSection) -> list[str]:
    """Return one section heading, kind and rendered content."""
    return [
        f"## {section.title}",
        "",
        f"Kind: {section.kind.value}",
        "",
        render_data(to_data(section.content)),
        "",
    ]
