"""Unit tests for PlainTextExporter."""

from __future__ import annotations

from tools.ha_docgen.export import PlainTextExporter
from tools.ha_docgen.tests.export.factory import empty_prompt, ordered_entity_prompt, populated_prompt

_EMPTY = """\
Title: Generic Prompt
Prompt type: generic

System instructions:
Use only the supplied context.

Task description:
Complete the task.
"""


def test_empty_prompt_plain_text_is_exact() -> None:
    assert PlainTextExporter().export(empty_prompt()) == _EMPTY


def test_populated_prompt_plain_text_keeps_section_order() -> None:
    rendered = PlainTextExporter().export(populated_prompt())
    entity = rendered.index("Entity Context:")
    automation = rendered.index("Automation Context:")
    package = rendered.index("Package Context:")
    assert entity < automation < package
    assert rendered.index("light.a") < rendered.index("light.b")
    assert "Kind: automation" in rendered
    assert rendered.startswith("Title: Programming Prompt\nPrompt type: programming\n")
    assert "packages/alpha.yaml" in rendered


def test_plain_text_has_no_markdown_syntax() -> None:
    rendered = PlainTextExporter().export(populated_prompt())
    assert "```" not in rendered
    for line in rendered.splitlines():
        assert not line.startswith("#")
        assert not line.startswith("- ")
        assert not line.startswith("*")
        assert not line.startswith(">")


def test_plain_text_preserves_sequence_order() -> None:
    rendered = PlainTextExporter().export(ordered_entity_prompt())
    assert rendered.index("light.b") < rendered.index("light.a")
    assert rendered.index("Formatting hints:") < rendered.index("Entity Context:")
    assert rendered.index("keep facts") < rendered.index("keep order")
    extra = rendered.index("extra:")
    assert rendered.index("m:", extra) < rendered.index("z:", extra)


def test_repeated_plain_text_exports_are_identical() -> None:
    exporter = PlainTextExporter()
    prompt = populated_prompt()
    first = exporter.export(prompt)
    assert exporter.export(prompt) == first
    assert exporter.export(empty_prompt()) == _EMPTY
    assert exporter.export(prompt) == first
