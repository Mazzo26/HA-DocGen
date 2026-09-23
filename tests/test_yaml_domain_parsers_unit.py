"""Unit tests for the public YAML domain parser APIs."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType

import pytest

from tools.ha_docgen.automation import AutomationParser
from tools.ha_docgen.blueprint import BlueprintParser
from tools.ha_docgen.dashboard import DashboardParser
from tools.ha_docgen.helper import HelperParser
from tools.ha_docgen.packages import Package, PackageParser, PackageStructure
from tools.ha_docgen.scene import SceneParser
from tools.ha_docgen.script import ScriptParser
from tools.ha_docgen.template import TemplateParser
from tools.ha_docgen.yaml import YamlDocument

pytestmark = pytest.mark.unit


def _structure(data: object) -> PackageStructure:
    """Build a parsed package structure with realistic mutable YAML data."""
    path = Path("packages") / "sample.yaml"
    document = YamlDocument(path=path, text="", data=data)
    package = Package(name="sample", path=path, document=document)
    return PackageParser().parse(package)


def test_automation_parser_supports_list_form_and_provenance() -> None:
    """List-form automations expose fields, aliases, raw data, and package."""
    structure = _structure(
        {
            "automation": [
                {
                    "id": "arrival",
                    "alias": "Arrival",
                    "description": "Welcome home",
                    "mode": "restart",
                    "trigger": [{"platform": "state"}],
                    "condition": [],
                    "action": [{"service": "light.turn_on"}],
                    "custom": True,
                }
            ]
        }
    )

    automation = AutomationParser().parse(structure)[0]

    assert automation.package is structure.package
    assert (automation.id, automation.alias, automation.mode) == (
        "arrival",
        "Arrival",
        "restart",
    )
    assert automation.triggers == [{"platform": "state"}]
    assert automation.actions == [{"service": "light.turn_on"}]
    assert automation.raw["custom"] is True
    assert isinstance(automation.raw, MappingProxyType)


def test_automation_parser_supports_named_mapping_without_inferred_id() -> None:
    """Mapping keys do not become automation identifiers."""
    structure = _structure({"automation": {"arrival": {"alias": "Arrival"}}})

    automation = AutomationParser().parse(structure)[0]

    assert automation.id is None
    assert automation.alias == "Arrival"


@pytest.mark.parametrize("data", [None, "invalid", 7, [None, "bad"]])
def test_automation_parser_ignores_malformed_section_items(data: object) -> None:
    """Unsupported automation shapes produce an empty immutable tuple."""
    result = AutomationParser().parse(_structure({"automation": data}))

    assert result == ()
    assert isinstance(result, tuple)


def test_script_parser_uses_mapping_key_and_freezes_mappings() -> None:
    """Scripts infer identity and expose immutable fields and raw mappings."""
    structure = _structure(
        {
            "script": {
                "wake_up": {
                    "alias": "Wake up",
                    "sequence": [{"service": "light.turn_on"}],
                    "fields": {"brightness": {"required": False}},
                    "variables": {"room": "bedroom"},
                }
            }
        }
    )

    script = ScriptParser().parse(structure)[0]

    assert script.package is structure.package
    assert script.id == "wake_up"
    assert script.sequence == [{"service": "light.turn_on"}]
    assert isinstance(script.fields, MappingProxyType)
    assert isinstance(script.variables, MappingProxyType)
    assert isinstance(script.raw, MappingProxyType)
    with pytest.raises(TypeError):
        script.raw["new"] = True  # type: ignore[index]


def test_script_parser_prefers_explicit_id_and_defaults_invalid_fields() -> None:
    """Explicit IDs win while malformed optional mappings become empty."""
    structure = _structure(
        {
            "script": {
                "mapping_key": {
                    "id": "explicit",
                    "alias": 12,
                    "fields": [],
                    "variables": "invalid",
                }
            }
        }
    )

    script = ScriptParser().parse(structure)[0]

    assert script.id == "explicit"
    assert script.alias is None
    assert script.sequence == ()
    assert dict(script.fields) == {}
    assert dict(script.variables) == {}


@pytest.mark.parametrize("section_data", [None, [], "invalid", {"bad": None}])
def test_script_parser_ignores_invalid_section_shapes(section_data: object) -> None:
    """Invalid script sections and entries do not create models."""
    assert ScriptParser().parse(_structure({"script": section_data})) == ()


def test_scene_parser_supports_list_and_mapping_forms() -> None:
    """Both scene shapes preserve provenance and freeze entity mappings."""
    list_structure = _structure(
        {"scene": [{"id": "evening", "name": "Evening", "entities": {"light.one": "on"}}]}
    )
    mapping_structure = _structure(
        {"scene": {"morning": {"name": "Morning", "entities": {"light.one": "off"}}}}
    )

    list_scene = SceneParser().parse(list_structure)[0]
    mapping_scene = SceneParser().parse(mapping_structure)[0]

    assert list_scene.id == "evening"
    assert mapping_scene.id == "morning"
    assert list_scene.package is list_structure.package
    assert mapping_scene.package is mapping_structure.package
    assert isinstance(list_scene.entities, MappingProxyType)
    assert isinstance(mapping_scene.raw, MappingProxyType)


@pytest.mark.parametrize("section_data", [None, "invalid", 4, [False]])
def test_scene_parser_ignores_malformed_section_items(section_data: object) -> None:
    """Unsupported scene shapes produce no scenes."""
    assert SceneParser().parse(_structure({"scene": section_data})) == ()


def test_helper_parser_filters_types_and_preserves_section_order() -> None:
    """Only supported helper domains are parsed in source section order."""
    structure = _structure(
        {
            "input_text": {"message": {"name": "Message", "icon": "mdi:text"}},
            "sensor": {"ignored": {"name": "Ignored"}},
            "input_boolean": {"enabled": {"name": "Enabled"}},
        }
    )

    helpers = HelperParser().parse(structure)

    assert tuple((helper.type, helper.id) for helper in helpers) == (
        ("input_boolean", "enabled"),
        ("input_text", "message"),
    )
    assert all(helper.package is structure.package for helper in helpers)
    assert all(isinstance(helper.raw, MappingProxyType) for helper in helpers)


@pytest.mark.parametrize("section_data", [None, [], "invalid", {"bad": False}])
def test_helper_parser_ignores_malformed_helper_data(section_data: object) -> None:
    """Invalid supported helper content creates no helpers."""
    assert HelperParser().parse(_structure({"input_boolean": section_data})) == ()


def test_dashboard_parser_reads_metadata_views_and_raw_mapping() -> None:
    """A valid dashboard retains path provenance and immutable mappings."""
    path = Path("dashboards/main.yaml")
    document = YamlDocument(
        path=path,
        text="",
        data={
            "id": "main",
            "title": "Main",
            "mode": "yaml",
            "views": [{"title": "Home"}, "invalid"],
            "custom": True,
        },
    )

    dashboard = DashboardParser().parse(document)

    assert (dashboard.id, dashboard.title, dashboard.mode) == ("main", "Main", "yaml")
    assert dashboard.path == path
    assert tuple(dict(view) for view in dashboard.views) == ({"title": "Home"},)
    assert isinstance(dashboard.views, tuple)
    assert isinstance(dashboard.views[0], MappingProxyType)
    assert isinstance(dashboard.raw, MappingProxyType)


@pytest.mark.parametrize("data", [None, [], "invalid", 3])
def test_dashboard_parser_defaults_non_mapping_documents(data: object) -> None:
    """Empty and malformed dashboard roots retain only source provenance."""
    path = Path("dashboards/invalid.yaml")

    dashboard = DashboardParser().parse(YamlDocument(path, "", data))

    assert dashboard.path == path
    assert dashboard.id is None
    assert dashboard.views == ()
    assert dict(dashboard.raw) == {}


def test_blueprint_parser_reads_metadata_input_and_raw_mapping() -> None:
    """Blueprint metadata and inputs are immutable and retain source path."""
    path = Path("blueprints/sample.yaml")
    document = YamlDocument(
        path=path,
        text="",
        data={
            "blueprint": {
                "name": "Motion light",
                "description": "Turns on a light",
                "domain": "automation",
                "source_url": "https://example.test/blueprint",
                "input": {"motion": {"selector": {"entity": {}}}},
            },
            "trigger": [],
        },
    )

    blueprint = BlueprintParser().parse(document)

    assert (blueprint.name, blueprint.domain) == ("Motion light", "automation")
    assert blueprint.path == path
    assert "motion" in blueprint.input
    assert isinstance(blueprint.input, MappingProxyType)
    assert isinstance(blueprint.raw, MappingProxyType)


@pytest.mark.parametrize(
    ("data", "raw"),
    [
        (None, {}),
        ([], {}),
        ({"blueprint": None, "trigger": []}, {"blueprint": None, "trigger": []}),
        ({"blueprint": []}, {"blueprint": []}),
    ],
)
def test_blueprint_parser_defaults_missing_or_malformed_metadata(
    data: object,
    raw: dict[str, object],
) -> None:
    """Missing blueprint metadata yields safe defaults without losing valid raw data."""
    path = Path("blueprints/invalid.yaml")

    blueprint = BlueprintParser().parse(YamlDocument(path, "", data))

    assert blueprint.path == path
    assert blueprint.name is None
    assert dict(blueprint.input) == {}
    assert dict(blueprint.raw) == raw


def test_template_parser_recurses_collects_and_reports_unknown_fields() -> None:
    """Known template fields are collected deterministically with provenance."""
    structure = _structure(
        {
            "template": [
                {
                    "sensor": [
                        {
                            "name": "Temperature",
                            "state": "{{ states('sensor.temp') }}",
                            "attribute_templates": {
                                "unit": "{{ 'C' }}",
                                "ignored": 5,
                            },
                            "custom_template": "{{ ignored }}",
                        }
                    ]
                }
            ]
        }
    )
    parser = TemplateParser()

    templates = parser.parse(structure)

    assert tuple(template.kind for template in templates) == (
        "name",
        "state",
        "attribute",
    )
    assert tuple(template.source for template in templates) == (
        "Temperature",
        "{{ states('sensor.temp') }}",
        "{{ 'C' }}",
    )
    assert all(template.package is structure.package for template in templates)
    assert all(template.path == structure.package.path for template in templates)
    assert all(isinstance(template.raw, MappingProxyType) for template in templates)
    assert parser.unknown_fields == frozenset({"custom_template"})


def test_template_parser_clears_diagnostics_and_handles_empty_structure() -> None:
    """Each parse is independent and empty input returns an immutable tuple."""
    parser = TemplateParser()
    parser.parse(_structure({"sensor": {"custom_template": "{{ value }}"}}))

    result = parser.parse(_structure({}))

    assert result == ()
    assert isinstance(result, tuple)
    assert parser.unknown_fields == frozenset()


def test_parsed_domain_model_is_frozen() -> None:
    """Domain parser results reject field reassignment."""
    automation = AutomationParser().parse(_structure({"automation": [{"id": "immutable"}]}))[0]

    with pytest.raises(FrozenInstanceError):
        automation.id = "changed"  # type: ignore[misc]
