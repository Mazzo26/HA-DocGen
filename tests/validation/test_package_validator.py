"""Unit tests for PackageValidator."""

from __future__ import annotations

from pathlib import Path

from tools.ha_docgen.automation.models import Automation
from tools.ha_docgen.helper.models import Helper
from tools.ha_docgen.packages.models import Package, PackageStructure, Section
from tools.ha_docgen.relationships.models import ObjectType
from tools.ha_docgen.script.models import Script
from tools.ha_docgen.validation import (
    PackageValidator,
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)
from tools.ha_docgen.yaml.models import YamlDocument
from tools.ha_docgen.yaml.repository import YamlRepository


def _package(name: str, path: str) -> Package:
    file_path = Path(path)
    return Package(
        name=name,
        path=file_path,
        document=YamlDocument(path=file_path, text="", data={}),
    )


def _automation(package: Package, automation_id: str | None) -> Automation:
    return Automation(package=package, id=automation_id, alias="Example")


def _script(package: Package, script_id: str | None) -> Script:
    return Script(package=package, id=script_id, alias="Example")


def _helper(package: Package, helper_type: str, helper_id: str) -> Helper:
    return Helper(package=package, type=helper_type, id=helper_id)


def _structure(package: Package, template_data: object) -> PackageStructure:
    return PackageStructure(
        package=package,
        sections=(Section(name="template", data=template_data),),
    )


def _validate(
    *,
    automations: tuple[Automation, ...] = (),
    scripts: tuple[Script, ...] = (),
    helpers: tuple[Helper, ...] = (),
    package_structures: tuple[PackageStructure, ...] = (),
) -> tuple[ValidationResult, ...]:
    return PackageValidator().validate(
        YamlRepository(
            automations=automations,
            scripts=scripts,
            helpers=helpers,
            package_structures=package_structures,
        )
    )


def _assert_duplicate(
    finding: ValidationResult,
    *,
    object_type: ObjectType,
    object_id: str,
    message: str,
) -> None:
    assert finding.object_type == object_type
    assert finding.object_id == object_id
    assert finding.validation_type == ValidationType.DUPLICATE
    assert finding.severity == ValidationSeverity.ERROR
    assert finding.message == message


def test_empty_project_has_no_findings() -> None:
    assert _validate() == ()


def test_project_without_duplicates_has_no_findings() -> None:
    lights = _package("lights", "packages/lights.yaml")
    climate = _package("climate", "packages/climate.yaml")
    results = _validate(
        automations=(
            _automation(lights, "lights_on"),
            _automation(climate, "climate_on"),
        ),
        scripts=(_script(lights, "reset_lights"), _script(climate, "reset_hvac")),
        helpers=(
            _helper(lights, "input_boolean", "guest_mode"),
            _helper(climate, "input_number", "target_temp"),
        ),
        package_structures=(
            _structure(
                lights,
                {"sensor": [{"entity_id": "sensor.lights_ok", "state": "{{ 1 }}"}]},
            ),
            _structure(
                climate,
                {
                    "binary_sensor": [
                        {"entity_id": "binary_sensor.climate_ok", "state": "{{ 1 }}"}
                    ]
                },
            ),
        ),
    )
    assert results == ()


def test_duplicate_automation_ids_across_packages() -> None:
    lights = _package("lights", "packages/lights.yaml")
    climate = _package("climate", "packages/climate.yaml")
    results = _validate(
        automations=(
            _automation(lights, "shared"),
            _automation(climate, "shared"),
        )
    )
    assert len(results) == 1
    _assert_duplicate(
        results[0],
        object_type=ObjectType.AUTOMATION,
        object_id="shared",
        message=(
            "Duplicate automation ID. Locations: "
            "packages/climate.yaml, packages/lights.yaml."
        ),
    )


def test_duplicate_automation_ids_inside_one_package() -> None:
    lights = _package("lights", "packages/lights.yaml")
    results = _validate(
        automations=(
            _automation(lights, "shared"),
            _automation(lights, "shared"),
        )
    )
    _assert_duplicate(
        results[0],
        object_type=ObjectType.AUTOMATION,
        object_id="shared",
        message="Duplicate automation ID. Locations: packages/lights.yaml.",
    )


def test_duplicate_script_ids_across_packages() -> None:
    lights = _package("lights", "packages/lights.yaml")
    climate = _package("climate", "packages/climate.yaml")
    results = _validate(
        scripts=(_script(lights, "reset"), _script(climate, "reset"))
    )
    _assert_duplicate(
        results[0],
        object_type=ObjectType.SCRIPT,
        object_id="reset",
        message=(
            "Duplicate script ID. Locations: "
            "packages/climate.yaml, packages/lights.yaml."
        ),
    )


def test_duplicate_script_ids_inside_one_package() -> None:
    lights = _package("lights", "packages/lights.yaml")
    results = _validate(
        scripts=(_script(lights, "reset"), _script(lights, "reset"))
    )
    _assert_duplicate(
        results[0],
        object_type=ObjectType.SCRIPT,
        object_id="reset",
        message="Duplicate script ID. Locations: packages/lights.yaml.",
    )


def test_duplicate_helper_ids_for_each_supported_type() -> None:
    first = _package("one", "packages/one.yaml")
    second = _package("two", "packages/two.yaml")
    helper_types = (
        "input_boolean",
        "input_number",
        "input_select",
        "input_text",
        "input_datetime",
        "input_button",
        "input_counter",
        "counter",
    )
    helpers = tuple(
        _helper(package, helper_type, "shared")
        for helper_type in helper_types
        for package in (first, second)
    )
    results = _validate(helpers=helpers)
    assert {finding.object_id for finding in results} == {
        f"{helper_type}.shared" for helper_type in helper_types
    }
    for finding in results:
        _assert_duplicate(
            finding,
            object_type=ObjectType.HELPER,
            object_id=finding.object_id,
            message=(
                "Duplicate helper ID. Locations: "
                "packages/one.yaml, packages/two.yaml."
            ),
        )


def test_helper_ids_may_repeat_across_different_types() -> None:
    package = _package("helpers", "packages/helpers.yaml")
    results = _validate(
        helpers=(
            _helper(package, "input_boolean", "shared"),
            _helper(package, "input_number", "shared"),
        )
    )
    assert results == ()


def test_unsupported_helper_types_are_ignored() -> None:
    first = _package("one", "packages/one.yaml")
    second = _package("two", "packages/two.yaml")
    results = _validate(
        helpers=(
            _helper(first, "timer", "laundry"),
            _helper(second, "timer", "laundry"),
        )
    )
    assert results == ()


def test_duplicate_template_entity_ids_across_packages() -> None:
    lights = _package("lights", "packages/lights.yaml")
    climate = _package("climate", "packages/climate.yaml")
    results = _validate(
        package_structures=(
            _structure(
                lights,
                {"sensor": [{"entity_id": "sensor.shared", "state": "{{ 1 }}"}]},
            ),
            _structure(
                climate,
                [
                    {
                        "sensor": [
                            {"entity_id": "sensor.shared", "state": "{{ 1 }}"},
                        ]
                    }
                ],
            ),
        )
    )
    _assert_duplicate(
        results[0],
        object_type=ObjectType.TEMPLATE,
        object_id="sensor.shared",
        message=(
            "Duplicate template entity ID. Locations: "
            "packages/climate.yaml, packages/lights.yaml."
        ),
    )


def test_duplicate_template_entity_ids_inside_one_package() -> None:
    lights = _package("lights", "packages/lights.yaml")
    results = _validate(
        package_structures=(
            _structure(
                lights,
                {
                    "sensor": [
                        {"entity_id": "sensor.dup", "state": "{{ 1 }}"},
                        {"entity_id": "sensor.dup", "state": "{{ 2 }}"},
                    ]
                },
            ),
        )
    )
    _assert_duplicate(
        results[0],
        object_type=ObjectType.TEMPLATE,
        object_id="sensor.dup",
        message="Duplicate template entity ID. Locations: packages/lights.yaml.",
    )


def test_template_platforms_are_all_checked() -> None:
    first = _package("one", "packages/one.yaml")
    second = _package("two", "packages/two.yaml")
    platforms = ("sensor", "binary_sensor", "number", "select", "switch")
    structures = tuple(
        _structure(
            package,
            {
                platform: [
                    {
                        "entity_id": f"{platform}.shared",
                        "state": "{{ 1 }}",
                    }
                ]
            },
        )
        for platform in platforms
        for package in (first, second)
    )
    results = _validate(package_structures=structures)
    assert {finding.object_id for finding in results} == {
        f"{platform}.shared" for platform in platforms
    }
    for finding in results:
        _assert_duplicate(
            finding,
            object_type=ObjectType.TEMPLATE,
            object_id=finding.object_id,
            message=(
                "Duplicate template entity ID. Locations: "
                "packages/one.yaml, packages/two.yaml."
            ),
        )


def test_template_mapping_form_and_missing_entity_id_are_skipped() -> None:
    package = _package("templates", "packages/templates.yaml")
    results = _validate(
        package_structures=(
            _structure(
                package,
                {
                    "sensor": {"name": "No id", "state": "{{ 1 }}"},
                    "binary_sensor": "ignored",
                },
            ),
        )
    )
    assert results == ()


def test_empty_and_missing_identifiers_are_not_duplicates() -> None:
    package = _package("core", "packages/core.yaml")
    results = _validate(
        automations=(_automation(package, None), _automation(package, "")),
        scripts=(_script(package, None), _script(package, "")),
        helpers=(_helper(package, "input_boolean", ""),),
    )
    assert results == ()


def test_multiple_duplicate_groups() -> None:
    lights = _package("lights", "packages/lights.yaml")
    climate = _package("climate", "packages/climate.yaml")
    results = _validate(
        automations=(
            _automation(lights, "alpha"),
            _automation(climate, "alpha"),
            _automation(lights, "beta"),
            _automation(climate, "beta"),
        ),
        scripts=(_script(lights, "gamma"), _script(climate, "gamma")),
    )
    assert [item.object_id for item in results] == ["alpha", "beta", "gamma"]
    assert all(item.validation_type == ValidationType.DUPLICATE for item in results)


def test_unique_objects_do_not_create_findings_with_duplicates() -> None:
    lights = _package("lights", "packages/lights.yaml")
    climate = _package("climate", "packages/climate.yaml")
    results = _validate(
        automations=(
            _automation(lights, "dup"),
            _automation(climate, "dup"),
            _automation(lights, "unique"),
        )
    )
    assert len(results) == 1
    assert results[0].object_id == "dup"


def test_structures_without_template_section_are_ignored() -> None:
    package = _package("core", "packages/core.yaml")
    structure = PackageStructure(
        package=package,
        sections=(Section(name="automation", data=[]),),
    )
    assert _validate(package_structures=(structure,)) == ()


def test_nested_template_platforms_are_collected() -> None:
    first = _package("one", "packages/one.yaml")
    second = _package("two", "packages/two.yaml")
    nested = {
        "trigger": [{"platform": "time"}],
        "sensor": [{"entity_id": "sensor.nested", "state": "{{ 1 }}"}],
    }
    results = _validate(
        package_structures=(
            _structure(first, [nested]),
            _structure(second, [nested]),
        )
    )
    _assert_duplicate(
        results[0],
        object_type=ObjectType.TEMPLATE,
        object_id="sensor.nested",
        message=(
            "Duplicate template entity ID. Locations: "
            "packages/one.yaml, packages/two.yaml."
        ),
    )