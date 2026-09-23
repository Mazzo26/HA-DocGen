"""Unit tests for document models and MarkdownBuilder."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from ha_docgen.document import (
    BulletList,
    CodeBlock,
    Document,
    DocumentItem,
    MarkdownBuilder,
    Paragraph,
    Section,
    Table,
)


def test_document_models_preserve_ordered_tuple_content() -> None:
    content = (
        Paragraph("Introduction"),
        BulletList(("first", "second")),
        Table(headers=("Name", "Value"), rows=(("alpha", "1"),)),
        CodeBlock(language="yaml", code="enabled: true"),
    )
    section = Section(heading="Details", content=content)
    document = Document(title="Example", sections=(section,))

    assert document.sections == (section,)
    assert section.content == content
    assert isinstance(document.sections, tuple)
    assert isinstance(section.content, tuple)


@pytest.mark.parametrize(
    ("model", "attribute", "replacement"),
    [
        (Paragraph("text"), "text", "changed"),
        (BulletList(("one",)), "items", ()),
        (Table(("A",), (("B",),)), "headers", ()),
        (CodeBlock("python", "pass"), "code", "raise"),
        (Section("Heading", ()), "heading", "Changed"),
        (Document("Title", ()), "title", "Changed"),
    ],
)
def test_document_models_are_immutable(
    model: object,
    attribute: str,
    replacement: object,
) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(model, attribute, replacement)


def test_document_models_have_value_equality_and_hashing() -> None:
    left = Document("Title", (Section("Body", (Paragraph("Text"),)),))
    right = Document("Title", (Section("Body", (Paragraph("Text"),)),))

    assert left == right
    assert hash(left) == hash(right)


def test_markdown_builder_formats_every_supported_item_directly() -> None:
    document = Document(
        title="Home",
        sections=(
            Section(
                heading="Details",
                content=(
                    Paragraph("Plain text"),
                    BulletList(("one", "two")),
                    Table(
                        headers=("Name", "Value"),
                        rows=(("alpha", "1"), ("beta", "2")),
                    ),
                    CodeBlock(language="yaml", code="enabled: true"),
                ),
            ),
        ),
    )

    assert MarkdownBuilder().build(document) == (
        "# Home\n\n"
        "## Details\n\n"
        "Plain text\n\n"
        "- one\n"
        "- two\n\n"
        "| Name | Value |\n"
        "|------|------|\n"
        "| alpha | 1 |\n"
        "| beta | 2 |\n\n"
        "```yaml\n"
        "enabled: true\n"
        "```\n\n"
    )


def test_markdown_builder_empty_document_and_empty_items() -> None:
    assert MarkdownBuilder().build(Document("Empty", ())) == "# Empty\n\n"

    document = Document(
        "Empty items",
        (
            Section(
                "Content",
                (Paragraph(""), BulletList(()), Table((), ()), CodeBlock("", "")),
            ),
        ),
    )
    assert MarkdownBuilder().build(document) == (
        "# Empty items\n\n## Content\n\n\n\n\n\n|  |\n||\n\n```\n\n```\n\n"
    )


def test_markdown_builder_rejects_unknown_document_item() -> None:
    document = Document(
        "Unsupported",
        (Section("Body", (DocumentItem(),)),),
    )

    with pytest.raises(TypeError, match="Unsupported DocumentItem type"):
        MarkdownBuilder().build(document)


def test_markdown_builder_is_stateless_and_deterministic() -> None:
    builder = MarkdownBuilder()
    document = Document("Repeat", (Section("Body", (Paragraph("Same"),)),))

    assert vars(builder) == {}
    assert builder.build(document) == builder.build(document)
