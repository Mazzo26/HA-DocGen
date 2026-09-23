"""Unit tests for prompt models."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, asdict

import pytest

from tools.ha_docgen.context import ContextMetadata, EntityContext
from tools.ha_docgen.prompt import Prompt, PromptSection, PromptSectionKind, PromptType
from tools.ha_docgen.registries.models import Entity


def _entity(entity_id: str) -> Entity:
    return Entity(registry_id=entity_id, entity_id=entity_id, unique_id=entity_id)


def _section(
    *,
    kind: PromptSectionKind = PromptSectionKind.METADATA,
    title: str = "Metadata",
    content: ContextMetadata | tuple[EntityContext, ...] | None = None,
) -> PromptSection:
    return PromptSection(
        kind=kind,
        title=title,
        content=ContextMetadata() if content is None else content,
    )


def _prompt(
    *,
    prompt_type: PromptType = PromptType.GENERIC,
    sections: tuple[PromptSection, ...] = (),
    formatting_hints: tuple[str, ...] = (),
) -> Prompt:
    return Prompt(
        prompt_type=prompt_type,
        system_instructions="Use only the supplied context.",
        task_description="Complete the task.",
        sections=sections,
        formatting_hints=formatting_hints,
    )


def test_prompt_type_members_are_provider_neutral() -> None:
    assert set(PromptType) == {
        PromptType.GENERIC,
        PromptType.PROGRAMMING,
        PromptType.REFACTORING,
        PromptType.DOCUMENTATION,
    }
    assert PromptType.GENERIC == "generic"
    assert isinstance(PromptType.PROGRAMMING, str)


def test_prompt_type_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        PromptType("openai")


def test_section_kind_follows_aicontext_field_order() -> None:
    assert tuple(PromptSectionKind) == (
        PromptSectionKind.METADATA,
        PromptSectionKind.REGISTRY,
        PromptSectionKind.ENTITY,
        PromptSectionKind.AUTOMATION,
        PromptSectionKind.DASHBOARD,
        PromptSectionKind.PACKAGE,
    )


def test_section_keeps_tuple_identity() -> None:
    entity = _entity("light.kitchen")
    original = (EntityContext(entity=entity),)
    section = _section(
        kind=PromptSectionKind.ENTITY,
        title="Entity Context",
        content=original,
    )
    assert section.content is original
    assert section.content[0].entity is entity  # type: ignore[index]


def test_section_freezes_a_sequence() -> None:
    entity = _entity("light.kitchen")
    section = PromptSection(
        kind=PromptSectionKind.ENTITY,
        title="Entity Context",
        content=[EntityContext(entity=entity)],  # type: ignore[arg-type]
    )
    assert section.content == (EntityContext(entity=entity),)
    assert isinstance(section.content, tuple)


def test_section_immutable() -> None:
    section = _section()
    with pytest.raises(FrozenInstanceError):
        section.title = "Changed"  # type: ignore[misc]


def test_section_equality() -> None:
    left = _section(content=ContextMetadata(version="1"))
    right = _section(content=ContextMetadata(version="1"))
    other = _section(content=ContextMetadata(version="2"))
    assert left == right
    assert left != other


def test_prompt_defaults_have_no_hints() -> None:
    prompt = Prompt(
        prompt_type=PromptType.GENERIC,
        system_instructions="Use only the supplied context.",
        task_description="Complete the task.",
    )
    assert prompt.sections == ()
    assert prompt.formatting_hints == ()


def test_prompt_preserves_section_order() -> None:
    first = _section(title="Entity Context", kind=PromptSectionKind.ENTITY)
    second = _section(title="Package Context", kind=PromptSectionKind.PACKAGE)
    prompt = _prompt(sections=(first, second))
    assert prompt.sections == (first, second)
    assert [section.kind for section in prompt.sections] == [
        PromptSectionKind.ENTITY,
        PromptSectionKind.PACKAGE,
    ]


def test_prompt_freezes_hint_sequence() -> None:
    prompt = Prompt(
        prompt_type=PromptType.GENERIC,
        system_instructions="Use only the supplied context.",
        task_description="Complete the task.",
        formatting_hints=["Keep section order."],  # type: ignore[arg-type]
    )
    assert prompt.formatting_hints == ("Keep section order.",)


def test_prompt_immutable() -> None:
    prompt = _prompt()
    with pytest.raises(FrozenInstanceError):
        prompt.task_description = "Changed"  # type: ignore[misc]


def test_prompt_equality_and_hash() -> None:
    left = _prompt(sections=(_section(),))
    right = _prompt(sections=(_section(),))
    other = _prompt(prompt_type=PromptType.DOCUMENTATION)
    assert left == right
    assert hash(left) == hash(right)
    assert left != other


def test_prompt_asdict_is_json_serializable() -> None:
    entity = Entity(
        registry_id="light.kitchen",
        entity_id="light.kitchen",
        unique_id="light.kitchen",
        extra={},
    )
    prompt = _prompt(
        sections=(
            _section(content=ContextMetadata(repository_name="home", version="1.0.0")),
            _section(
                kind=PromptSectionKind.ENTITY,
                title="Entity Context",
                content=(EntityContext(entity=entity),),
            ),
        )
    )
    encoded = json.dumps(asdict(prompt), default=str, sort_keys=True)
    assert "generic" in encoded
    assert "home" in encoded
    assert "light.kitchen" in encoded
    assert "Entity Context" in encoded
