"""Unit tests for dashboard context projection."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

import pytest

from tools.ha_docgen.analysis import AnalysisModel
from tools.ha_docgen.automation import Automation
from tools.ha_docgen.context import ContextGenerator, DashboardContext
from tools.ha_docgen.dashboard import Dashboard
from tools.ha_docgen.packages import Package
from tools.ha_docgen.registries.home_assistant_model import HomeAssistantModel
from tools.ha_docgen.registries.models import Entity
from tools.ha_docgen.relationships import (
    ObjectType,
    Relationship,
    RelationshipRepository,
    RelationshipType,
)
from tools.ha_docgen.tests.support import PackageBuilder, build_relationship
from tools.ha_docgen.yaml import YamlRepository


def _package(name: str = "lighting") -> Package:
    return PackageBuilder(name).build()


def _entity(entity_id: str) -> Entity:
    return Entity(registry_id=entity_id, entity_id=entity_id, unique_id=entity_id)


def _automation(
    package: Package,
    automation_id: str | None = "evening",
    alias: str | None = "Evening",
) -> Automation:
    return Automation(package=package, id=automation_id, alias=alias)


def _view(title: str, cards: object | None = None) -> Mapping[str, object]:
    payload: dict[str, object] = {"title": title}
    if cards is not None:
        payload["cards"] = cards
    return MappingProxyType(payload)


def _dashboard(
    dashboard_id: str | None = "main",
    title: str | None = "Main",
    views: tuple[Mapping[str, object], ...] = (),
    path: Path | None = None,
) -> Dashboard:
    return Dashboard(id=dashboard_id, title=title, mode="yaml", path=path, views=views)


def _edge(
    source_type: ObjectType,
    source_id: str,
    target_type: ObjectType,
    target_id: str,
    relationship_type: RelationshipType = RelationshipType.REFERENCES,
) -> Relationship:
    return build_relationship(
        source_type,
        source_id,
        target_type,
        target_id,
        relationship_type,
    )


def _generate(
    *,
    dashboards: tuple[Dashboard, ...] = (),
    entities: tuple[Entity, ...] = (),
    automations: tuple[Automation, ...] = (),
    packages: tuple[Package, ...] = (),
    relationships: tuple[Relationship, ...] = (),
) -> tuple[DashboardContext, ...]:
    context = ContextGenerator().generate(
        AnalysisModel(
            home_assistant_model=HomeAssistantModel(entities=entities),
            yaml_repository=YamlRepository(
                packages=packages,
                automations=automations,
                dashboards=dashboards,
            ),
            relationship_repository=RelationshipRepository(relationships),
        )
    )
    return context.dashboard_contexts


def test_empty_repository_has_no_dashboard_contexts() -> None:
    assert _generate() == ()


def test_empty_dashboard_keeps_the_original_object() -> None:
    dashboard = _dashboard(views=())
    projected = _generate(dashboards=(dashboard,))
    assert len(projected) == 1
    assert projected[0].dashboard is dashboard
    assert projected[0].views == ()
    assert projected[0].referenced_entities == ()
    assert projected[0].related_automations == ()
    assert projected[0].relationships == ()


def test_metadata_and_views_stay_on_the_original_dashboard() -> None:
    home = _view("Home", [{"type": "button", "entity": "light.kitchen"}])
    outside = _view("Outside")
    path = Path("dashboards/main.yaml")
    dashboard = _dashboard(views=(home, outside), path=path)
    projected = _generate(dashboards=(dashboard,))
    assert projected[0].dashboard is dashboard
    assert projected[0].dashboard.title == "Main"
    assert projected[0].dashboard.mode == "yaml"
    assert projected[0].dashboard.path is path
    assert projected[0].views is dashboard.views
    assert projected[0].views == (home, outside)
    assert projected[0].referenced_entities == ()
    assert projected[0].unresolved_entity_ids == ()
    assert "cards" not in DashboardContext.__dataclass_fields__


def test_referenced_entities_keep_original_objects() -> None:
    dashboard = _dashboard()
    kitchen = _entity("light.kitchen")
    porch = _entity("light.porch")
    projected = _generate(
        dashboards=(dashboard,),
        entities=(kitchen, porch),
        relationships=(
            _edge(ObjectType.DASHBOARD, "main", ObjectType.ENTITY, "light.porch"),
            _edge(ObjectType.ENTITY, "light.kitchen", ObjectType.DASHBOARD, "main"),
        ),
    )
    assert projected[0].referenced_entities == (kitchen, porch)
    assert projected[0].referenced_entities[0] is kitchen
    assert projected[0].referenced_entities[1] is porch
    assert projected[0].unresolved_entity_ids == ()


def test_duplicate_entity_references_collapse() -> None:
    dashboard = _dashboard()
    kitchen = _entity("light.kitchen")
    projected = _generate(
        dashboards=(dashboard,),
        entities=(kitchen,),
        relationships=(
            _edge(ObjectType.DASHBOARD, "main", ObjectType.ENTITY, "light.kitchen"),
            _edge(
                ObjectType.DASHBOARD,
                "main",
                ObjectType.ENTITY,
                "light.kitchen",
                RelationshipType.USES,
            ),
            _edge(ObjectType.DASHBOARD, "main", ObjectType.ENTITY, "light.kitchen"),
        ),
    )
    assert projected[0].referenced_entities == (kitchen,)
    assert projected[0].referenced_entities[0] is kitchen
    assert len(projected[0].relationships) == 2


def test_missing_entity_stays_unresolved() -> None:
    dashboard = _dashboard()
    projected = _generate(
        dashboards=(dashboard,),
        relationships=(
            _edge(ObjectType.DASHBOARD, "main", ObjectType.ENTITY, "light.missing"),
            _edge(ObjectType.DASHBOARD, "main", ObjectType.ENTITY, "kitchen"),
        ),
    )
    assert projected[0].referenced_entities == ()
    assert projected[0].unresolved_entity_ids == ("kitchen", "light.missing")


def test_view_contents_are_not_treated_as_relationships() -> None:
    view = _view("Home", [{"type": "entities", "entities": ["light.hidden"]}])
    dashboard = _dashboard(views=(view,))
    kitchen = _entity("light.kitchen")
    projected = _generate(
        dashboards=(dashboard,),
        entities=(kitchen, _entity("light.hidden")),
        relationships=(_edge(ObjectType.DASHBOARD, "main", ObjectType.ENTITY, "light.kitchen"),),
    )
    assert projected[0].views[0] is view
    assert projected[0].referenced_entities == (kitchen,)
    assert projected[0].unresolved_entity_ids == ()


def test_related_automations_keep_original_objects() -> None:
    package = _package()
    dashboard = _dashboard()
    evening = _automation(package, "evening", "Evening")
    morning = _automation(package, "morning", "Morning")
    projected = _generate(
        dashboards=(dashboard,),
        automations=(evening, morning),
        packages=(package,),
        relationships=(
            _edge(ObjectType.DASHBOARD, "main", ObjectType.AUTOMATION, "morning"),
            _edge(ObjectType.AUTOMATION, "evening", ObjectType.DASHBOARD, "main"),
        ),
    )
    assert projected[0].related_automations == (evening, morning)
    assert projected[0].related_automations[0] is evening
    assert projected[0].related_automations[1] is morning
    assert projected[0].unresolved_automation_ids == ()


def test_missing_automation_stays_unresolved_without_alias_lookup() -> None:
    package = _package()
    dashboard = _dashboard()
    evening = _automation(package, "evening", "Evening")
    alias_only = _automation(package, None, "Movie")
    projected = _generate(
        dashboards=(dashboard,),
        automations=(evening, alias_only),
        packages=(package,),
        relationships=(
            _edge(ObjectType.DASHBOARD, "main", ObjectType.AUTOMATION, "missing"),
            _edge(ObjectType.DASHBOARD, "main", ObjectType.AUTOMATION, "Evening"),
            _edge(ObjectType.DASHBOARD, "main", ObjectType.AUTOMATION, "Movie"),
        ),
    )
    assert projected[0].related_automations == ()
    assert projected[0].unresolved_automation_ids == ("Evening", "Movie", "missing")


def test_title_is_the_relationship_key_when_id_is_absent() -> None:
    dashboard = _dashboard(None, "Overview")
    entity = _entity("light.kitchen")
    projected = _generate(
        dashboards=(dashboard,),
        entities=(entity,),
        relationships=(
            _edge(ObjectType.DASHBOARD, "Overview", ObjectType.ENTITY, "light.kitchen"),
        ),
    )
    assert projected[0].referenced_entities == (entity,)


def test_id_is_preferred_over_title() -> None:
    dashboard = _dashboard("main", "Overview")
    entity = _entity("light.kitchen")
    projected = _generate(
        dashboards=(dashboard,),
        entities=(entity,),
        relationships=(
            _edge(ObjectType.DASHBOARD, "Overview", ObjectType.ENTITY, "light.kitchen"),
        ),
    )
    assert projected[0].referenced_entities == ()
    assert projected[0].unresolved_entity_ids == ()
    assert projected[0].relationships == ()


def test_dashboard_without_identity_has_no_relationships() -> None:
    dashboard = _dashboard(None, None, path=Path("dashboards/orphan.yaml"))
    projected = _generate(
        dashboards=(dashboard,),
        entities=(_entity("light.kitchen"),),
        relationships=(
            _edge(
                ObjectType.DASHBOARD,
                "dashboards/orphan.yaml",
                ObjectType.ENTITY,
                "light.kitchen",
            ),
        ),
    )
    assert projected[0].dashboard is dashboard
    assert projected[0].relationships == ()
    assert projected[0].referenced_entities == ()


def test_device_relationships_are_not_projected() -> None:
    dashboard = _dashboard()
    projected = _generate(
        dashboards=(dashboard,),
        relationships=(_edge(ObjectType.DASHBOARD, "main", ObjectType.DEVICE, "device-1"),),
    )
    assert projected[0].relationships == ()
    assert projected[0].referenced_entities == ()
    assert projected[0].related_automations == ()
    assert projected[0].unresolved_entity_ids == ()
    assert projected[0].unresolved_automation_ids == ()


def test_dashboard_contexts_are_ordered_by_identity() -> None:
    by_title = _dashboard(None, "Alpha", path=Path("dashboards/z.yaml"))
    by_id = _dashboard("main", "Zebra", path=Path("dashboards/m.yaml"))
    by_path = _dashboard("main", "Zebra", path=Path("dashboards/a.yaml"))
    projected = _generate(dashboards=(by_id, by_title, by_path))
    assert [item.dashboard for item in projected] == [by_title, by_path, by_id]
    assert projected[0].dashboard is by_title
    assert projected[1].dashboard is by_path
    assert projected[2].dashboard is by_id


def test_projection_is_deterministic_and_does_not_mutate() -> None:
    card = {"type": "button", "entity": "light.kitchen"}
    cards = [card]
    view = _view("Home", cards)
    dashboard = _dashboard(views=(view,))
    analysis = AnalysisModel(
        yaml_repository=YamlRepository(dashboards=(dashboard,)),
    )
    generator = ContextGenerator()
    first = generator.generate(analysis)
    second = generator.generate(analysis)
    assert first == second
    assert first.dashboard_contexts[0].dashboard is dashboard
    assert first.dashboard_contexts[0].views is dashboard.views
    assert first.dashboard_contexts[0].views[0] is view
    assert dashboard.views[0].get("cards") is cards
    assert cards == [card]


def test_dashboard_projection_leaves_module_13_1_and_13_2_unchanged() -> None:
    package = _package()
    entity = _entity("light.kitchen")
    automation = _automation(package)
    relationship = _edge(
        ObjectType.AUTOMATION,
        "evening",
        ObjectType.ENTITY,
        "light.kitchen",
    )
    registry = HomeAssistantModel(entities=(entity,))
    repository = YamlRepository(
        packages=(package,),
        automations=(automation,),
    )
    relationships = RelationshipRepository((relationship,))
    baseline = ContextGenerator().generate(
        AnalysisModel(
            home_assistant_model=registry,
            yaml_repository=repository,
            relationship_repository=relationships,
        )
    )
    populated = ContextGenerator().generate(
        AnalysisModel(
            home_assistant_model=registry,
            yaml_repository=YamlRepository(
                packages=(package,),
                automations=(automation,),
                dashboards=(_dashboard(),),
            ),
            relationship_repository=relationships,
        )
    )
    assert populated.metadata == baseline.metadata
    assert populated.sections == baseline.sections
    assert populated.entity_contexts == baseline.entity_contexts
    assert populated.automation_contexts == baseline.automation_contexts
    assert baseline.dashboard_contexts == ()
    assert populated.dashboard_contexts[0].dashboard.id == "main"


def test_projection_does_not_touch_the_filesystem(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("filesystem access")

    monkeypatch.setattr("builtins.open", _fail)
    view = _view("Home", [{"type": "button"}])
    dashboard = _dashboard(views=(view,))
    projected = _generate(dashboards=(dashboard,))
    assert projected[0].views[0] is view
