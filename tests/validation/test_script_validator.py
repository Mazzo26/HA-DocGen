"""Unit tests for ScriptValidator."""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

from tools.ha_docgen.packages.models import Package
from tools.ha_docgen.registries.models import Entity
from tools.ha_docgen.relationships.models import (
    ObjectType,
    Relationship,
    RelationshipType,
)
from tools.ha_docgen.relationships.repository import RelationshipRepository
from tools.ha_docgen.script.models import Script
from tools.ha_docgen.validation import (
    ScriptValidator,
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)
from tools.ha_docgen.yaml.models import YamlDocument

_LIGHT_SERVICE = "light.turn_on"
_LIGHT_ENTITY = "light.kitchen"
_KNOWN_SERVICES = frozenset({_LIGHT_SERVICE, "script.turn_on"})


def _package() -> Package:
    path = Path("packages/test.yaml")
    return Package(
        name="test",
        path=path,
        document=YamlDocument(path=path, text="", data={}),
    )


def _entity(entity_id: str) -> Entity:
    return Entity(registry_id=entity_id, entity_id=entity_id, unique_id=entity_id)


def _action() -> dict[str, object]:
    return {
        "action": _LIGHT_SERVICE,
        "target": {"entity_id": _LIGHT_ENTITY},
    }


def _script(
    script_id: str = "example",
    *,
    alias: str | None = "Example",
    mode: str | None = "single",
    sequence: object | None = None,
    raw: dict[str, object] | None = None,
    include_sequence: bool = True,
) -> Script:
    if sequence is None:
        sequence = [_action()]
    mapping: dict[str, object] = {}
    if alias is not None:
        mapping["alias"] = alias
    if mode is not None:
        mapping["mode"] = mode
    if include_sequence:
        mapping["sequence"] = sequence
    if raw is not None:
        mapping.update(raw)
    return Script(
        package=_package(),
        id=script_id,
        alias=alias,
        mode=mode,
        sequence=sequence if include_sequence else (),
        raw=MappingProxyType(mapping),
    )


def _validate(
    scripts: tuple[Script, ...],
    *,
    repository: RelationshipRepository | None = None,
    entities: tuple[Entity, ...] | None = None,
    known_services: frozenset[str] = _KNOWN_SERVICES,
) -> tuple[ValidationResult, ...]:
    return ScriptValidator().validate(
        scripts,
        repository if repository is not None else RelationshipRepository(),
        entities if entities is not None else (_entity(_LIGHT_ENTITY),),
        known_services,
    )


def _messages(results: tuple[ValidationResult, ...]) -> list[str]:
    return [result.message for result in results]


def _finding(
    results: tuple[ValidationResult, ...],
    message: str,
) -> ValidationResult:
    return next(item for item in results if item.message == message)


def _assert_finding(
    finding: ValidationResult,
    *,
    message: str,
    severity: ValidationSeverity,
    validation_type: ValidationType,
    object_id: str,
) -> None:
    assert finding.message == message
    assert finding.severity == severity
    assert finding.validation_type == validation_type
    assert finding.object_type == ObjectType.SCRIPT
    assert finding.object_id == object_id


def test_valid_script_has_no_findings() -> None:
    results = _validate((_script(),))
    assert results == ()


def test_duplicate_script_ids() -> None:
    results = _validate((_script("dup"), _script("dup")))
    _assert_finding(
        _finding(results, "Duplicate script ID."),
        message="Duplicate script ID.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.DUPLICATE,
        object_id="dup",
    )


def test_missing_alias() -> None:
    results = _validate((_script(alias=None),))
    _assert_finding(
        _finding(results, "Script has no alias."),
        message="Script has no alias.",
        severity=ValidationSeverity.WARNING,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_empty_alias() -> None:
    results = _validate((_script(alias=""),))
    _assert_finding(
        _finding(results, "Script alias is empty."),
        message="Script alias is empty.",
        severity=ValidationSeverity.WARNING,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_missing_sequence() -> None:
    results = _validate((_script(include_sequence=False),))
    _assert_finding(
        _finding(results, "Script has no sequence."),
        message="Script has no sequence.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_empty_sequence() -> None:
    results = _validate((_script(sequence=[]),))
    _assert_finding(
        _finding(results, "Script sequence is empty."),
        message="Script sequence is empty.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_sequence_must_be_a_list() -> None:
    results = _validate((_script(sequence="delay"),))
    _assert_finding(
        _finding(results, "Script sequence must be a list."),
        message="Script sequence must be a list.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_invalid_top_level_keys() -> None:
    results = _validate((_script(raw={"not_a_key": True}),))
    _assert_finding(
        _finding(results, "Invalid top-level key: not_a_key."),
        message="Invalid top-level key: not_a_key.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_invalid_script_mode() -> None:
    results = _validate((_script(mode="burst"),))
    _assert_finding(
        _finding(results, "Invalid script mode."),
        message="Invalid script mode.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_queued_mode_without_max() -> None:
    results = _validate((_script(mode="queued"),))
    _assert_finding(
        _finding(results, "Queued mode without max."),
        message="Queued mode without max.",
        severity=ValidationSeverity.WARNING,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_queued_mode_with_max_is_valid() -> None:
    results = _validate((_script(mode="queued", raw={"max": 10}),))
    assert "Queued mode without max." not in _messages(results)


def test_max_smaller_than_one() -> None:
    results = _validate((_script(raw={"max": 0}),))
    _assert_finding(
        _finding(results, "Script max must be at least 1."),
        message="Script max must be at least 1.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_invalid_delay() -> None:
    results = _validate((_script(sequence=[{"delay": "not-a-delay"}]),))
    _assert_finding(
        _finding(results, "Invalid delay."),
        message="Invalid delay.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_valid_delay_formats() -> None:
    scripts = (
        _script("seconds", sequence=[{"delay": 5}]),
            _script("clock_short", sequence=[{"delay": "00:01"}]),
        _script("mapping", sequence=[{"delay": {"seconds": 2, "minutes": 1}}]),
        _script("template", sequence=[{"delay": "{{ delay }}"}]),
    )
    assert _validate(scripts) == ()


def test_unknown_service() -> None:
    results = _validate(
        (_script(sequence=[{"action": "not_a_real.service"}]),),
    )
    _assert_finding(
        _finding(results, "Unknown service: not_a_real.service."),
        message="Unknown service: not_a_real.service.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_unknown_entity() -> None:
    results = _validate(
        (
            _script(
                sequence=[
                    {
                        "action": _LIGHT_SERVICE,
                        "target": {"entity_id": "light.missing"},
                    },
                ],
            ),
        ),
    )
    _assert_finding(
        _finding(results, "Unknown entity: light.missing."),
        message="Unknown entity: light.missing.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_empty_catalogs_skip_unknown_checks() -> None:
    results = ScriptValidator().validate(
        (
            _script(
                sequence=[
                    {
                        "action": "not_a_real.service",
                        "target": {"entity_id": "light.missing"},
                    },
                ],
            ),
        ),
        RelationshipRepository(),
        (),
        frozenset(),
    )
    assert "Unknown service: not_a_real.service." not in _messages(results)
    assert "Unknown entity: light.missing." not in _messages(results)


def test_non_mapping_sequence_item() -> None:
    results = _validate((_script(sequence=["delay", None]),))
    finding = _finding(results, "Unsupported action type.")
    _assert_finding(
        finding,
        message="Unsupported action type.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.UNSUPPORTED,
        object_id="example",
    )


def test_invalid_choose_not_a_list() -> None:
    results = _validate((_script(sequence=[{"choose": {}, "default": []}]),))
    _assert_finding(
        _finding(results, "Choose must be a list."),
        message="Choose must be a list.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_invalid_choose_missing_conditions_and_sequence() -> None:
    results = _validate(
        (_script(sequence=[{"choose": [{}], "default": []}]),),
    )
    _assert_finding(
        _finding(results, "Choose option is missing conditions."),
        message="Choose option is missing conditions.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )
    _assert_finding(
        _finding(results, "Choose option is missing sequence."),
        message="Choose option is missing sequence.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_choose_missing_default_is_warning() -> None:
    results = _validate(
        (
            _script(
                sequence=[
                    {
                        "choose": [
                            {"conditions": [], "sequence": [_action()]},
                        ],
                    },
                ],
            ),
        ),
    )
    _assert_finding(
        _finding(results, "Choose has no default branch."),
        message="Choose has no default branch.",
        severity=ValidationSeverity.WARNING,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_invalid_repeat_not_a_mapping() -> None:
    results = _validate((_script(sequence=[{"repeat": []}]),))
    _assert_finding(
        _finding(results, "Invalid repeat structure."),
        message="Invalid repeat structure.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_invalid_repeat_missing_kind_and_sequence() -> None:
    results = _validate((_script(sequence=[{"repeat": {}}]),))
    _assert_finding(
        _finding(results, "Repeat is missing count, while, until or for_each."),
        message="Repeat is missing count, while, until or for_each.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )
    _assert_finding(
        _finding(results, "Repeat is missing sequence."),
        message="Repeat is missing sequence.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_valid_repeat_kinds() -> None:
    scripts = (
        _script("count", sequence=[{"repeat": {"count": 2, "sequence": [_action()]}}]),
        _script(
            "while",
            sequence=[{"repeat": {"while": [], "sequence": [_action()]}}],
        ),
        _script(
            "until",
            sequence=[{"repeat": {"until": [], "sequence": [_action()]}}],
        ),
        _script(
            "for_each",
            sequence=[{"repeat": {"for_each": ["a"], "sequence": [_action()]}}],
        ),
    )
    assert _validate(scripts) == ()


def test_recursive_scripts() -> None:
    script_a = _script("a", sequence=[{"action": "script.b"}])
    script_b = _script("b", sequence=[{"action": "script.a"}])
    results = _validate((script_a, script_b))
    findings = [
        item
        for item in results
        if item.message == "Recursive script call detected."
    ]
    assert {item.object_id for item in findings} == {"a", "b"}
    for finding in findings:
        _assert_finding(
            finding,
            message="Recursive script call detected.",
            severity=ValidationSeverity.ERROR,
            validation_type=ValidationType.INVALID_CONFIGURATION,
            object_id=finding.object_id,
        )


def test_self_recursive_script() -> None:
    results = _validate((_script("loop", sequence=[{"action": "script.loop"}]),))
    _assert_finding(
        _finding(results, "Recursive script call detected."),
        message="Recursive script call detected.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="loop",
    )


def test_recursive_scripts_via_turn_on_and_relationships() -> None:
    script_a = _script(
        "a",
        sequence=[
            {
                "service": "script.turn_on",
                "target": {"entity_id": "script.b"},
            },
        ],
    )
    script_b = _script("b", sequence=[{"action": "script.a"}])
    repository = RelationshipRepository(
        relationships=(
            Relationship(
                source_type=ObjectType.SCRIPT,
                source_id="a",
                target_type=ObjectType.SCRIPT,
                target_id="script.b",
                relationship_type=RelationshipType.REFERENCES,
            ),
        ),
    )
    results = _validate((script_a, script_b), repository=repository)
    _assert_finding(
        _finding(results, "Recursive script call detected."),
        message="Recursive script call detected.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="a",
    )


def test_unsupported_action() -> None:
    results = _validate((_script(sequence=[{"not_an_action": True}]),))
    _assert_finding(
        _finding(results, "Unsupported action type."),
        message="Unsupported action type.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.UNSUPPORTED,
        object_id="example",
    )


def test_results_are_validation_result_only() -> None:
    results = _validate((_script(alias=None), _script("dup"), _script("dup")))
    assert results
    assert all(isinstance(result, ValidationResult) for result in results)
    assert all(result.object_type == ObjectType.SCRIPT for result in results)
    _assert_finding(
        _finding(results, "Script has no alias."),
        message="Script has no alias.",
        severity=ValidationSeverity.WARNING,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )
    _assert_finding(
        _finding(results, "Duplicate script ID."),
        message="Duplicate script ID.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.DUPLICATE,
        object_id="dup",
    )


def test_template_max_is_valid() -> None:
    results = _validate((_script(raw={"max": "{{ states('input_number.max') }}"}),))
    assert "Script max must be at least 1." not in _messages(results)


def test_invalid_delay_boolean_and_list() -> None:
    results = _validate(
        (
            _script("bool_delay", sequence=[{"delay": True}]),
            _script("list_delay", sequence=[{"delay": [1]}]),
            _script("bad_clock", sequence=[{"delay": "00:xx"}]),
            _script("bad_key", sequence=[{"delay": {"weeks": 1, "foo": 1}}]),
            _script("bad_part", sequence=[{"delay": {"seconds": False}}]),
            _script("nested_part", sequence=[{"delay": {"seconds": [1]}}]),
        ),
    )
    assert _messages(results).count("Invalid delay.") == 6
    _assert_finding(
        next(
            item
            for item in results
            if item.message == "Invalid delay." and item.object_id == "bool_delay"
        ),
        message="Invalid delay.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="bool_delay",
    )


def test_delay_number_string_and_template_part() -> None:
    scripts = (
        _script("number_string", sequence=[{"delay": "5"}]),
        _script("part_template", sequence=[{"delay": {"minutes": "{{ n }}"}}]),
        _script("non_str_key", sequence=[{"delay": {1: 2}}]),
    )
    results = _validate(scripts)
    invalid = _finding(results, "Invalid delay.")
    _assert_finding(
        invalid,
        message="Invalid delay.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="non_str_key",
    )
    assert "number_string" not in {
        item.object_id for item in results if item.message == "Invalid delay."
    }
    assert "part_template" not in {
        item.object_id for item in results if item.message == "Invalid delay."
    }


def test_choose_option_not_mapping() -> None:
    results = _validate(
        (_script(sequence=[{"choose": ["bad"], "default": []}]),),
    )
    assert "Invalid choose structure." in _messages(results)
    _assert_finding(
        _finding(results, "Invalid choose structure."),
        message="Invalid choose structure.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_unknown_script_control_service() -> None:
    results = _validate(
        (
            _script(
                sequence=[
                    {
                        "service": "script.turn_on",
                        "target": {"entity_id": "script.example"},
                    },
                ],
            ),
        ),
        known_services=frozenset({_LIGHT_SERVICE}),
    )
    _assert_finding(
        _finding(results, "Unknown service: script.turn_on."),
        message="Unknown service: script.turn_on.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="example",
    )


def test_empty_script_id_skips_call_map() -> None:
    results = _validate((_script(""),))
    assert all(item.message != "Recursive script call detected." for item in results)


def test_entity_id_list_and_target_list() -> None:
    results = _validate(
        (
            _script(
                "bad_entity_type",
                sequence=[{"action": _LIGHT_SERVICE, "entity_id": 1}],
            ),
            _script(
                "list_ids",
                sequence=[
                    {
                        "action": _LIGHT_SERVICE,
                        "entity_id": [_LIGHT_ENTITY, "{{ skip }}", 1],
                    },
                ],
            ),
            _script(
                "target_list",
                sequence=[
                    {
                        "action": _LIGHT_SERVICE,
                        "target": [{"entity_id": _LIGHT_ENTITY}, "ignore"],
                    },
                ],
            ),
        ),
    )
    assert "Unknown entity: light.kitchen." not in _messages(results)


def test_invalid_max_non_numeric() -> None:
    results = _validate(
        (
            _script("abc", raw={"max": "abc"}),
            _script("flag", raw={"max": True}),
            _script("none", raw={"max": None}),
        ),
    )
    assert _messages(results).count("Script max must be at least 1.") == 3
    _assert_finding(
        _finding(results, "Script max must be at least 1."),
        message="Script max must be at least 1.",
        severity=ValidationSeverity.ERROR,
        validation_type=ValidationType.INVALID_CONFIGURATION,
        object_id="abc",
    )


def test_nested_if_and_parallel_actions() -> None:
    results = _validate(
        (
            _script(
                sequence=[
                    {
                        "if": [],
                        "then": [_action()],
                        "else": [{"delay": 1}],
                    },
                    {"parallel": [_action()]},
                ],
            ),
        ),
    )
    assert results == ()
