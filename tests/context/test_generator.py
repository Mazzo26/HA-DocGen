"""Unit tests for ContextGenerator."""

from __future__ import annotations

import inspect

import pytest

from ha_docgen.analysis import AnalysisModel
from ha_docgen.context import AIContext, ContextGenerator, ContextSectionKind
from ha_docgen.registries.home_assistant_model import HomeAssistantModel
from ha_docgen.registries.models import (
    Area,
    ConfigEntry,
    Device,
    Entity,
    Floor,
    Label,
)
from ha_docgen.relationships import RelationshipRepository
from tests.support import (
    build_relationship,
    build_sample_yaml_repository,
)

_KIND_ORDER = (
    ContextSectionKind.AREAS,
    ContextSectionKind.CONFIG_ENTRIES,
    ContextSectionKind.DEVICES,
    ContextSectionKind.ENTITIES,
    ContextSectionKind.FLOORS,
    ContextSectionKind.LABELS,
)


def _analysis(model: HomeAssistantModel | None = None) -> AnalysisModel:
    return AnalysisModel(home_assistant_model=model or HomeAssistantModel())


def _entity(entity_id: str, *, device_id: str | None = None) -> Entity:
    return Entity(
        registry_id=entity_id,
        entity_id=entity_id,
        unique_id=entity_id,
        device_id=device_id,
    )


def _items(context: AIContext, kind: ContextSectionKind) -> tuple[object, ...]:
    return next(section.items for section in context.sections if section.kind is kind)


def test_generate_accepts_only_the_analysis_model() -> None:
    parameters = list(inspect.signature(ContextGenerator.generate).parameters)
    assert parameters == ["self", "analysis_model"]


def test_empty_model_has_empty_metadata_and_no_sections() -> None:
    context = ContextGenerator().generate(AnalysisModel())
    assert context.sections == ()
    assert context.entity_contexts == ()
    assert context.automation_contexts == ()
    assert context.dashboard_contexts == ()
    assert context.package_contexts == ()
    assert context.esphome_contexts == ()
    assert context.metadata.repository_name is None
    assert context.metadata.project_path is None
    assert context.metadata.version is None
    assert context.metadata.generated_at is None


def test_populated_model_keeps_original_objects() -> None:
    kitchen = _entity("light.kitchen", device_id="device-1")
    porch = _entity("light.porch")
    device = Device(registry_id="device-1")
    area = Area(registry_id="kitchen", name="Kitchen")
    label = Label(registry_id="night", name="Night")
    floor = Floor(registry_id="ground", name="Ground")
    entry = ConfigEntry(registry_id="entry-1", domain="hue", title="Hue")
    model = HomeAssistantModel(
        entities=(kitchen, porch),
        devices=(device,),
        areas=(area,),
        labels=(label,),
        floors=(floor,),
        config_entries=(entry,),
    )
    context = ContextGenerator().generate(_analysis(model))
    assert _items(context, ContextSectionKind.ENTITIES) == (kitchen, porch)
    assert _items(context, ContextSectionKind.ENTITIES)[0] is kitchen
    assert _items(context, ContextSectionKind.DEVICES) == (device,)
    assert _items(context, ContextSectionKind.DEVICES)[0] is device
    assert _items(context, ContextSectionKind.AREAS)[0] is area
    assert _items(context, ContextSectionKind.LABELS)[0] is label
    assert _items(context, ContextSectionKind.FLOORS)[0] is floor
    assert _items(context, ContextSectionKind.CONFIG_ENTRIES)[0] is entry
    assert [section.kind for section in context.sections] == list(_KIND_ORDER)


def test_empty_categories_are_omitted() -> None:
    entity = _entity("light.kitchen")
    context = ContextGenerator().generate(_analysis(HomeAssistantModel(entities=(entity,))))
    assert [section.kind for section in context.sections] == [ContextSectionKind.ENTITIES]
    assert _items(context, ContextSectionKind.ENTITIES) == (entity,)


def test_section_order_follows_identity_keys() -> None:
    first = _entity("light.b")
    second = _entity("light.a")
    third = Entity(registry_id="dup", entity_id="light.a", unique_id="dup")
    blank = Entity(registry_id="blank", entity_id="", unique_id="blank")
    model = HomeAssistantModel(entities=(first, third, blank, second))
    context = ContextGenerator().generate(_analysis(model))
    projected = _items(context, ContextSectionKind.ENTITIES)
    assert projected == (blank, third, second, first)
    assert projected[1] is third
    assert projected[2] is second


def test_device_link_stays_on_the_original_entity() -> None:
    entity = _entity("light.kitchen", device_id="device-1")
    device = Device(registry_id="device-1")
    context = ContextGenerator().generate(
        _analysis(HomeAssistantModel(entities=(entity,), devices=(device,)))
    )
    projected = _items(context, ContextSectionKind.ENTITIES)[0]
    assert projected is entity
    assert isinstance(projected, Entity)
    assert projected.device_id == "device-1"
    assert [section.kind for section in context.sections] == [
        ContextSectionKind.DEVICES,
        ContextSectionKind.ENTITIES,
    ]


def test_generation_is_idempotent_and_does_not_mutate_the_model() -> None:
    entity = _entity("light.kitchen")
    registry = HomeAssistantModel(entities=(entity,))
    analysis = _analysis(registry)
    entities = registry.entities
    generator = ContextGenerator()
    first = generator.generate(analysis)
    second = generator.generate(analysis)
    assert first == second
    assert first.sections[0].items[0] is entity
    assert second.sections[0].items[0] is entity
    assert analysis.home_assistant_model is registry
    assert registry.entities is entities
    assert registry.entities[0].entity_id == "light.kitchen"


def test_yaml_and_relationships_do_not_change_module_13_1_context() -> None:
    entity = _entity("light.kitchen")
    registry = HomeAssistantModel(entities=(entity,))
    baseline = ContextGenerator().generate(_analysis(registry))
    populated = ContextGenerator().generate(
        AnalysisModel(
            home_assistant_model=registry,
            yaml_repository=build_sample_yaml_repository(),
            relationship_repository=RelationshipRepository((build_relationship(),)),
        )
    )
    assert populated.metadata == baseline.metadata
    assert populated.sections == baseline.sections
    assert _items(populated, ContextSectionKind.ENTITIES) == (entity,)
    assert _items(populated, ContextSectionKind.ENTITIES)[0] is entity


def test_generator_does_not_touch_the_filesystem(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("filesystem access")

    monkeypatch.setattr("builtins.open", _fail)
    entity = _entity("light.kitchen")
    context = ContextGenerator().generate(_analysis(HomeAssistantModel(entities=(entity,))))
    assert _items(context, ContextSectionKind.ENTITIES)[0] is entity
