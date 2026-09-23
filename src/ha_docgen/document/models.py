"""Immutable documentation data models.

Pure document structure only — no Markdown, HTML, JSON, rendering,
builders, exporters or Home Assistant domain coupling.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DocumentItem:
    """Polymorphic base for block-level content within a section.

    Concrete item kinds inherit from this type. Format-specific
    rendering belongs in later modules.
    """


@dataclass(frozen=True, slots=True)
class Paragraph(DocumentItem):
    """Immutable plain-text paragraph."""

    text: str


@dataclass(frozen=True, slots=True)
class Table(DocumentItem):
    """Immutable tabular content with string headers and rows."""

    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class CodeBlock(DocumentItem):
    """Immutable code block with language hint and source."""

    language: str
    code: str


@dataclass(frozen=True, slots=True)
class BulletList(DocumentItem):
    """Immutable unordered list of plain-text items."""

    items: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Section:
    """Immutable document section with a heading and ordered content."""

    heading: str
    content: tuple[DocumentItem, ...]


@dataclass(frozen=True, slots=True)
class Document:
    """Immutable output-independent document tree.

    Holds a title and ordered sections. Serialisation formats
    (Markdown, HTML, JSON) belong in later modules.
    """

    title: str
    sections: tuple[Section, ...]
