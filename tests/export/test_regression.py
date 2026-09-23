"""Regression tests for modules that Module 13.6 must not change."""

from __future__ import annotations

import inspect
from dataclasses import fields
from pathlib import Path

from tools.ha_docgen.analysis import AnalysisModel
from tools.ha_docgen.context import AIContext, ContextGenerator
from tools.ha_docgen.export import ExportFormat, PromptExporter
from tools.ha_docgen.prompt import Prompt, PromptBuilder, PromptType
from tools.ha_docgen.prompt import builder as builder_module
from tools.ha_docgen.tests.export.factory import populated_context, populated_prompt

_FORBIDDEN = (
    "AnalysisModel",
    "AIContext",
    "ContextGenerator",
    "YamlRepository",
    "RelationshipRepository",
    "write_text",
    "mkdir",
)


def test_prompt_fields_are_unchanged() -> None:
    assert [field.name for field in fields(Prompt)] == [
        "prompt_type",
        "system_instructions",
        "task_description",
        "sections",
        "formatting_hints",
    ]
    assert not hasattr(Prompt, "export")
    assert not hasattr(Prompt, "render")


def test_prompt_builder_signature_is_unchanged() -> None:
    assert list(inspect.signature(PromptBuilder.build).parameters) == [
        "self",
        "context",
        "prompt_type",
    ]
    assert "AnalysisModel" not in dir(builder_module)
    assert "YamlRepository" not in dir(builder_module)
    assert "RelationshipRepository" not in dir(builder_module)
    source = inspect.getsource(builder_module)
    assert "ha_docgen.export" not in source


def test_aicontext_and_generator_are_unchanged() -> None:
    assert [field.name for field in fields(AIContext)] == [
        "metadata",
        "sections",
        "entity_contexts",
        "automation_contexts",
        "dashboard_contexts",
        "package_contexts",
        "esphome_contexts",
    ]
    assert list(inspect.signature(ContextGenerator.generate).parameters) == [
        "self",
        "analysis_model",
    ]
    generated = ContextGenerator().generate(AnalysisModel())
    assert PromptBuilder().build(generated, PromptType.GENERIC) == PromptBuilder().build(
        ContextGenerator().generate(AnalysisModel()),
        PromptType.GENERIC,
    )


def test_export_does_not_change_prompt_or_context() -> None:
    context = populated_context()
    prompt = PromptBuilder().build(context, PromptType.PROGRAMMING)
    sections = prompt.sections
    metadata = context.metadata
    entities = context.entity_contexts
    before = prompt
    for export_format in ExportFormat:
        PromptExporter().export(prompt, export_format)
    assert prompt == before
    assert prompt.sections is sections
    assert context.metadata is metadata
    assert context.entity_contexts is entities
    assert [item.entity.entity_id for item in context.entity_contexts] == ["light.a", "light.b"]


def test_exporters_do_not_consume_lower_layers_or_the_filesystem() -> None:
    root = Path(__file__).parents[2] / "export"
    for path in sorted(root.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        for name in _FORBIDDEN:
            assert name not in source
    assert list(inspect.signature(PromptExporter.export).parameters) == [
        "self",
        "prompt",
        "export_format",
    ]


def test_public_export_api_is_limited_to_exporters() -> None:
    import tools.ha_docgen.export as export

    assert export.__all__ == [
        "ExportFormat",
        "JsonExporter",
        "MarkdownExporter",
        "PlainTextExporter",
        "PromptExporter",
    ]
    assert not hasattr(export, "prompt_data")
    assert not hasattr(export, "render_data")
    assert not hasattr(export, "to_data")


def test_populated_prompt_builder_output_still_exports() -> None:
    prompt = populated_prompt()
    assert [section.kind.value for section in prompt.sections] == [
        "entity",
        "automation",
        "package",
    ]
    rendered = PromptExporter().export(prompt, ExportFormat.JSON)
    assert '"prompt_type": "programming"' in rendered
