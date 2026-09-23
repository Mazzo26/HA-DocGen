"""Unit tests for Home Assistant inventory reporting."""

from __future__ import annotations

import inspect
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

from ha_docgen.analysis import AnalysisModel
from ha_docgen.automation import Automation
from ha_docgen.blueprint import Blueprint
from ha_docgen.dashboard import Dashboard
from ha_docgen.esphome import ESPHomeDevice
from ha_docgen.helper import Helper
from ha_docgen.packages import Package
from ha_docgen.registries import HomeAssistantModel, Label
from ha_docgen.relationships import RelationshipRepository
from ha_docgen.reporting import (
    DiscoveredFile,
    HomeAssistantInventory,
    HomeAssistantInventoryGenerator,
    InventoryReportGenerator,
)
from ha_docgen.scene import Scene
from ha_docgen.script import Script
from ha_docgen.yaml import YamlDocument, YamlRepository
from tests.support.paths import PACKAGE_SOURCE_ROOT


def _package(name: str, relative: str) -> Package:
    path = Path(relative)
    return Package(name=name, path=path, document=YamlDocument(path=path, text="", data={}))


def _automation(package: Package, automation_id: str | None, alias: str | None) -> Automation:
    return Automation(package=package, id=automation_id, alias=alias)


def _script(package: Package, script_id: str | None, alias: str | None) -> Script:
    return Script(package=package, id=script_id, alias=alias)


def _scene(package: Package, scene_id: str | None, name: str | None) -> Scene:
    return Scene(package=package, id=scene_id, name=name)


def _helper(package: Package, helper_type: str, helper_id: str) -> Helper:
    return Helper(package=package, type=helper_type, id=helper_id)


def _label(registry_id: str, name: str) -> Label:
    return Label(registry_id=registry_id, name=name)


def _inventory(
    *,
    packages: tuple[Package, ...] = (),
    automations: tuple[Automation, ...] = (),
    scripts: tuple[Script, ...] = (),
    scenes: tuple[Scene, ...] = (),
    blueprints: tuple[Blueprint, ...] = (),
    helpers: tuple[Helper, ...] = (),
    labels: tuple[Label, ...] = (),
    dashboards: tuple[Dashboard, ...] = (),
    esphome_devices: tuple[ESPHomeDevice, ...] = (),
    relationships: RelationshipRepository | None = None,
) -> tuple[AnalysisModel, HomeAssistantInventory]:
    analysis = AnalysisModel(
        home_assistant_model=HomeAssistantModel(labels=labels),
        yaml_repository=YamlRepository(
            packages=packages,
            automations=automations,
            scripts=scripts,
            scenes=scenes,
            blueprints=blueprints,
            helpers=helpers,
            dashboards=dashboards,
            esphome_devices=esphome_devices,
        ),
        relationship_repository=relationships or RelationshipRepository(),
    )
    return analysis, HomeAssistantInventoryGenerator().generate(analysis)


def test_empty_inventory() -> None:
    analysis, inventory = _inventory()
    assert inventory == HomeAssistantInventory()
    assert inventory.discovered_files == ()
    assert inventory.automations == ()
    assert inventory.scripts == ()
    assert inventory.scenes == ()
    assert inventory.blueprints == ()
    assert inventory.helpers == ()
    assert inventory.labels == ()
    assert analysis.yaml_repository.automations == ()


def test_automation_inventory_keeps_repository_objects() -> None:
    later = _package("later", "packages/later.yaml")
    earlier = _package("earlier", "packages/earlier.yaml")
    second = _automation(later, "zeta", "Second")
    first = _automation(earlier, "alpha", "First")
    missing = _automation(earlier, None, "Missing")
    _analysis, inventory = _inventory(
        packages=(later, earlier),
        automations=(second, missing, first),
    )
    assert inventory.automations == (first, second, missing)
    assert inventory.automations[0] is first
    assert inventory.automations[0].package is earlier


def test_script_inventory_orders_by_identity() -> None:
    package = _package("scripts", "packages/scripts.yaml")
    later = _script(package, "zeta", "Later")
    earlier = _script(package, "alpha", "Earlier")
    _analysis, inventory = _inventory(packages=(package,), scripts=(later, earlier))
    assert inventory.scripts == (earlier, later)
    assert inventory.scripts[0] is earlier
    assert inventory.scripts[0].package is package


def test_scene_inventory_orders_by_identity() -> None:
    package = _package("scenes", "packages/scenes.yaml")
    later = _scene(package, "zeta", "Later")
    earlier = _scene(package, "alpha", "Earlier")
    _analysis, inventory = _inventory(packages=(package,), scenes=(later, earlier))
    assert inventory.scenes == (earlier, later)
    assert inventory.scenes[0] is earlier
    assert inventory.scenes[0].package is package


def test_blueprint_inventory_orders_by_path_name_and_domain() -> None:
    later = Blueprint(name="Zeta", domain="script", path=Path("blueprints/zeta.yaml"))
    earlier = Blueprint(name="Alpha", domain="automation", path=Path("blueprints/alpha.yaml"))
    missing = Blueprint(name="Loose", domain="automation", path=None)
    _analysis, inventory = _inventory(blueprints=(later, missing, earlier))
    assert inventory.blueprints == (earlier, later, missing)
    assert inventory.blueprints[0] is earlier
    assert inventory.blueprints[2].path is None


def test_helper_inventory_orders_by_type_and_id() -> None:
    package = _package("helpers", "packages/helpers.yaml")
    boolean = _helper(package, "input_boolean", "guest")
    number = _helper(package, "input_number", "alpha")
    _analysis, inventory = _inventory(packages=(package,), helpers=(number, boolean))
    assert inventory.helpers == (boolean, number)
    assert inventory.helpers[0] is boolean
    assert inventory.helpers[0].package is package


def test_label_inventory_orders_by_registry_id() -> None:
    later = _label("zeta", "Zeta")
    earlier = _label("alpha", "Alpha")
    analysis, inventory = _inventory(labels=(later, earlier))
    assert inventory.labels == (earlier, later)
    assert inventory.labels[0] is earlier
    assert inventory.labels[0] is analysis.home_assistant_model.labels[1]


def test_deterministic_ordering_is_independent_of_input_order() -> None:
    package_b = _package("b", "packages/b.yaml")
    package_a = _package("a", "packages/a.yaml")
    automation_b = _automation(package_b, "b", "B")
    automation_a = _automation(package_a, "a", "A")
    script_b = _script(package_b, "b", "B")
    script_a = _script(package_a, "a", "A")
    scene_b = _scene(package_b, "b", "B")
    scene_a = _scene(package_a, "a", "A")
    helper_b = _helper(package_b, "input_text", "b")
    helper_a = _helper(package_a, "input_boolean", "a")
    blueprint_b = Blueprint(name="B", domain="script", path=Path("blueprints/b.yaml"))
    blueprint_a = Blueprint(name="A", domain="automation", path=Path("blueprints/a.yaml"))
    label_b = _label("b", "B")
    label_a = _label("a", "A")
    _forward, forward = _inventory(
        packages=(package_b, package_a),
        automations=(automation_b, automation_a),
        scripts=(script_b, script_a),
        scenes=(scene_b, scene_a),
        blueprints=(blueprint_b, blueprint_a),
        helpers=(helper_b, helper_a),
        labels=(label_b, label_a),
    )
    _reverse, reverse = _inventory(
        packages=(package_a, package_b),
        automations=(automation_a, automation_b),
        scripts=(script_a, script_b),
        scenes=(scene_a, scene_b),
        blueprints=(blueprint_a, blueprint_b),
        helpers=(helper_a, helper_b),
        labels=(label_a, label_b),
    )
    assert forward == reverse
    assert [item.path.as_posix() for item in forward.discovered_files] == [
        "blueprints/a.yaml",
        "blueprints/b.yaml",
        "packages/a.yaml",
        "packages/b.yaml",
    ]
    again = HomeAssistantInventoryGenerator().generate(_forward)
    assert again == forward


def test_discovered_files_are_distinct_from_parsed_objects() -> None:
    empty = _package("empty", "packages/empty.yaml")
    shared = _package("shared", "packages/shared.yaml")
    first = _automation(shared, "one", "One")
    second = _automation(shared, "two", "Two")
    helper = _helper(shared, "input_boolean", "guest")
    blueprint = Blueprint(name="Motion", domain="automation", path=Path("blueprints/motion.yaml"))
    loose = Blueprint(name="Loose", domain="script", path=None)
    label = _label("energy", "Energy")
    dashboard = Dashboard(id="overview", path=Path("dashboards/overview.yaml"))
    device = ESPHomeDevice(name="sensor", path=Path("esphome/sensor.yaml"))
    _analysis, inventory = _inventory(
        packages=(shared, empty),
        automations=(second, first),
        helpers=(helper,),
        blueprints=(loose, blueprint),
        labels=(label,),
        dashboards=(dashboard,),
        esphome_devices=(device,),
    )
    paths = tuple(item.path.as_posix() for item in inventory.discovered_files)
    assert paths == ("blueprints/motion.yaml", "packages/empty.yaml", "packages/shared.yaml")
    assert inventory.discovered_files[1].path is empty.path
    assert inventory.discovered_files[2].path is shared.path
    assert inventory.automations == (first, second)
    assert all(not isinstance(item, Automation) for item in inventory.discovered_files)
    assert helper not in inventory.discovered_files
    assert inventory.blueprints == (blueprint, loose)
    assert inventory.labels == (label,)
    assert "dashboards/overview.yaml" not in paths
    assert "esphome/sensor.yaml" not in paths
    assert len(inventory.discovered_files) != len(inventory.automations)


def test_repeated_paths_collapse_without_dropping_objects() -> None:
    package = _package("shared", "blueprints/motion.yaml")
    blueprint = Blueprint(name="Motion", domain="automation", path=package.path)
    automation = _automation(package, "motion", "Motion")
    _analysis, inventory = _inventory(
        packages=(package,),
        blueprints=(blueprint,),
        automations=(automation,),
    )
    assert inventory.discovered_files == (DiscoveredFile(package.path),)
    assert inventory.discovered_files[0].path is package.path
    assert inventory.automations == (automation,)
    assert inventory.blueprints == (blueprint,)


def test_inventory_does_not_modify_analysis() -> None:
    package = _package("lighting", "packages/lighting.yaml")
    automation = _automation(package, "lights", "Lights")
    label = _label("energy", "Energy")
    analysis = AnalysisModel(
        home_assistant_model=HomeAssistantModel(labels=(label,)),
        yaml_repository=YamlRepository(packages=(package,), automations=(automation,)),
    )
    repository = analysis.yaml_repository
    automations = repository.automations
    packages = repository.packages
    labels = analysis.home_assistant_model.labels
    relationships = analysis.relationship_repository
    inventory = HomeAssistantInventoryGenerator().generate(analysis)
    assert inventory.automations[0] is automation
    assert inventory.automations[0] is automations[0]
    assert analysis.yaml_repository is repository
    assert analysis.yaml_repository.automations is automations
    assert analysis.yaml_repository.packages is packages
    assert analysis.home_assistant_model.labels is labels
    assert analysis.relationship_repository is relationships


def test_inventory_model_is_frozen() -> None:
    inventory = HomeAssistantInventory()
    with pytest.raises(FrozenInstanceError):
        inventory.automations = ()  # type: ignore[misc]


def test_regression_boundaries_stay_unchanged() -> None:
    assert [field.name for field in fields(AnalysisModel)] == [
        "home_assistant_model",
        "yaml_repository",
        "relationship_repository",
    ]
    assert list(inspect.signature(InventoryReportGenerator.generate).parameters) == [
        "self",
        "model",
        "yaml_repository",
        "project_tree",
        "metadata",
    ]
    root = PACKAGE_SOURCE_ROOT / "reporting"
    names = ("home_assistant_inventory.py", "home_assistant_inventory_generator.py")
    forbidden = (
        "discover_project",
        "FilesystemWalker",
        "ProjectTree",
        "YamlLoader",
        "scanner_diagnostics",
        "rglob",
        "iterdir",
        "read_text",
        "Relationship",
        "ESPHome",
    )
    for name in names:
        source = (root / name).read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in source
    assert list(inspect.signature(HomeAssistantInventoryGenerator.generate).parameters) == [
        "self",
        "analysis_model",
    ]
