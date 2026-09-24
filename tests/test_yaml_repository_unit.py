"""Unit tests for the public immutable YAML repository API."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType

import pytest

from ha_docgen.automation import AutomationParser
from ha_docgen.blueprint import BlueprintParser
from ha_docgen.dashboard import DashboardParser
from ha_docgen.helper import HelperParser
from ha_docgen.packages import Package, PackageParser
from ha_docgen.scene import SceneParser
from ha_docgen.script import ScriptParser
from ha_docgen.template import TemplateParser
from ha_docgen.yaml import YamlDocument, YamlRepository
from tests.support import (
    AutomationBuilder,
    PackageBuilder,
    YamlRepositoryBuilder,
)

pytestmark = pytest.mark.unit


def _parsed_repository() -> YamlRepository:
    """Build one repository covering every supported YAML domain."""
    path = Path("packages/all.yaml")
    data = {
        "automation": [{"id": "automation_one", "alias": "One"}],
        "script": {"script_one": {"alias": "One"}},
        "scene": [{"id": "scene_one", "name": "One"}],
        "input_boolean": {"helper_one": {"name": "One"}},
        "template": [{"sensor": [{"state": "{{ 1 }}"}]}],
    }
    package = Package("all", path, YamlDocument(path, "", data))
    structure = PackageParser().parse(package)
    dashboard_document = YamlDocument(
        Path("dashboards/main.yaml"),
        "",
        {"id": "dashboard_one", "views": []},
    )
    blueprint_document = YamlDocument(
        Path("blueprints/motion.yaml"),
        "",
        {"blueprint": {"name": "Motion", "domain": "automation"}},
    )
    return YamlRepository(
        packages=(package,),
        package_structures=(structure,),
        automations=AutomationParser().parse(structure),
        scripts=ScriptParser().parse(structure),
        scenes=SceneParser().parse(structure),
        helpers=HelperParser().parse(structure),
        dashboards=(DashboardParser().parse(dashboard_document),),
        blueprints=(BlueprintParser().parse(blueprint_document),),
        templates=TemplateParser().parse(structure),
    )


def test_empty_repository_has_immutable_empty_collections_and_missing_lookups() -> None:
    """The minimal repository returns tuples and None for every lookup."""
    repository = YamlRepository()

    assert all(
        isinstance(collection, tuple)
        for collection in (
            repository.packages,
            repository.package_structures,
            repository.automations,
            repository.scripts,
            repository.scenes,
            repository.helpers,
            repository.dashboards,
            repository.blueprints,
            repository.templates,
            repository.esphome_devices,
        )
    )
    assert repository.get_package("missing") is None
    assert repository.get_package_structure("missing") is None
    assert repository.get_automation("missing") is None
    assert repository.get_script("missing") is None
    assert repository.get_scene("missing") is None
    assert repository.get_helper("missing") is None
    assert repository.get_dashboard("missing") is None
    assert repository.get_blueprint("missing") is None
    assert repository.get_esphome_device("missing") is None


def test_repository_lookups_cover_every_indexed_domain() -> None:
    """Every stable identifier resolves to the original parsed object."""
    repository = _parsed_repository()

    assert repository.get_package("all") is repository.packages[0]
    assert repository.get_package_structure("all") is repository.package_structures[0]
    assert repository.get_automation("automation_one") is repository.automations[0]
    assert repository.get_script("script_one") is repository.scripts[0]
    assert repository.get_scene("scene_one") is repository.scenes[0]
    assert repository.get_helper("helper_one") is repository.helpers[0]
    assert repository.get_dashboard("dashboard_one") is repository.dashboards[0]
    blueprint_path = str(repository.blueprints[0].path)
    assert repository.get_blueprint(blueprint_path) is repository.blueprints[0]
    assert repository.esphome_devices == ()
    assert repository.get_esphome_device("missing") is None


def test_repository_freezes_supplied_collections_and_indexes() -> None:
    """Mutable inputs become tuples and internal lookup maps reject mutation."""
    package = PackageBuilder("sample").build()
    supplied = [package]

    repository = YamlRepository(packages=supplied)  # type: ignore[arg-type]
    supplied.append(PackageBuilder("later").build())

    assert repository.packages == (package,)
    assert isinstance(repository._package_index, MappingProxyType)
    with pytest.raises(TypeError):
        repository._package_index["new"] = package  # type: ignore[index]


def test_repository_is_frozen() -> None:
    """Repository fields cannot be reassigned after construction."""
    repository = YamlRepository()

    with pytest.raises(FrozenInstanceError):
        repository.packages = ()  # type: ignore[misc]


def test_models_without_stable_identifiers_are_retained_but_not_indexed() -> None:
    """Identifier-less objects stay in collections and cannot be looked up."""
    package = PackageBuilder().build()
    automation = AutomationBuilder().with_package(package).with_id(None).build()

    repository = YamlRepository(automations=(automation,))

    assert repository.automations == (automation,)
    assert repository.get_automation("") is None


def test_repository_builder_orders_supported_collections_deterministically() -> None:
    """The Module 11.1 builder removes caller insertion-order variance."""
    alpha = PackageBuilder("alpha").build()
    zulu = PackageBuilder("zulu").build()
    automation_z = AutomationBuilder().with_package(zulu).with_id("zulu").with_alias("Z").build()
    automation_a = AutomationBuilder().with_package(alpha).with_id("alpha").with_alias("A").build()

    repository = (
        YamlRepositoryBuilder()
        .add_package(zulu)
        .add_package(alpha)
        .add_automation(automation_z)
        .add_automation(automation_a)
        .build()
    )

    assert tuple(package.name for package in repository.packages) == ("alpha", "zulu")
    assert tuple(automation.id for automation in repository.automations) == (
        "alpha",
        "zulu",
    )


def test_duplicate_lookup_identifier_resolves_to_last_supplied_object() -> None:
    """Duplicate keys produce one deterministic index entry."""
    package = PackageBuilder().build()
    first = (
        AutomationBuilder().with_package(package).with_id("duplicate").with_alias("First").build()
    )
    second = (
        AutomationBuilder().with_package(package).with_id("duplicate").with_alias("Second").build()
    )

    repository = YamlRepository(automations=(first, second))

    assert repository.automations == (first, second)
    assert repository.get_automation("duplicate") is second
