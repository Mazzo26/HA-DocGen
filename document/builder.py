"""Stateless Markdown rendering from document models.

Converts an immutable ``Document`` tree into a Markdown string.
Knows only document models — no YAML, registries, relationships,
graph, filesystem or Home Assistant domain knowledge.
"""

from __future__ import annotations

from .models import (
    BulletList,
    CodeBlock,
    Document,
    DocumentItem,
    Paragraph,
    Section,
    Table,
)


class MarkdownBuilder:
    """Render a Document to a Markdown string.

    Fully stateless: no instance state, no caching, no configuration
    and no side effects.
    """

    def build(self, document: Document) -> str:
        """Return deterministic Markdown for ``document``."""
        chunks: list[str] = [f"# {document.title}\n\n"]
        for section in document.sections:
            chunks.append(_build_section(section))
        return "".join(chunks)


def _build_section(section: Section) -> str:
    """Render one Section including heading and content items."""
    chunks: list[str] = [f"## {section.heading}\n\n"]
    for item in section.content:
        chunks.append(_build_item(item))
    return "".join(chunks)


def _build_item(item: DocumentItem) -> str:
    """Dispatch one DocumentItem to the matching private renderer."""
    if isinstance(item, Paragraph):
        return _build_paragraph(item)
    if isinstance(item, Table):
        return _build_table(item)
    if isinstance(item, CodeBlock):
        return _build_codeblock(item)
    if isinstance(item, BulletList):
        return _build_bullet_list(item)
    raise TypeError(f"Unsupported DocumentItem type: {type(item).__name__}")


def _build_paragraph(paragraph: Paragraph) -> str:
    """Render a Paragraph as plain text with a trailing blank line."""
    return f"{paragraph.text}\n\n"


def _build_bullet_list(bullet_list: BulletList) -> str:
    """Render a BulletList as Markdown list items."""
    lines = [f"- {entry}" for entry in bullet_list.items]
    return "\n".join(lines) + "\n\n"


def _build_codeblock(code_block: CodeBlock) -> str:
    """Render a CodeBlock as a fenced Markdown code block."""
    return f"```{code_block.language}\n{code_block.code}\n```\n\n"


def _build_table(table: Table) -> str:
    """Render a Table as a GitHub-flavoured Markdown table."""
    header = "| " + " | ".join(table.headers) + " |"
    separator = "|" + "|".join("------" for _ in table.headers) + "|"
    rows = ["| " + " | ".join(row) + " |" for row in table.rows]
    return "\n".join([header, separator, *rows]) + "\n\n"
