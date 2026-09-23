"""Prompt fixtures for export tests."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

from ha_docgen.automation import Automation
from ha_docgen.context import (
    AIContext,
    AutomationContext,
    ContextMetadata,
    ContextSection,
    ContextSectionKind,
    DashboardContext,
    EntityContext,
    PackageContext,
)
from ha_docgen.dashboard import Dashboard
from ha_docgen.packages import Package
from ha_docgen.prompt import (
    Prompt,
    PromptBuilder,
    PromptSection,
    PromptSectionKind,
    PromptType,
)
from ha_docgen.registries.models import Entity
from ha_docgen.yaml import YamlDocument


def entity(entity_id: str, extra: MappingProxyType[str, object] | None = None) -> Entity:
    """Return one registry entity."""
    if extra is None:
        return Entity(registry_id=entity_id, entity_id=entity_id, unique_id=entity_id)
    return Entity(
        registry_id=entity_id,
        entity_id=entity_id,
        unique_id=entity_id,
        extra=extra,
    )


def package(name: str = "alpha") -> Package:
    """Return one package whose path uses a portable POSIX form."""
    path = Path("packages") / f"{name}.yaml"
    return Package(name=name, path=path, document=YamlDocument(path=path, text="", data={}))


def empty_prompt() -> Prompt:
    """Return a prompt with no sections."""
    return Prompt(
        prompt_type=PromptType.GENERIC,
        system_instructions="Use only the supplied context.",
        task_description="Complete the task.",
    )


def populated_context() -> AIContext:
    """Return one context that selects every prompt section kind."""
    owned = package()
    return AIContext(
        metadata=ContextMetadata(repository_name="home", version="1.0.0"),
        sections=(
            ContextSection(
                kind=ContextSectionKind.ENTITIES,
                title="Entities",
                items=(entity("light.kitchen"),),
            ),
        ),
        entity_contexts=(
            EntityContext(entity=entity("light.b")),
            EntityContext(entity=entity("light.a")),
        ),
        automation_contexts=(
            AutomationContext(
                automation=Automation(package=owned, id="evening"),
                package=owned,
            ),
        ),
        dashboard_contexts=(DashboardContext(dashboard=Dashboard(id="main", title="Main")),),
        package_contexts=(PackageContext(package=owned),),
    )


def populated_prompt() -> Prompt:
    """Return a programming prompt built from ``populated_context``."""
    return PromptBuilder().build(populated_context(), PromptType.PROGRAMMING)


def ordered_entity_prompt() -> Prompt:
    """Return entity sections in caller order, not alphabetical order."""
    content = (
        EntityContext(entity=entity("light.b", MappingProxyType({"z": 1, "m": 2}))),
        EntityContext(entity=entity("light.a", MappingProxyType({"m": 2, "z": 1}))),
    )
    return Prompt(
        prompt_type=PromptType.PROGRAMMING,
        system_instructions="Use only the supplied context.",
        task_description="Complete the task.",
        sections=(
            PromptSection(
                kind=PromptSectionKind.ENTITY,
                title="Entity Context",
                content=content,
            ),
        ),
        formatting_hints=("keep facts", "keep order"),
    )
