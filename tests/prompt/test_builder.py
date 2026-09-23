"""Unit tests for PromptBuilder."""

from __future__ import annotations

import inspect
from pathlib import Path

from tools.ha_docgen.analysis import AnalysisModel
from tools.ha_docgen.automation import Automation
from tools.ha_docgen.context import (
    AIContext,
    AutomationContext,
    ContextGenerator,
    ContextMetadata,
    ContextSection,
    ContextSectionKind,
    DashboardContext,
    EntityContext,
    PackageContext,
)
from tools.ha_docgen.dashboard import Dashboard
from tools.ha_docgen.packages import Package
from tools.ha_docgen.prompt import PromptBuilder, PromptSectionKind, PromptType
from tools.ha_docgen.prompt import builder as builder_module
from tools.ha_docgen.registries.models import Entity
from tools.ha_docgen.yaml import YamlDocument

_PROVIDER_NAMES = ("openai", "claude", "gemini", "anthropic")
_EXPORT_FORMATS = ("markdown", "json", "plain text")


def _entity(entity_id: str) -> Entity:
    return Entity(registry_id=entity_id, entity_id=entity_id, unique_id=entity_id)


def _package(name: str) -> Package:
    path = Path(f"packages/{name}.yaml")
    return Package(name=name, path=path, document=YamlDocument(path=path, text="", data={}))


def _populated() -> AIContext:
    package = _package("alpha")
    return AIContext(
        metadata=ContextMetadata(repository_name="home", version="1.0.0"),
        sections=(
            ContextSection(
                kind=ContextSectionKind.ENTITIES,
                title="Entities",
                items=(_entity("light.kitchen"),),
            ),
        ),
        entity_contexts=(
            EntityContext(entity=_entity("light.b")),
            EntityContext(entity=_entity("light.a")),
        ),
        automation_contexts=(
            AutomationContext(
                automation=Automation(package=package, id="evening"),
                package=package,
            ),
        ),
        dashboard_contexts=(DashboardContext(dashboard=Dashboard(id="main", title="Main")),),
        package_contexts=(PackageContext(package=package),),
    )


def _kinds(prompt_type: PromptType, context: AIContext) -> list[PromptSectionKind]:
    prompt = PromptBuilder().build(context, prompt_type)
    return [section.kind for section in prompt.sections]


def test_empty_generic_prompt_keeps_metadata_only() -> None:
    context = AIContext(metadata=ContextMetadata())
    prompt = PromptBuilder().build(context, PromptType.GENERIC)
    assert prompt.prompt_type is PromptType.GENERIC
    assert prompt.formatting_hints == ()
    assert [section.kind for section in prompt.sections] == [PromptSectionKind.METADATA]
    assert prompt.sections[0].content is context.metadata


def test_empty_focused_prompts_have_no_sections() -> None:
    context = AIContext(metadata=ContextMetadata())
    builder = PromptBuilder()
    assert builder.build(context, PromptType.PROGRAMMING).sections == ()
    assert builder.build(context, PromptType.REFACTORING).sections == ()
    assert builder.build(context, PromptType.DOCUMENTATION).sections == ()


def test_populated_prompt_types_select_fixed_sections() -> None:
    context = _populated()
    assert _kinds(PromptType.GENERIC, context) == [
        PromptSectionKind.METADATA,
        PromptSectionKind.REGISTRY,
        PromptSectionKind.ENTITY,
        PromptSectionKind.AUTOMATION,
        PromptSectionKind.DASHBOARD,
        PromptSectionKind.PACKAGE,
    ]
    assert _kinds(PromptType.PROGRAMMING, context) == [
        PromptSectionKind.ENTITY,
        PromptSectionKind.AUTOMATION,
        PromptSectionKind.PACKAGE,
    ]
    assert _kinds(PromptType.REFACTORING, context) == [
        PromptSectionKind.ENTITY,
        PromptSectionKind.AUTOMATION,
        PromptSectionKind.DASHBOARD,
        PromptSectionKind.PACKAGE,
    ]
    assert _kinds(PromptType.DOCUMENTATION, context) == [
        PromptSectionKind.DASHBOARD,
        PromptSectionKind.PACKAGE,
    ]


def test_programming_prompt_reuses_context_objects() -> None:
    context = _populated()
    prompt = PromptBuilder().build(context, PromptType.PROGRAMMING)
    by_kind = {section.kind: section for section in prompt.sections}
    assert by_kind[PromptSectionKind.ENTITY].content is context.entity_contexts
    assert by_kind[PromptSectionKind.AUTOMATION].content is context.automation_contexts
    assert by_kind[PromptSectionKind.PACKAGE].content is context.package_contexts
    assert [item.entity.entity_id for item in context.entity_contexts] == [
        "light.a",
        "light.b",
    ]


def test_titles_match_section_kinds() -> None:
    prompt = PromptBuilder().build(_populated(), PromptType.GENERIC)
    assert [(section.kind, section.title) for section in prompt.sections] == [
        (PromptSectionKind.METADATA, "Metadata"),
        (PromptSectionKind.REGISTRY, "Registry"),
        (PromptSectionKind.ENTITY, "Entity Context"),
        (PromptSectionKind.AUTOMATION, "Automation Context"),
        (PromptSectionKind.DASHBOARD, "Dashboard Context"),
        (PromptSectionKind.PACKAGE, "Package Context"),
    ]


def test_task_text_is_deterministic_and_provider_neutral() -> None:
    context = _populated()
    builder = PromptBuilder()
    expected = {
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
    for prompt_type, task in expected.items():
        prompt = builder.build(context, prompt_type)
        text = f"{prompt.system_instructions}\n{prompt.task_description}".lower()
        assert prompt.task_description == task
        assert prompt.system_instructions.startswith("Use only the context supplied")
        assert prompt.formatting_hints == ()
        assert all(name not in text for name in _PROVIDER_NAMES)
        assert all(name not in text for name in _EXPORT_FORMATS)


def test_builder_is_stateless_and_repeatable() -> None:
    context = _populated()
    builder = PromptBuilder()
    first = builder.build(context, PromptType.PROGRAMMING)
    other = builder.build(context, PromptType.DOCUMENTATION)
    second = builder.build(context, PromptType.PROGRAMMING)
    assert first == second
    assert first is not second
    assert first.prompt_type is PromptType.PROGRAMMING
    assert other.prompt_type is PromptType.DOCUMENTATION


def test_build_leaves_aicontext_unchanged() -> None:
    context = _populated()
    entity_ids = tuple(item.entity.entity_id for item in context.entity_contexts)
    automation_ids = tuple(item.automation.id for item in context.automation_contexts)
    dashboard_ids = tuple(item.dashboard.id for item in context.dashboard_contexts)
    package_names = tuple(item.package.name for item in context.package_contexts)
    identities = (
        context.metadata,
        context.sections,
        context.entity_contexts,
        context.automation_contexts,
        context.dashboard_contexts,
        context.package_contexts,
    )
    PromptBuilder().build(context, PromptType.GENERIC)
    assert context.metadata is identities[0]
    assert context.sections is identities[1]
    assert context.entity_contexts is identities[2]
    assert context.automation_contexts is identities[3]
    assert context.dashboard_contexts is identities[4]
    assert context.package_contexts is identities[5]
    assert tuple(item.entity.entity_id for item in context.entity_contexts) == entity_ids
    assert tuple(item.automation.id for item in context.automation_contexts) == automation_ids
    assert tuple(item.dashboard.id for item in context.dashboard_contexts) == dashboard_ids
    assert tuple(item.package.name for item in context.package_contexts) == package_names


def test_context_generator_contract_is_unchanged() -> None:
    parameters = list(inspect.signature(ContextGenerator.generate).parameters)
    assert parameters == ["self", "analysis_model"]
    assert set(AIContext.__dataclass_fields__) == {
        "metadata",
        "sections",
        "entity_contexts",
        "automation_contexts",
        "dashboard_contexts",
        "package_contexts",
        "esphome_contexts",
    }


def test_building_a_prompt_leaves_generated_context_equal() -> None:
    generated = ContextGenerator().generate(AnalysisModel())
    again = ContextGenerator().generate(AnalysisModel())
    PromptBuilder().build(generated, PromptType.GENERIC)
    assert generated == again
    assert ContextGenerator().generate(AnalysisModel()) == generated


def test_builder_does_not_consume_analysis_or_repositories() -> None:
    names = dir(builder_module)
    assert "AnalysisModel" not in names
    assert "YamlRepository" not in names
    assert "RelationshipRepository" not in names
    parameters = list(inspect.signature(PromptBuilder.build).parameters)
    assert parameters == ["self", "context", "prompt_type"]
