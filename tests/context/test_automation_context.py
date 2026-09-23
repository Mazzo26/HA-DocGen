"""Unit tests for automation context projection."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from ha_docgen.analysis import AnalysisModel
from ha_docgen.automation import Automation
from ha_docgen.context import AutomationContext, ContextGenerator
from ha_docgen.packages import Package
from ha_docgen.registries.home_assistant_model import HomeAssistantModel
from ha_docgen.registries.models import Entity
from ha_docgen.relationships import (
    ObjectType,
    Relationship,
    RelationshipRepository,
    RelationshipType,
)
from ha_docgen.scene import Scene
from ha_docgen.script import Script
from tests.support import PackageBuilder, build_relationship
from ha_docgen.yaml import YamlRepository


def _package(name: str = "lighting") -> Package:
    return PackageBuilder(name).build()


def _entity(entity_id: str) -> Entity:
    return Entity(registry_id=entity_id, entity_id=entity_id, unique_id=entity_id)


def _automation(
    package: Package,
    automation_id: str | None = "evening",
    alias: str | None = "Evening",
    *,
    triggers: object = (),
    conditions: object = (),
    actions: object = (),
    raw: object | None = None,
) -> Automation:
    stored_raw = raw if raw is not None else MappingProxyType({})
    return Automation(
        package=package,
        id=automation_id,
        alias=alias,
        triggers=triggers,
        conditions=conditions,
        actions=actions,
        raw=stored_raw,  # type: ignore[arg-type]
    )


def _generate(
    *,
    automations: tuple[Automation, ...] = (),
    entities: tuple[Entity, ...] = (),
    scripts: tuple[Script, ...] = (),
    scenes: tuple[Scene, ...] = (),
    packages: tuple[Package, ...] = (),
    relationships: tuple[Relationship, ...] = (),
) -> tuple[AutomationContext, ...]:
    context = ContextGenerator().generate(
        AnalysisModel(
            home_assistant_model=HomeAssistantModel(entities=entities),
            yaml_repository=YamlRepository(
                packages=packages,
                automations=automations,
                scripts=scripts,
                scenes=scenes,
            ),
            relationship_repository=RelationshipRepository(relationships),
        )
    )
    return context.automation_contexts


def test_triggers_conditions_actions_and_package_keep_original_objects() -> None:
    package = _package()
    triggers = ({"platform": "state", "entity_id": "light.kitchen"},)
    conditions = ({"condition": "state", "entity_id": "binary_sensor.door"},)
    actions = ({"action": "light.turn_on"},)
    raw = MappingProxyType({"id": "evening", "alias": "Evening"})
    automation = _automation(
        package,
        triggers=triggers,
        conditions=conditions,
        actions=actions,
        raw=raw,
    )
    projected = _generate(automations=(automation,), packages=(package,))
    assert len(projected) == 1
    assert projected[0].automation is automation
    assert projected[0].automation.triggers is triggers
    assert projected[0].automation.conditions is conditions
    assert projected[0].automation.actions is actions
    assert projected[0].automation.raw is raw
    assert projected[0].package is package
    assert projected[0].package is automation.package


def test_related_entities_scripts_and_scenes_keep_original_objects() -> None:
    package = _package()
    automation = _automation(package)
    kitchen = _entity("light.kitchen")
    porch = _entity("light.porch")
    script = Script(package=package, id="evening", alias="Evening")
    scene = Scene(package=package, id="movie", name="Movie")
    relationships = (
        build_relationship(
            ObjectType.AUTOMATION,
            "evening",
            ObjectType.ENTITY,
            "light.porch",
            RelationshipType.REFERENCES,
        ),
        build_relationship(
            ObjectType.AUTOMATION,
            "evening",
            ObjectType.ENTITY,
            "light.kitchen",
            RelationshipType.REFERENCES,
        ),
        build_relationship(
            ObjectType.SCRIPT,
            "evening",
            ObjectType.AUTOMATION,
            "evening",
            RelationshipType.REFERENCES,
        ),
        build_relationship(
            ObjectType.AUTOMATION,
            "evening",
            ObjectType.SCENE,
            "movie",
            RelationshipType.REFERENCES,
        ),
        build_relationship(
            ObjectType.AUTOMATION,
            "evening",
            ObjectType.DEVICE,
            "device-1",
            RelationshipType.REFERENCES,
        ),
    )
    projected = _generate(
        automations=(automation,),
        entities=(kitchen, porch),
        scripts=(script,),
        scenes=(scene,),
        packages=(package,),
        relationships=relationships,
    )
    assert projected[0].referenced_entities == (kitchen, porch)
    assert projected[0].referenced_entities[0] is kitchen
    assert projected[0].referenced_entities[1] is porch
    assert projected[0].related_scripts == (script,)
    assert projected[0].related_scripts[0] is script
    assert projected[0].related_scenes == (scene,)
    assert projected[0].related_scenes[0] is scene
    assert all(item.target_type is not ObjectType.DEVICE for item in projected[0].relationships)
    assert projected[0].unresolved_entity_ids == ()
    assert projected[0].unresolved_script_ids == ()
    assert projected[0].unresolved_scene_ids == ()


def test_missing_references_stay_unresolved_ids() -> None:
    package = _package()
    automation = _automation(package)
    script = Script(package=package, id="evening", alias="Evening")
    relationships = (
        build_relationship(
            ObjectType.AUTOMATION,
            "evening",
            ObjectType.ENTITY,
            "light.missing",
            RelationshipType.REFERENCES,
        ),
        build_relationship(
            ObjectType.AUTOMATION,
            "evening",
            ObjectType.SCRIPT,
            "script.evening",
            RelationshipType.REFERENCES,
        ),
        build_relationship(
            ObjectType.AUTOMATION,
            "evening",
            ObjectType.SCENE,
            "scene.movie",
            RelationshipType.REFERENCES,
        ),
    )
    projected = _generate(
        automations=(automation,),
        scripts=(script,),
        packages=(package,),
        relationships=relationships,
    )
    assert projected[0].referenced_entities == ()
    assert projected[0].related_scripts == ()
    assert projected[0].related_scenes == ()
    assert projected[0].unresolved_entity_ids == ("light.missing",)
    assert projected[0].unresolved_script_ids == ("script.evening",)
    assert projected[0].unresolved_scene_ids == ("scene.movie",)


def test_duplicate_references_collapse_to_one_object() -> None:
    package = _package()
    automation = _automation(package)
    kitchen = _entity("light.kitchen")
    relationships = (
        build_relationship(
            ObjectType.AUTOMATION,
            "evening",
            ObjectType.ENTITY,
            "light.kitchen",
            RelationshipType.REFERENCES,
        ),
        build_relationship(
            ObjectType.AUTOMATION,
            "evening",
            ObjectType.ENTITY,
            "light.kitchen",
            RelationshipType.USES,
        ),
        build_relationship(
            ObjectType.AUTOMATION,
            "evening",
            ObjectType.ENTITY,
            "light.missing",
            RelationshipType.REFERENCES,
        ),
        build_relationship(
            ObjectType.AUTOMATION,
            "evening",
            ObjectType.ENTITY,
            "light.missing",
            RelationshipType.USES,
        ),
    )
    projected = _generate(
        automations=(automation,),
        entities=(kitchen,),
        packages=(package,),
        relationships=relationships,
    )
    assert projected[0].referenced_entities == (kitchen,)
    assert projected[0].referenced_entities[0] is kitchen
    assert projected[0].unresolved_entity_ids == ("light.missing",)
    assert len(projected[0].relationships) == 4


def test_automation_contexts_are_ordered_by_identity() -> None:
    package = _package()
    later = _automation(package, "zeta", "Zeta")
    earlier = _automation(package, "alpha", "Alpha")
    projected = _generate(automations=(later, earlier), packages=(package,))
    assert [item.automation.id for item in projected] == ["alpha", "zeta"]
    assert projected[0].automation is earlier
    assert projected[1].automation is later


def test_unresolved_ids_are_ordered() -> None:
    package = _package()
    automation = _automation(package)
    relationships = (
        build_relationship(
            ObjectType.AUTOMATION,
            "evening",
            ObjectType.ENTITY,
            "light.zeta",
            RelationshipType.REFERENCES,
        ),
        build_relationship(
            ObjectType.AUTOMATION,
            "evening",
            ObjectType.ENTITY,
            "light.alpha",
            RelationshipType.REFERENCES,
        ),
    )
    projected = _generate(
        automations=(automation,),
        packages=(package,),
        relationships=relationships,
    )
    assert projected[0].unresolved_entity_ids == ("light.alpha", "light.zeta")


def test_automation_without_identity_keeps_yaml_and_no_relationships() -> None:
    package = _package()
    automation = _automation(package, None, None, triggers=({"platform": "time"},))
    relationship = build_relationship(
        ObjectType.AUTOMATION,
        "evening",
        ObjectType.ENTITY,
        "light.kitchen",
        RelationshipType.REFERENCES,
    )
    projected = _generate(
        automations=(automation,),
        packages=(package,),
        relationships=(relationship,),
    )
    assert projected[0].automation is automation
    assert projected[0].automation.triggers == ({"platform": "time"},)
    assert projected[0].relationships == ()
    assert projected[0].referenced_entities == ()
    assert projected[0].unresolved_entity_ids == ()


def test_alias_is_the_relationship_key_only_when_id_is_absent() -> None:
    package = _package()
    by_alias = _automation(package, None, "Evening lights")
    by_id = _automation(package, "evening", "Evening lights")
    alias_edge = build_relationship(
        ObjectType.AUTOMATION,
        "Evening lights",
        ObjectType.ENTITY,
        "light.alias",
        RelationshipType.REFERENCES,
    )
    id_edge = build_relationship(
        ObjectType.AUTOMATION,
        "evening",
        ObjectType.ENTITY,
        "light.id",
        RelationshipType.REFERENCES,
    )
    alias_context = _generate(
        automations=(by_alias,),
        packages=(package,),
        relationships=(alias_edge, id_edge),
    )
    id_context = _generate(
        automations=(by_id,),
        packages=(package,),
        relationships=(alias_edge, id_edge),
    )
    assert alias_context[0].unresolved_entity_ids == ("light.alias",)
    assert id_context[0].unresolved_entity_ids == ("light.id",)


def test_generation_is_idempotent_and_does_not_read_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("filesystem access")

    monkeypatch.setattr("builtins.open", _fail)
    package = _package()
    automation = _automation(package)
    entity = _entity("light.kitchen")
    relationship = build_relationship(
        ObjectType.AUTOMATION,
        "evening",
        ObjectType.ENTITY,
        "light.kitchen",
        RelationshipType.REFERENCES,
    )
    analysis = AnalysisModel(
        home_assistant_model=HomeAssistantModel(entities=(entity,)),
        yaml_repository=YamlRepository(packages=(package,), automations=(automation,)),
        relationship_repository=RelationshipRepository((relationship,)),
    )
    automations = analysis.yaml_repository.automations
    generator = ContextGenerator()
    first = generator.generate(analysis)
    second = generator.generate(analysis)
    assert first == second
    assert first.automation_contexts[0].automation is automation
    assert first.automation_contexts[0].referenced_entities[0] is entity
    assert analysis.yaml_repository.automations is automations
