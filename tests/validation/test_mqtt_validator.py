"""Unit tests for MQTTValidator."""

from __future__ import annotations

from pathlib import Path

from ha_docgen.packages.models import Package, PackageStructure, Section
from ha_docgen.relationships.models import ObjectType
from ha_docgen.validation import (
    MQTTValidator,
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)
from ha_docgen.yaml.models import YamlDocument
from ha_docgen.yaml.repository import YamlRepository


def _package(name: str, path: str) -> Package:
    file_path = Path(path)
    return Package(
        name=name,
        path=file_path,
        document=YamlDocument(path=file_path, text="", data={}),
    )


def _structure(
    path: str,
    mqtt_data: object,
    name: str = "mqtt_package",
) -> PackageStructure:
    package = _package(name, path)
    return PackageStructure(
        package=package,
        sections=(Section(name="mqtt", data=mqtt_data),),
    )


def _validate(
    *structures: PackageStructure,
) -> tuple[ValidationResult, ...]:
    return MQTTValidator().validate(
        YamlRepository(package_structures=structures),
    )


def _assert_finding(
    finding: ValidationResult,
    *,
    message: str,
    object_id: str,
    validation_type: ValidationType,
    severity: ValidationSeverity = ValidationSeverity.ERROR,
) -> None:
    assert finding.message == message
    assert finding.object_id == object_id
    assert finding.object_type == ObjectType.MQTT_TOPIC
    assert finding.validation_type == validation_type
    assert finding.severity == severity


def test_empty_project_has_no_findings() -> None:
    assert MQTTValidator().validate(YamlRepository()) == ()


def test_package_without_mqtt_section_has_no_findings() -> None:
    package = _package("lights", "packages/lights.yaml")
    structure = PackageStructure(
        package=package,
        sections=(Section(name="script", data={}),),
    )
    assert _validate(structure) == ()


def test_valid_mqtt_configuration_has_no_findings() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "discovery": True,
                "discovery_prefix": "homeassistant",
                "sensor": [
                    {
                        "name": "Power",
                        "unique_id": "power",
                        "object_id": "power",
                        "state_topic": "house/power/state",
                        "availability_topic": "house/status",
                    },
                    {
                        "name": "Energy",
                        "unique_id": "energy",
                        "object_id": "energy",
                        "state_topic": "house/energy/state",
                        "availability": [{"topic": "house/status"}],
                    },
                ],
                "switch": [
                    {
                        "name": "Pump",
                        "unique_id": "pump",
                        "command_topic": "house/pump/set",
                        "state_topic": "house/pump/state",
                        "availability_topic": "house/status",
                    }
                ],
            },
        )
    )
    assert results == ()


def test_legacy_list_format_is_valid() -> None:
    results = _validate(
        _structure(
            "packages/legacy.yaml",
            [
                {
                    "platform": "sensor",
                    "unique_id": "legacy_sensor",
                    "state_topic": "legacy/state",
                }
            ],
        )
    )
    assert results == ()


def test_missing_state_topic() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {"sensor": [{"unique_id": "power", "name": "Power"}]},
        )
    )
    assert len(results) == 1
    _assert_finding(
        results[0],
        message="MQTT entity is missing required state_topic.",
        object_id="power",
        validation_type=ValidationType.INVALID_CONFIGURATION,
    )


def test_missing_command_topic() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "button": [
                    {
                        "unique_id": "press",
                        "name": "Press",
                    }
                ]
            },
        )
    )
    assert len(results) == 1
    _assert_finding(
        results[0],
        message="MQTT entity is missing required command_topic.",
        object_id="press",
        validation_type=ValidationType.INVALID_CONFIGURATION,
    )


def test_image_missing_required_topic() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {"image": [{"unique_id": "cam_still", "name": "Still"}]},
        )
    )
    assert len(results) == 1
    _assert_finding(
        results[0],
        message="MQTT entity is missing required url_topic.",
        object_id="cam_still",
        validation_type=ValidationType.INVALID_CONFIGURATION,
    )


def test_empty_topics() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "sensor": [
                    {
                        "unique_id": "blank",
                        "state_topic": "",
                    },
                    {
                        "unique_id": "spaces",
                        "state_topic": "   ",
                    },
                ]
            },
        )
    )
    assert len(results) == 4
    _assert_finding(
        results[0],
        message="MQTT entity is missing required state_topic.",
        object_id="blank",
        validation_type=ValidationType.INVALID_CONFIGURATION,
    )
    _assert_finding(
        results[1],
        message="MQTT state_topic is empty.",
        object_id="blank",
        validation_type=ValidationType.INVALID_CONFIGURATION,
    )
    _assert_finding(
        results[2],
        message="MQTT entity is missing required state_topic.",
        object_id="spaces",
        validation_type=ValidationType.INVALID_CONFIGURATION,
    )
    _assert_finding(
        results[3],
        message="MQTT state_topic is empty.",
        object_id="spaces",
        validation_type=ValidationType.INVALID_CONFIGURATION,
    )


def test_invalid_topic_format() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "sensor": [
                    {
                        "unique_id": "leading",
                        "state_topic": " house/state",
                    },
                    {
                        "unique_id": "trailing",
                        "state_topic": "house/state ",
                    },
                    {
                        "unique_id": "repeated",
                        "state_topic": "house//state",
                    },
                    {
                        "unique_id": "empty_segment",
                        "state_topic": "house/state/",
                    },
                ]
            },
        )
    )
    assert len(results) == 4
    _assert_finding(
        results[0],
        message="MQTT state_topic has invalid format.",
        object_id="empty_segment",
        validation_type=ValidationType.INVALID_CONFIGURATION,
    )
    _assert_finding(
        results[1],
        message="MQTT state_topic has invalid format.",
        object_id="leading",
        validation_type=ValidationType.INVALID_CONFIGURATION,
    )
    _assert_finding(
        results[2],
        message="MQTT state_topic has invalid format.",
        object_id="repeated",
        validation_type=ValidationType.INVALID_CONFIGURATION,
    )
    _assert_finding(
        results[3],
        message="MQTT state_topic has invalid format.",
        object_id="trailing",
        validation_type=ValidationType.INVALID_CONFIGURATION,
    )


def test_duplicate_topics() -> None:
    results = _validate(
        _structure("packages/one.yaml", {
            "sensor": [{"unique_id": "one", "state_topic": "shared/state"}]
        }, name="one"),
        _structure("packages/two.yaml", {
            "sensor": [{"unique_id": "two", "state_topic": "shared/state"}]
        }, name="two"),
    )
    assert len(results) == 1
    _assert_finding(
        results[0],
        message=(
            "Duplicate MQTT state_topic 'shared/state'. "
            "Object IDs: one, two. "
            "Locations: packages/one.yaml, packages/two.yaml."
        ),
        object_id="shared/state",
        validation_type=ValidationType.DUPLICATE,
    )


def test_shared_availability_topics_are_not_duplicates() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "sensor": [
                    {
                        "unique_id": "one",
                        "state_topic": "one/state",
                        "availability_topic": "bridge/status",
                    },
                    {
                        "unique_id": "two",
                        "state_topic": "two/state",
                        "availability": {"topic": "bridge/status"},
                    },
                ]
            },
        )
    )
    assert results == ()


def test_duplicate_unique_ids() -> None:
    results = _validate(
        _structure("packages/one.yaml", {
            "sensor": [{"unique_id": "power", "state_topic": "one/state"}]
        }, name="one"),
        _structure("packages/two.yaml", {
            "sensor": [{"unique_id": "power", "state_topic": "two/state"}]
        }, name="two"),
    )
    assert len(results) == 1
    _assert_finding(
        results[0],
        message=(
            "Duplicate MQTT unique_id. "
            "Locations: packages/one.yaml, packages/two.yaml."
        ),
        object_id="power",
        validation_type=ValidationType.DUPLICATE,
    )


def test_duplicate_discovery_identifiers() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "sensor": [
                    {
                        "unique_id": "one",
                        "object_id": "power",
                        "state_topic": "one/state",
                    },
                    {
                        "unique_id": "two",
                        "object_id": "power",
                        "state_topic": "two/state",
                    },
                ]
            },
        )
    )
    assert len(results) == 1
    _assert_finding(
        results[0],
        message="Duplicate MQTT discovery identifier. Locations: packages/mqtt.yaml.",
        object_id="power",
        validation_type=ValidationType.DUPLICATE,
    )


def test_duplicate_command_topics() -> None:
    results = _validate(
        _structure("packages/one.yaml", {
            "switch": [{"unique_id": "one", "command_topic": "shared/set"}]
        }, name="one"),
        _structure("packages/two.yaml", {
            "switch": [{"unique_id": "two", "command_topic": "shared/set"}]
        }, name="two"),
    )
    assert len(results) == 1
    _assert_finding(
        results[0],
        message=(
            "Duplicate MQTT command_topic 'shared/set'. "
            "Object IDs: one, two. "
            "Locations: packages/one.yaml, packages/two.yaml."
        ),
        object_id="shared/set",
        validation_type=ValidationType.DUPLICATE,
    )


def test_duplicate_command_topics_for_unnamed_entities() -> None:
    results = _validate(
        _structure("packages/one.yaml", {
            "switch": [{"command_topic": "shared/set"}]
        }, name="one"),
        _structure("packages/two.yaml", {
            "switch": [{"command_topic": "shared/set"}]
        }, name="two"),
    )
    assert len(results) == 1
    _assert_finding(
        results[0],
        message=(
            "Duplicate MQTT command_topic 'shared/set'. "
            "Object IDs: switch. "
            "Locations: packages/one.yaml, packages/two.yaml."
        ),
        object_id="shared/set",
        validation_type=ValidationType.DUPLICATE,
    )
    results = _validate(
        _structure("packages/one.yaml", {
            "sensor": [{"state_topic": "shared/state"}]
        }, name="one"),
        _structure("packages/two.yaml", {
            "sensor": [{"state_topic": "shared/state"}]
        }, name="two"),
    )
    assert len(results) == 1
    _assert_finding(
        results[0],
        message=(
            "Duplicate MQTT state_topic 'shared/state'. "
            "Object IDs: sensor. "
            "Locations: packages/one.yaml, packages/two.yaml."
        ),
        object_id="shared/state",
        validation_type=ValidationType.DUPLICATE,
    )


def test_optimistic_switch_without_state_topic_is_valid() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "switch": [
                    {
                        "unique_id": "pump",
                        "command_topic": "house/pump/set",
                    }
                ]
            },
        )
    )
    assert results == ()


def test_cover_with_only_state_topic_is_valid() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "cover": [
                    {
                        "unique_id": "gate",
                        "state_topic": "house/gate/state",
                    }
                ]
            },
        )
    )
    assert results == ()


def test_identical_command_and_state_topics_are_allowed() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "switch": [
                    {
                        "unique_id": "pump",
                        "command_topic": "house/pump",
                        "state_topic": "house/pump",
                    }
                ]
            },
        )
    )
    assert results == ()


def test_multiple_findings_on_one_entity() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "switch": [
                    {
                        "unique_id": "pump",
                        "command_topic": " house/pump",
                        "state_topic": "",
                    }
                ]
            },
        )
    )
    assert len(results) == 2
    _assert_finding(
        results[0],
        message="MQTT command_topic has invalid format.",
        object_id="pump",
        validation_type=ValidationType.INVALID_CONFIGURATION,
    )
    _assert_finding(
        results[1],
        message="MQTT state_topic is empty.",
        object_id="pump",
        validation_type=ValidationType.INVALID_CONFIGURATION,
    )


def test_template_topics_are_not_format_errors() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "sensor": [
                    {
                        "unique_id": "templated",
                        "state_topic": "{{ states('input_text.topic') }}",
                    }
                ]
            },
        )
    )
    assert results == ()


def test_single_platform_mapping_is_valid() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "sensor": {
                    "unique_id": "solo",
                    "state_topic": "solo/state",
                }
            },
        )
    )
    assert results == ()


def test_non_mapping_mqtt_section_is_ignored() -> None:
    assert _validate(_structure("packages/mqtt.yaml", "not-a-mapping")) == ()


def test_invalid_platform_payloads_are_ignored() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "sensor": "not-a-list",
                1: [{"unique_id": "bad_key", "state_topic": "x/state"}],
            },
        )
    )
    assert results == ()


def test_legacy_unknown_platform_is_ignored() -> None:
    results = _validate(
        _structure(
            "packages/legacy.yaml",
            [{"platform": "not_a_platform", "state_topic": "x/state"}, "skip"],
        )
    )
    assert results == ()


def test_availability_topic_shapes() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "sensor": [
                    {
                        "unique_id": "string_avail",
                        "state_topic": "one/state",
                        "availability": "bridge/status",
                    },
                    {
                        "unique_id": "list_string_avail",
                        "state_topic": "two/state",
                        "availability": ["bridge/status"],
                    },
                    {
                        "unique_id": "empty_avail_map",
                        "state_topic": "three/state",
                        "availability": {"payload_available": "online"},
                    },
                    {
                        "unique_id": "invalid_avail",
                        "state_topic": "four/state",
                        "availability": 3,
                    },
                    {
                        "unique_id": "avail_list_invalid",
                        "state_topic": "five/state",
                        "availability": [{"payload_available": "online"}, 1],
                    },
                ]
            },
        )
    )
    assert results == ()


def test_image_with_url_topic_is_valid() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {"image": [{"unique_id": "still", "url_topic": "cam/url"}]},
        )
    )
    assert results == ()


def test_non_string_topic_keys_are_ignored() -> None:
    results = _validate(
        _structure(
            "packages/mqtt.yaml",
            {
                "sensor": [
                    {
                        "unique_id": "odd",
                        "state_topic": "odd/state",
                        2: "ignored/topic",
                    }
                ]
            },
        )
    )
    assert results == ()
