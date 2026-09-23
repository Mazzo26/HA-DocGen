"""Unit tests for package context projection."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path

import pytest

from ha_docgen.analysis import AnalysisModel
from ha_docgen.automation import Automation
from ha_docgen.context import AIContext, ContextGenerator, ContextMetadata, PackageContext
from ha_docgen.dashboard import Dashboard
from ha_docgen.helper import Helper
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
from ha_docgen.template import Template
from tests.support import PackageBuilder, build_relationship
from ha_docgen.yaml import YamlDocument, YamlRepository


def _package(name: str = "lighting", path: str | None = None) -> Package:
    builder = PackageBuilder(name)
    if path is not None:
        builder.with_path(Path(path))
    return builder.build()


def _entity(entity_id: str) -> Entity:
    return Entity(registry_id=entity_id, entity_id=entity_id, unique_id=entity_id)


def _automation(
    package: Package,
    automation_id: str | None = "evening",
    alias: str | None = "Evening",
) -> Automation:
    return Automation(package=package, id=automation_id, alias=alias)


def _script(
    package: Package,
    script_id: str | None = "evening",
    alias: str | None = "Evening",
) -> Script:
    return Script(package=package, id=script_id, alias=alias)


def _scene(
    package: Package,
    scene_id: str | None = "movie",
    name: str | None = "Movie",
) -> Scene:
    return Scene(package=package, id=scene_id, name=name)


def _helper(
    package: Package, helper_id: str = "guest", helper_type: str = "input_boolean"
) -> Helper:
    return Helper(package=package, type=helper_type, id=helper_id)


def _template(package: Package, kind: str = "state", source: str = "{{ value }}") -> Template:
    return Template(package=package, kind=kind, source=source, path=package.path)


def _dashboard(
    dashboard_id: str | None = "main",
    title: str | None = "Main",
    path: Path | None = None,
) -> Dashboard:
    return Dashboard(id=dashboard_id, title=title, path=path)


def _edge(
    source_type: ObjectType,
    source_id: str,
    target_type: ObjectType,
    target_id: str,
    relationship_type: RelationshipType = RelationshipType.REFERENCES,
) -> Relationship:
    return build_relationship(source_type, source_id, target_type, target_id, relationship_type)


def _generate(
    *,
    packages: tuple[Package, ...] = (),
    automations: tuple[Automation, ...] = (),
    scripts: tuple[Script, ...] = (),
    scenes: tuple[Scene, ...] = (),
    helpers: tuple[Helper, ...] = (),
    templates: tuple[Template, ...] = (),
    dashboards: tuple[Dashboard, ...] = (),
    entities: tuple[Entity, ...] = (),
    relationships: tuple[Relationship, ...] = (),
) -> tuple[PackageContext, ...]:
    context = ContextGenerator().generate(
        AnalysisModel(
            home_assistant_model=HomeAssistantModel(entities=entities),
            yaml_repository=YamlRepository(
                packages=packages,
                automations=automations,
                scripts=scripts,
                scenes=scenes,
                helpers=helpers,
                templates=templates,
                dashboards=dashboards,
            ),
            relationship_repository=RelationshipRepository(relationships),
        )
    )
    return context.package_contexts


def test_empty_repository_has_no_package_contexts() -> None:
    assert _generate() == ()


def test_single_package_keeps_original_metadata() -> None:
    package = _package()
    projected = _generate(packages=(package,))
    assert len(projected) == 1
    assert projected[0].package is package
    assert projected[0].package.name == "lighting"
    assert projected[0].package.path is package.path
    assert projected[0].package.document is package.document
    assert projected[0].automations == ()
    assert projected[0].dashboards == ()
    assert projected[0].relationships == ()


def test_multiple_packages_keep_only_their_own_members() -> None:
    lighting = _package("lighting")
    climate = _package("climate")
    light_automation = _automation(lighting, "evening", "Evening")
    climate_script = _script(climate, "heat", "Heat")
    projected = _generate(
        packages=(climate, lighting),
        automations=(light_automation,),
        scripts=(climate_script,),
    )
    assert [item.package for item in projected] == [climate, lighting]
    assert projected[0].package is climate
    assert projected[0].scripts == (climate_script,)
    assert projected[0].scripts[0] is climate_script
    assert projected[0].automations == ()
    assert projected[1].package is lighting
    assert projected[1].automations == (light_automation,)
    assert projected[1].automations[0] is light_automation
    assert projected[1].scripts == ()


def test_automations_keep_original_objects() -> None:
    package = _package()
    later = _automation(package, "zeta", "Zeta")
    earlier = _automation(package, "alpha", "Alpha")
    other = _automation(_package("climate"), "other", "Other")
    projected = _generate(packages=(package,), automations=(later, other, earlier))
    assert projected[0].automations == (earlier, later)
    assert projected[0].automations[0] is earlier
    assert projected[0].automations[1] is later


def test_scripts_keep_original_objects() -> None:
    package = _package()
    later = _script(package, "zeta", "Zeta")
    earlier = _script(package, "alpha", "Alpha")
    projected = _generate(packages=(package,), scripts=(later, earlier))
    assert projected[0].scripts == (earlier, later)
    assert projected[0].scripts[0] is earlier
    assert projected[0].scripts[1] is later


def test_scenes_keep_original_objects() -> None:
    package = _package()
    later = _scene(package, "zeta", "Zeta")
    earlier = _scene(package, "alpha", "Alpha")
    projected = _generate(packages=(package,), scenes=(later, earlier))
    assert projected[0].scenes == (earlier, later)
    assert projected[0].scenes[0] is earlier
    assert projected[0].scenes[1] is later


def test_helpers_keep_original_objects() -> None:
    package = _package()
    later = _helper(package, "zeta", "input_number")
    earlier = _helper(package, "alpha", "input_boolean")
    same_type = _helper(package, "guest", "input_boolean")
    projected = _generate(packages=(package,), helpers=(later, same_type, earlier))
    assert projected[0].helpers == (earlier, same_type, later)
    assert projected[0].helpers[0] is earlier
    assert projected[0].helpers[1] is same_type
    assert projected[0].helpers[2] is later


def test_templates_keep_original_objects() -> None:
    package = _package()
    later = _template(package, "value", "{{ zeta }}")
    earlier = _template(package, "state", "{{ alpha }}")
    projected = _generate(packages=(package,), templates=(later, earlier))
    assert projected[0].templates == (earlier, later)
    assert projected[0].templates[0] is earlier
    assert projected[0].templates[1] is later


def test_dashboards_are_not_inferred_as_members() -> None:
    package = _package()
    dashboard = _dashboard(path=package.path)
    relationship = _edge(ObjectType.PACKAGE, package.name, ObjectType.DASHBOARD, "main")
    projected = _generate(
        packages=(package,),
        dashboards=(dashboard,),
        relationships=(relationship,),
    )
    assert projected[0].dashboards == ()
    assert projected[0].referenced_dashboards == (dashboard,)
    assert projected[0].referenced_dashboards[0] is dashboard


def test_referenced_entities_keep_original_objects() -> None:
    package = _package()
    kitchen = _entity("light.kitchen")
    porch = _entity("light.porch")
    outgoing = _edge(ObjectType.PACKAGE, package.name, ObjectType.ENTITY, "light.porch")
    incoming = _edge(ObjectType.ENTITY, "light.kitchen", ObjectType.PACKAGE, package.name)
    device = _edge(ObjectType.PACKAGE, package.name, ObjectType.DEVICE, "device-1")
    projected = _generate(
        packages=(package,),
        entities=(porch, kitchen),
        relationships=(device, outgoing, incoming),
    )
    assert projected[0].referenced_entities == (kitchen, porch)
    assert projected[0].referenced_entities[0] is kitchen
    assert projected[0].referenced_entities[1] is porch
    assert device not in projected[0].relationships
    assert projected[0].unresolved_entity_ids == ()


def test_referenced_scripts_keep_original_objects() -> None:
    package = _package()
    other = _package("climate")
    script = _script(other, "heat", "Heat")
    relationship = _edge(ObjectType.PACKAGE, package.name, ObjectType.SCRIPT, "heat")
    projected = _generate(
        packages=(package,),
        scripts=(script,),
        relationships=(relationship,),
    )
    assert projected[0].scripts == ()
    assert projected[0].referenced_scripts == (script,)
    assert projected[0].referenced_scripts[0] is script


def test_referenced_scenes_keep_original_objects() -> None:
    package = _package()
    scene = _scene(package, "movie", "Movie")
    relationship = _edge(ObjectType.SCENE, "movie", ObjectType.PACKAGE, package.name)
    projected = _generate(
        packages=(package,),
        scenes=(scene,),
        relationships=(relationship,),
    )
    assert projected[0].scenes == (scene,)
    assert projected[0].scenes[0] is scene
    assert projected[0].referenced_scenes == (scene,)
    assert projected[0].referenced_scenes[0] is scene


def test_referenced_dashboards_keep_original_objects() -> None:
    package = _package()
    dashboard = _dashboard()
    relationship = _edge(
        ObjectType.DASHBOARD,
        "main",
        ObjectType.PACKAGE,
        package.name,
        RelationshipType.USES,
    )
    projected = _generate(
        packages=(package,),
        dashboards=(dashboard,),
        relationships=(relationship,),
    )
    assert projected[0].dashboards == ()
    assert projected[0].referenced_dashboards == (dashboard,)
    assert projected[0].referenced_dashboards[0] is dashboard
    assert projected[0].relationships == (relationship,)


def test_dashboard_lookup_uses_the_stored_id() -> None:
    package = _package()
    dashboard = _dashboard("main", "Overview")
    relationship = _edge(ObjectType.PACKAGE, package.name, ObjectType.DASHBOARD, "Overview")
    projected = _generate(
        packages=(package,),
        dashboards=(dashboard,),
        relationships=(relationship,),
    )
    assert projected[0].referenced_dashboards == ()
    assert projected[0].unresolved_dashboard_ids == ("Overview",)


def test_missing_references_stay_unresolved_ids() -> None:
    package = _package()
    script = _script(package, "evening", "Evening")
    relationships = (
        _edge(ObjectType.PACKAGE, package.name, ObjectType.ENTITY, "light.missing"),
        _edge(ObjectType.PACKAGE, package.name, ObjectType.SCRIPT, "script.evening"),
        _edge(ObjectType.PACKAGE, package.name, ObjectType.SCENE, "scene.movie"),
        _edge(ObjectType.PACKAGE, package.name, ObjectType.DASHBOARD, "missing"),
    )
    projected = _generate(
        packages=(package,),
        scripts=(script,),
        relationships=relationships,
    )
    assert projected[0].referenced_entities == ()
    assert projected[0].referenced_scripts == ()
    assert projected[0].referenced_scenes == ()
    assert projected[0].referenced_dashboards == ()
    assert projected[0].unresolved_entity_ids == ("light.missing",)
    assert projected[0].unresolved_script_ids == ("script.evening",)
    assert projected[0].unresolved_scene_ids == ("scene.movie",)
    assert projected[0].unresolved_dashboard_ids == ("missing",)


def test_duplicate_references_collapse_to_one_object() -> None:
    package = _package()
    kitchen = _entity("light.kitchen")
    relationships = (
        _edge(ObjectType.PACKAGE, package.name, ObjectType.ENTITY, "light.kitchen"),
        _edge(
            ObjectType.PACKAGE,
            package.name,
            ObjectType.ENTITY,
            "light.kitchen",
            RelationshipType.USES,
        ),
        _edge(ObjectType.PACKAGE, package.name, ObjectType.ENTITY, "light.missing"),
        _edge(
            ObjectType.PACKAGE,
            package.name,
            ObjectType.ENTITY,
            "light.missing",
            RelationshipType.USES,
        ),
    )
    projected = _generate(
        packages=(package,),
        entities=(kitchen,),
        relationships=relationships,
    )
    assert projected[0].referenced_entities == (kitchen,)
    assert projected[0].referenced_entities[0] is kitchen
    assert projected[0].unresolved_entity_ids == ("light.missing",)
    assert len(projected[0].relationships) == 4


def test_package_contexts_and_references_are_ordered() -> None:
    later = _package("zeta", "packages/zeta.yaml")
    earlier = _package("alpha", "packages/alpha.yaml")
    same_name = _package("alpha", "packages/a.yaml")
    relationships = (
        _edge(ObjectType.PACKAGE, "zeta", ObjectType.ENTITY, "light.zeta"),
        _edge(ObjectType.PACKAGE, "zeta", ObjectType.ENTITY, "light.alpha"),
    )
    projected = _generate(packages=(later, earlier, same_name), relationships=relationships)
    assert [item.package for item in projected] == [same_name, earlier, later]
    assert projected[0].package is same_name
    assert projected[1].package is earlier
    assert projected[2].package is later
    assert projected[2].unresolved_entity_ids == ("light.alpha", "light.zeta")
    assert [item.target_id for item in projected[2].relationships] == ["light.alpha", "light.zeta"]


def test_member_references_are_not_inferred_from_package_contents() -> None:
    package = _package()
    automation = _automation(package)
    entity = _entity("light.kitchen")
    relationship = _edge(ObjectType.AUTOMATION, "evening", ObjectType.ENTITY, "light.kitchen")
    projected = _generate(
        packages=(package,),
        automations=(automation,),
        entities=(entity,),
        relationships=(relationship,),
    )
    assert projected[0].automations == (automation,)
    assert projected[0].relationships == ()
    assert projected[0].referenced_entities == ()
    assert projected[0].unresolved_entity_ids == ()


def test_equal_package_copy_is_not_treated_as_membership() -> None:
    stored = _package()
    copy = Package(name=stored.name, path=stored.path, document=stored.document)
    automation = _automation(copy)
    projected = _generate(packages=(stored,), automations=(automation,))
    assert copy == stored
    assert projected[0].automations == ()


def test_projection_is_deterministic_and_does_not_mutate() -> None:
    package = _package()
    automation = _automation(package)
    entity = _entity("light.kitchen")
    relationship = _edge(ObjectType.PACKAGE, package.name, ObjectType.ENTITY, "light.kitchen")
    repository = YamlRepository(packages=(package,), automations=(automation,))
    analysis = AnalysisModel(
        home_assistant_model=HomeAssistantModel(entities=(entity,)),
        yaml_repository=repository,
        relationship_repository=RelationshipRepository((relationship,)),
    )
    automations = repository.automations
    generator = ContextGenerator()
    first = generator.generate(analysis)
    second = generator.generate(analysis)
    assert first == second
    assert first.package_contexts[0].package is package
    assert first.package_contexts[0].automations[0] is automation
    assert first.package_contexts[0].referenced_entities[0] is entity
    assert analysis.yaml_repository is repository
    assert repository.automations is automations


def test_package_context_is_immutable_and_serializable() -> None:
    document = YamlDocument(
        path=Path("packages/lighting.yaml"),
        text="name: lighting",
        data={"name": "lighting"},
    )
    package = Package(name="lighting", path=document.path, document=document)
    automation = Automation(package=package, id="evening", alias="Evening", raw={})
    relationship = _edge(ObjectType.PACKAGE, package.name, ObjectType.ENTITY, "light.kitchen")
    context = PackageContext(
        package=package,
        automations=(automation,),
        relationships=(relationship,),
    )
    encoded = json.dumps(asdict(context), default=str)
    assert context.automations[0] is automation
    assert context.package is package
    assert context.relationships[0] is relationship
    assert "lighting" in encoded
    assert "light.kitchen" in encoded
    with pytest.raises(FrozenInstanceError):
        context.automations = ()  # type: ignore[misc]


def test_projection_leaves_modules_13_1_13_2_and_13_3_unchanged() -> None:
    package = _package()
    entity = _entity("light.kitchen")
    automation = _automation(package)
    dashboard = _dashboard()
    relationship = _edge(ObjectType.AUTOMATION, "evening", ObjectType.ENTITY, "light.kitchen")
    registry = HomeAssistantModel(entities=(entity,))
    baseline = ContextGenerator().generate(
        AnalysisModel(
            home_assistant_model=registry,
            yaml_repository=YamlRepository(
                packages=(package,),
                automations=(automation,),
                dashboards=(dashboard,),
            ),
            relationship_repository=RelationshipRepository((relationship,)),
        )
    )
    extra = _package("climate")
    populated = ContextGenerator().generate(
        AnalysisModel(
            home_assistant_model=registry,
            yaml_repository=YamlRepository(
                packages=(package, extra),
                automations=(automation,),
                dashboards=(dashboard,),
                helpers=(_helper(extra),),
            ),
            relationship_repository=RelationshipRepository(
                (
                    relationship,
                    _edge(ObjectType.PACKAGE, "climate", ObjectType.DASHBOARD, "main"),
                )
            ),
        )
    )
    assert populated.metadata == baseline.metadata
    assert populated.sections == baseline.sections
    assert populated.entity_contexts == baseline.entity_contexts
    assert populated.automation_contexts == baseline.automation_contexts
    assert populated.dashboard_contexts == baseline.dashboard_contexts
    assert [item.package.name for item in baseline.package_contexts] == ["lighting"]
    assert [item.package.name for item in populated.package_contexts] == ["climate", "lighting"]
    assert populated.package_contexts[0].referenced_dashboards == (dashboard,)
    assert populated.package_contexts[0].dashboards == ()


def test_aicontext_without_package_contexts_stays_compatible() -> None:
    metadata = ContextMetadata()
    assert AIContext(metadata=metadata) == AIContext(metadata=metadata, package_contexts=())


def test_projection_does_not_touch_the_filesystem(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("filesystem access")

    monkeypatch.setattr("builtins.open", _fail)
    package = _package()
    projected = _generate(packages=(package,), automations=(_automation(package),))
    assert projected[0].package is package
    assert projected[0].automations[0].package is package
