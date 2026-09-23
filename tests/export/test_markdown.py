"""Unit tests for MarkdownExporter."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from tools.ha_docgen.context import AIContext, ContextMetadata, EntityContext
from tools.ha_docgen.export import MarkdownExporter
from tools.ha_docgen.prompt import PromptBuilder, PromptType
from tools.ha_docgen.registries.models import Entity
from tools.ha_docgen.relationships import ObjectType, Relationship, RelationshipType
from tools.ha_docgen.tests.export.factory import empty_prompt, ordered_entity_prompt, populated_prompt

_EMPTY = """\
# Generic Prompt

Prompt type: generic

## System instructions

Use only the supplied context.

## Task description

Complete the task.
"""

_PROVIDERS = ("openai", "claude", "gemini", "anthropic")


def test_empty_prompt_markdown_is_exact() -> None:
    assert MarkdownExporter().export(empty_prompt()) == _EMPTY


def test_populated_prompt_markdown_keeps_section_order() -> None:
    rendered = MarkdownExporter().export(populated_prompt())
    entity = rendered.index("## Entity Context")
    automation = rendered.index("## Automation Context")
    package = rendered.index("## Package Context")
    assert entity < automation < package
    assert rendered.index("light.a") < rendered.index("light.b")
    assert "Kind: entity" in rendered
    assert "evening" in rendered
    assert "packages/alpha.yaml" in rendered
    assert "packages\\alpha.yaml" not in rendered
    assert rendered.startswith("# Programming Prompt\n\nPrompt type: programming\n")
    assert all(name not in rendered.lower() for name in _PROVIDERS)


def test_markdown_preserves_sequence_order_and_sorts_mapping_keys() -> None:
    rendered = MarkdownExporter().export(ordered_entity_prompt())
    assert rendered.index("light.b") < rendered.index("light.a")
    assert rendered.index("## Formatting hints") < rendered.index("## Entity Context")
    assert rendered.index("keep facts") < rendered.index("keep order")
    extra = rendered.index("extra:")
    assert rendered.index("m:", extra) < rendered.index("z:", extra)


def test_markdown_formatting_is_stable_across_prompts() -> None:
    empty = MarkdownExporter().export(empty_prompt())
    populated = MarkdownExporter().export(populated_prompt())
    assert empty.startswith("# ")
    assert "\n## System instructions\n" in empty
    assert "\n## Task description\n" in empty
    assert "\n## System instructions\n" in populated
    assert "\n## Task description\n" in populated
    assert "## Formatting hints" not in empty


def test_markdown_renders_metadata_enums_and_multiline_values() -> None:
    relationship = Relationship(
        source_type=ObjectType.ENTITY,
        source_id="light.kitchen",
        target_type=ObjectType.DEVICE,
        target_id="device-1",
        relationship_type=RelationshipType.REFERENCES,
    )
    entity = Entity(
        registry_id="light.kitchen",
        entity_id="light.kitchen",
        unique_id="kitchen",
        name="Kitchen\nLamp",
        labels=("porch", "kitchen"),
        has_entity_name=True,
    )
    context = AIContext(
        metadata=ContextMetadata(
            repository_name="home",
            project_path=Path("config"),
            generated_at=datetime(2026, 9, 22, 8, 0, 0),
        ),
        entity_contexts=(EntityContext(entity=entity, relationships=(relationship,)),),
    )
    rendered = MarkdownExporter().export(PromptBuilder().build(context, PromptType.GENERIC))
    assert rendered.index("## Metadata") < rendered.index("## Entity Context")
    assert "repository_name: home" in rendered
    assert "project_path: config" in rendered
    assert "generated_at: 2026-09-22T08:00:00" in rendered
    assert "relationship_type: references" in rendered
    assert "has_entity_name: true" in rendered
    assert "name:\n      Kitchen\n      Lamp" in rendered
    labels = rendered.index("labels:")
    assert rendered.index("[0]: porch", labels) < rendered.index("[1]: kitchen", labels)
    assert "extra: {}" in rendered
    assert "aliases: []" in rendered


def test_repeated_markdown_exports_are_identical() -> None:
    exporter = MarkdownExporter()
    prompt = populated_prompt()
    first = exporter.export(prompt)
    second = exporter.export(prompt)
    assert first == second
    assert exporter.export(empty_prompt()) == _EMPTY
    assert exporter.export(prompt) == first
