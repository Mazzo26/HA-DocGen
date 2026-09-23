"""Validate Home Assistant scripts against explicit rules.

Produces immutable ``ValidationResult`` tuples only — no repository,
engine, reports, Markdown, filesystem or graph coupling.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from typing import Final

from ..registries.models import Entity
from ..relationships.models import ObjectType
from ..relationships.repository import RelationshipRepository
from ..script.models import Script
from .models import (
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)

_ALLOWED_MODES: Final[frozenset[str]] = frozenset(
    {"single", "restart", "queued", "parallel"},
)
_ALLOWED_TOP_LEVEL: Final[frozenset[str]] = frozenset(
    {
        "alias",
        "description",
        "fields",
        "icon",
        "id",
        "max",
        "max_exceeded",
        "mode",
        "sequence",
        "trace",
        "variables",
    },
)
_SUPPORTED_ACTION_KEYS: Final[frozenset[str]] = frozenset(
    {
        "action",
        "choose",
        "condition",
        "delay",
        "device_id",
        "error",
        "event",
        "if",
        "parallel",
        "repeat",
        "scene",
        "sequence",
        "service",
        "set_conversation_response",
        "stop",
        "variables",
        "wait",
        "wait_for_trigger",
        "wait_template",
    },
)
_DELAY_KEYS: Final[frozenset[str]] = frozenset(
    {"days", "hours", "milliseconds", "minutes", "seconds", "weeks"},
)
_REPEAT_KIND_KEYS: Final[frozenset[str]] = frozenset(
    {"count", "for_each", "until", "while"},
)
_SCRIPT_PREFIX: Final[str] = "script."
_SCRIPT_CONTROL_SERVICES: Final[frozenset[str]] = frozenset(
    {
        "script.reload",
        "script.toggle",
        "script.turn_off",
        "script.turn_on",
    },
)
_JINJA_MARKERS: Final[tuple[str, ...]] = ("{{", "{%")
_SERVICE_KEYS: Final[tuple[str, ...]] = ("service", "action")


class ScriptValidator:
    """Stateless validator for explicit script integrity checks.

    Accepts already-loaded scripts, a relationship repository, known
    entities and known service names. Emits findings only.
    """

    def validate(
        self,
        scripts: tuple[Script, ...],
        relationship_repository: RelationshipRepository,
        entities: tuple[Entity, ...] = (),
        known_services: frozenset[str] = frozenset(),
    ) -> tuple[ValidationResult, ...]:
        """Return sorted validation findings for *scripts*."""
        known_entity_ids = frozenset(entity.entity_id for entity in entities)
        script_ids = _defined_script_ids(scripts)
        services = frozenset(known_services)
        results: list[ValidationResult] = []
        results.extend(_validate_duplicates(scripts))
        results.extend(
            _validate_recursion(scripts, relationship_repository, script_ids),
        )
        for script in scripts:
            results.extend(
                _validate_script(
                    script,
                    known_entity_ids,
                    services,
                    script_ids,
                ),
            )
        return _sort_results(results)


def _object_id(script: Script) -> str:
    """Return the script identity string used in findings."""
    return script.id if script.id is not None else ""


def _defined_script_ids(scripts: tuple[Script, ...]) -> frozenset[str]:
    """Return non-empty script identifiers from *scripts*."""
    return frozenset(
        script_id
        for script_id in (_object_id(script) for script in scripts)
        if script_id != ""
    )


def _finding(
    object_id: str,
    validation_type: ValidationType,
    severity: ValidationSeverity,
    message: str,
) -> ValidationResult:
    """Build a script ``ValidationResult``."""
    return ValidationResult(
        object_type=ObjectType.SCRIPT,
        object_id=object_id,
        validation_type=validation_type,
        severity=severity,
        message=message,
    )


def _validate_script(
    script: Script,
    known_entity_ids: frozenset[str],
    known_services: frozenset[str],
    script_ids: frozenset[str],
) -> tuple[ValidationResult, ...]:
    """Run per-script structural and semantic checks."""
    results: list[ValidationResult] = []
    results.extend(_validate_alias(script))
    results.extend(_validate_mode(script))
    results.extend(_validate_max(script))
    results.extend(_validate_top_level_keys(script))
    results.extend(
        _validate_sequence(script, known_entity_ids, known_services, script_ids),
    )
    return tuple(results)


def _validate_alias(script: Script) -> tuple[ValidationResult, ...]:
    """Flag a missing or empty script alias."""
    object_id = _object_id(script)
    if script.alias is None:
        return (
            _finding(
                object_id,
                ValidationType.INVALID_CONFIGURATION,
                ValidationSeverity.WARNING,
                "Script has no alias.",
            ),
        )
    if script.alias == "":
        return (
            _finding(
                object_id,
                ValidationType.INVALID_CONFIGURATION,
                ValidationSeverity.WARNING,
                "Script alias is empty.",
            ),
        )
    return ()


def _validate_mode(script: Script) -> tuple[ValidationResult, ...]:
    """Flag a script mode that Home Assistant does not allow."""
    if script.mode is None or script.mode in _ALLOWED_MODES:
        return ()
    return (
        _finding(
            _object_id(script),
            ValidationType.INVALID_CONFIGURATION,
            ValidationSeverity.ERROR,
            "Invalid script mode.",
        ),
    )


def _validate_max(script: Script) -> tuple[ValidationResult, ...]:
    """Flag queued scripts without max, and max values below 1."""
    object_id = _object_id(script)
    if "max" not in script.raw:
        if script.mode != "queued":
            return ()
        return (
            _finding(
                object_id,
                ValidationType.INVALID_CONFIGURATION,
                ValidationSeverity.WARNING,
                "Queued mode without max.",
            ),
        )
    max_value = script.raw.get("max")
    if isinstance(max_value, str) and _is_template(max_value):
        return ()
    number = _as_number(max_value)
    if number is not None and number >= 1:
        return ()
    return (
        _finding(
            object_id,
            ValidationType.INVALID_CONFIGURATION,
            ValidationSeverity.ERROR,
            "Script max must be at least 1.",
        ),
    )


def _validate_top_level_keys(script: Script) -> tuple[ValidationResult, ...]:
    """Flag YAML keys that are not valid on a script mapping."""
    object_id = _object_id(script)
    invalid = sorted(
        str(key)
        for key in script.raw
        if not isinstance(key, str) or key not in _ALLOWED_TOP_LEVEL
    )
    return tuple(
        _finding(
            object_id,
            ValidationType.INVALID_CONFIGURATION,
            ValidationSeverity.ERROR,
            f"Invalid top-level key: {key}.",
        )
        for key in invalid
    )


def _validate_duplicates(
    scripts: tuple[Script, ...],
) -> tuple[ValidationResult, ...]:
    """Flag script IDs that appear more than once in *scripts*."""
    counts = Counter(_object_id(script) for script in scripts)
    return tuple(
        _finding(
            script_id,
            ValidationType.DUPLICATE,
            ValidationSeverity.ERROR,
            "Duplicate script ID.",
        )
        for script_id, count in counts.items()
        if count > 1
    )


def _validate_sequence(
    script: Script,
    known_entity_ids: frozenset[str],
    known_services: frozenset[str],
    script_ids: frozenset[str],
) -> tuple[ValidationResult, ...]:
    """Validate sequence presence, type, contents and nested actions."""
    structure_error = _sequence_structure_error(script)
    if structure_error is not None:
        return (structure_error,)
    sequence = script.sequence
    if not isinstance(sequence, list):
        return (
            _finding(
                _object_id(script),
                ValidationType.INVALID_CONFIGURATION,
                ValidationSeverity.ERROR,
                "Script sequence must be a list.",
            ),
        )
    return _validate_actions(
        sequence,
        _object_id(script),
        known_entity_ids,
        known_services,
        script_ids,
    )


def _sequence_structure_error(script: Script) -> ValidationResult | None:
    """Return a structure finding when sequence is missing, empty or not a list."""
    object_id = _object_id(script)
    if "sequence" not in script.raw:
        message = "Script has no sequence."
    elif not isinstance(script.sequence, list):
        return None
    elif len(script.sequence) == 0:
        message = "Script sequence is empty."
    else:
        return None
    return _finding(
        object_id,
        ValidationType.INVALID_CONFIGURATION,
        ValidationSeverity.ERROR,
        message,
    )


def _validate_actions(
    sequence: list[object],
    object_id: str,
    known_entity_ids: frozenset[str],
    known_services: frozenset[str],
    script_ids: frozenset[str],
) -> tuple[ValidationResult, ...]:
    """Validate every action mapping reachable from *sequence*."""
    results: list[ValidationResult] = []
    results.extend(_validate_non_mapping_items(sequence, object_id))
    for action in _iter_action_mappings(sequence):
        results.extend(_validate_action_type(action, object_id))
        results.extend(_validate_delay(action, object_id))
        results.extend(_validate_choose(action, object_id))
        results.extend(_validate_repeat(action, object_id))
        results.extend(
            _validate_service(action, object_id, known_services, script_ids),
        )
        results.extend(
            _validate_entities(action, object_id, known_entity_ids, script_ids),
        )
    return tuple(results)


def _validate_non_mapping_items(
    sequence: object,
    object_id: str,
) -> tuple[ValidationResult, ...]:
    """Flag sequence items that are not action mappings."""
    if not isinstance(sequence, list):
        return ()
    results: list[ValidationResult] = []
    for item in sequence:
        if isinstance(item, Mapping):
            for child in _child_sequences(item):
                results.extend(_validate_non_mapping_items(child, object_id))
            continue
        results.append(
            _finding(
                object_id,
                ValidationType.UNSUPPORTED,
                ValidationSeverity.ERROR,
                "Unsupported action type.",
            ),
        )
    return tuple(results)


def _validate_action_type(
    action: Mapping[object, object],
    object_id: str,
) -> tuple[ValidationResult, ...]:
    """Flag action mappings that use no supported action key."""
    if _is_supported_action(action):
        return ()
    return (
        _finding(
            object_id,
            ValidationType.UNSUPPORTED,
            ValidationSeverity.ERROR,
            "Unsupported action type.",
        ),
    )


def _is_supported_action(action: Mapping[object, object]) -> bool:
    """Return True when *action* declares a known action kind."""
    return any(
        isinstance(key, str) and key in _SUPPORTED_ACTION_KEYS for key in action
    )


def _validate_delay(
    action: Mapping[object, object],
    object_id: str,
) -> tuple[ValidationResult, ...]:
    """Flag delay values that Home Assistant does not accept."""
    if "delay" not in action:
        return ()
    if _is_valid_delay(action.get("delay")):
        return ()
    return (
        _finding(
            object_id,
            ValidationType.INVALID_CONFIGURATION,
            ValidationSeverity.ERROR,
            "Invalid delay.",
        ),
    )


def _is_valid_delay(value: object) -> bool:
    """Return True when *value* is a Home Assistant delay format."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value >= 0
    if isinstance(value, str):
        return _is_valid_delay_string(value)
    if isinstance(value, Mapping):
        return _is_valid_delay_mapping(value)
    return False


def _is_valid_delay_string(value: str) -> bool:
    """Return True when *value* is a template, number or HH:MM[:SS]."""
    if _is_template(value):
        return True
    stripped = value.strip()
    if _is_non_negative_number_string(stripped):
        return True
    parts = stripped.split(":")
    if len(parts) not in {2, 3}:
        return False
    return all(_is_non_negative_number_string(part) for part in parts)


def _is_valid_delay_mapping(value: Mapping[object, object]) -> bool:
    """Return True when *value* is a delay mapping with known keys."""
    if any(key not in _DELAY_KEYS for key in value if isinstance(key, str)):
        return False
    if any(not isinstance(key, str) for key in value):
        return False
    return all(_is_valid_delay_part(part) for part in value.values())


def _is_valid_delay_part(value: object) -> bool:
    """Return True when *value* is a numeric or template delay field."""
    if isinstance(value, str):
        return _is_template(value) or _is_non_negative_number_string(value)
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value >= 0
    return False


def _validate_choose(
    action: Mapping[object, object],
    object_id: str,
) -> tuple[ValidationResult, ...]:
    """Flag invalid choose structure and a missing default branch."""
    if "choose" not in action:
        return ()
    results: list[ValidationResult] = []
    choose = action.get("choose")
    if not isinstance(choose, list):
        results.append(
            _finding(
                object_id,
                ValidationType.INVALID_CONFIGURATION,
                ValidationSeverity.ERROR,
                "Choose must be a list.",
            ),
        )
    else:
        results.extend(_validate_choose_options(choose, object_id))
    if "default" not in action:
        results.append(
            _finding(
                object_id,
                ValidationType.INVALID_CONFIGURATION,
                ValidationSeverity.WARNING,
                "Choose has no default branch.",
            ),
        )
    return tuple(results)


def _validate_choose_options(
    choose: list[object],
    object_id: str,
) -> tuple[ValidationResult, ...]:
    """Flag choose options that lack conditions or sequence."""
    results: list[ValidationResult] = []
    for option in choose:
        if not isinstance(option, Mapping):
            results.append(
                _finding(
                    object_id,
                    ValidationType.INVALID_CONFIGURATION,
                    ValidationSeverity.ERROR,
                    "Invalid choose structure.",
                ),
            )
            continue
        results.extend(_validate_choose_option(option, object_id))
    return tuple(results)


def _validate_choose_option(
    option: Mapping[object, object],
    object_id: str,
) -> tuple[ValidationResult, ...]:
    """Flag a choose option missing conditions or sequence."""
    results: list[ValidationResult] = []
    if "conditions" not in option and "condition" not in option:
        results.append(
            _finding(
                object_id,
                ValidationType.INVALID_CONFIGURATION,
                ValidationSeverity.ERROR,
                "Choose option is missing conditions.",
            ),
        )
    if "sequence" not in option:
        results.append(
            _finding(
                object_id,
                ValidationType.INVALID_CONFIGURATION,
                ValidationSeverity.ERROR,
                "Choose option is missing sequence.",
            ),
        )
    return tuple(results)


def _validate_repeat(
    action: Mapping[object, object],
    object_id: str,
) -> tuple[ValidationResult, ...]:
    """Flag repeat actions that lack a kind or a sequence."""
    if "repeat" not in action:
        return ()
    repeat = action.get("repeat")
    if not isinstance(repeat, Mapping):
        return (
            _finding(
                object_id,
                ValidationType.INVALID_CONFIGURATION,
                ValidationSeverity.ERROR,
                "Invalid repeat structure.",
            ),
        )
    return _validate_repeat_mapping(repeat, object_id)


def _validate_repeat_mapping(
    repeat: Mapping[object, object],
    object_id: str,
) -> tuple[ValidationResult, ...]:
    """Flag missing repeat kind keys and missing repeat sequence."""
    results: list[ValidationResult] = []
    if not any(key in repeat for key in _REPEAT_KIND_KEYS):
        results.append(
            _finding(
                object_id,
                ValidationType.INVALID_CONFIGURATION,
                ValidationSeverity.ERROR,
                "Repeat is missing count, while, until or for_each.",
            ),
        )
    if "sequence" not in repeat:
        results.append(
            _finding(
                object_id,
                ValidationType.INVALID_CONFIGURATION,
                ValidationSeverity.ERROR,
                "Repeat is missing sequence.",
            ),
        )
    return tuple(results)


def _validate_service(
    action: Mapping[object, object],
    object_id: str,
    known_services: frozenset[str],
    script_ids: frozenset[str],
) -> tuple[ValidationResult, ...]:
    """Flag explicit service/action names that are not known."""
    if not known_services:
        return ()
    name = _explicit_service_name(action)
    if name is None or _is_known_service(name, known_services, script_ids):
        return ()
    return (
        _finding(
            object_id,
            ValidationType.INVALID_CONFIGURATION,
            ValidationSeverity.ERROR,
            f"Unknown service: {name}.",
        ),
    )


def _is_known_service(
    name: str,
    known_services: frozenset[str],
    script_ids: frozenset[str],
) -> bool:
    """Return True when *name* is a known service or local script."""
    if name in known_services:
        return True
    if name in _SCRIPT_CONTROL_SERVICES:
        return False
    if name.startswith(_SCRIPT_PREFIX):
        return name.removeprefix(_SCRIPT_PREFIX) in script_ids
    return False


def _validate_entities(
    action: Mapping[object, object],
    object_id: str,
    known_entity_ids: frozenset[str],
    script_ids: frozenset[str],
) -> tuple[ValidationResult, ...]:
    """Flag explicit entity ids that are not known."""
    if not known_entity_ids:
        return ()
    return tuple(
        _finding(
            object_id,
            ValidationType.INVALID_CONFIGURATION,
            ValidationSeverity.ERROR,
            f"Unknown entity: {entity_id}.",
        )
        for entity_id in _action_entity_ids(action)
        if not _is_known_entity(entity_id, known_entity_ids, script_ids)
    )


def _is_known_entity(
    entity_id: str,
    known_entity_ids: frozenset[str],
    script_ids: frozenset[str],
) -> bool:
    """Return True when *entity_id* exists as entity or local script."""
    if entity_id in known_entity_ids:
        return True
    if entity_id.startswith(_SCRIPT_PREFIX):
        return entity_id.removeprefix(_SCRIPT_PREFIX) in script_ids
    return False


def _validate_recursion(
    scripts: tuple[Script, ...],
    relationship_repository: RelationshipRepository,
    script_ids: frozenset[str],
) -> tuple[ValidationResult, ...]:
    """Flag scripts that participate in a recursive call cycle."""
    call_map = _script_call_map(scripts, relationship_repository)
    cyclic: set[str] = set()
    done: set[str] = set()
    for script_id in sorted(script_ids):
        _find_cycles(script_id, call_map, [], cyclic, done)
    return tuple(
        _finding(
            script_id,
            ValidationType.INVALID_CONFIGURATION,
            ValidationSeverity.ERROR,
            "Recursive script call detected.",
        )
        for script_id in sorted(cyclic)
    )


def _script_call_map(
    scripts: tuple[Script, ...],
    relationship_repository: RelationshipRepository,
) -> dict[str, set[str]]:
    """Build script-id → callee-id edges from YAML and relationships."""
    call_map: dict[str, set[str]] = {
        _object_id(script): set() for script in scripts if _object_id(script)
    }
    for script in scripts:
        object_id = _object_id(script)
        if object_id == "":
            continue
        call_map[object_id].update(_callees_from_script(script))
        call_map[object_id].update(
            _callees_from_relationships(object_id, relationship_repository),
        )
    return call_map


def _callees_from_script(script: Script) -> set[str]:
    """Collect script ids invoked from *script* sequence actions."""
    sequence = script.sequence
    if not isinstance(sequence, list):
        return set()
    callees: set[str] = set()
    for action in _iter_action_mappings(sequence):
        callees.update(_callees_from_action(action))
    return callees


def _callees_from_action(action: Mapping[object, object]) -> set[str]:
    """Collect script ids invoked by one action mapping."""
    name = _explicit_service_name(action)
    if name is None:
        return set()
    if name in _SCRIPT_CONTROL_SERVICES:
        return {
            _normalize_script_id(entity_id)
            for entity_id in _action_entity_ids(action)
            if entity_id.startswith(_SCRIPT_PREFIX)
        }
    if name.startswith(_SCRIPT_PREFIX):
        return {_normalize_script_id(name)}
    return set()


def _callees_from_relationships(
    object_id: str,
    relationship_repository: RelationshipRepository,
) -> set[str]:
    """Collect script ids from SCRIPT REFERENCES edges."""
    return {
        _normalize_script_id(relationship.target_id)
        for relationship in relationship_repository.by_source(
            ObjectType.SCRIPT,
            object_id,
        )
        if relationship.target_type == ObjectType.SCRIPT
        and relationship.target_id != ""
    }


def _find_cycles(
    node: str,
    graph: Mapping[str, set[str]],
    path: list[str],
    cyclic: set[str],
    done: set[str],
) -> None:
    """Record nodes that participate in a directed cycle."""
    if node in path:
        cyclic.update(path[path.index(node) :])
        return
    if node in done:
        return
    path.append(node)
    for callee in sorted(graph.get(node, ())):
        _find_cycles(callee, graph, path, cyclic, done)
    path.pop()
    done.add(node)


def _iter_action_mappings(sequence: list[object]) -> tuple[Mapping[object, object], ...]:
    """Return every action mapping nested under *sequence*."""
    found: list[Mapping[object, object]] = []
    _collect_action_mappings(sequence, found)
    return tuple(found)


def _collect_action_mappings(
    sequence: object,
    found: list[Mapping[object, object]],
) -> None:
    """Append action mappings from *sequence* into *found*."""
    if not isinstance(sequence, list):
        return
    for item in sequence:
        if isinstance(item, Mapping):
            found.append(item)
            for child in _child_sequences(item):
                _collect_action_mappings(child, found)


def _child_sequences(action: Mapping[object, object]) -> tuple[object, ...]:
    """Return nested sequences under choose, repeat, if and wrappers."""
    children: list[object] = []
    children.extend(_choose_sequences(action))
    children.extend(_repeat_sequences(action))
    children.append(action.get("default"))
    children.append(action.get("then"))
    children.append(action.get("else"))
    children.append(action.get("parallel"))
    if "choose" not in action and "repeat" not in action:
        children.append(action.get("sequence"))
    return tuple(children)


def _choose_sequences(action: Mapping[object, object]) -> tuple[object, ...]:
    """Return sequences declared on choose options."""
    choose = action.get("choose")
    if not isinstance(choose, list):
        return ()
    return tuple(
        option.get("sequence")
        for option in choose
        if isinstance(option, Mapping)
    )


def _repeat_sequences(action: Mapping[object, object]) -> tuple[object, ...]:
    """Return the sequence declared on a repeat mapping."""
    repeat = action.get("repeat")
    if not isinstance(repeat, Mapping):
        return ()
    return (repeat.get("sequence"),)


def _explicit_service_name(action: Mapping[object, object]) -> str | None:
    """Return an explicit service/action string, or None."""
    for key in _SERVICE_KEYS:
        value = action.get(key)
        if isinstance(value, str) and not _is_template(value):
            return value
    return None


def _action_entity_ids(action: Mapping[object, object]) -> tuple[str, ...]:
    """Collect explicit entity ids from *action* and its target."""
    ids = list(_explicit_id_values(action.get("entity_id")))
    target = action.get("target")
    if isinstance(target, Mapping):
        ids.extend(_explicit_id_values(target.get("entity_id")))
        return tuple(ids)
    if _is_sequence(target):
        for item in target:
            if isinstance(item, Mapping):
                ids.extend(_explicit_id_values(item.get("entity_id")))
    return tuple(ids)


def _explicit_id_values(value: object) -> tuple[str, ...]:
    """Return explicit non-template id strings from a scalar or list."""
    if isinstance(value, str):
        return () if _is_template(value) else (value,)
    if _is_sequence(value):
        return tuple(
            item
            for item in value
            if isinstance(item, str) and not _is_template(item)
        )
    return ()


def _normalize_script_id(value: str) -> str:
    """Strip the ``script.`` domain prefix when present."""
    return value.removeprefix(_SCRIPT_PREFIX)


def _is_template(value: str) -> bool:
    """Return True when *value* contains Jinja markers."""
    return any(marker in value for marker in _JINJA_MARKERS)


def _is_sequence(node: object) -> bool:
    """Return True for list-like YAML nodes (not str/bytes/Mapping)."""
    return isinstance(node, Sequence) and not isinstance(
        node,
        (str, bytes, bytearray, Mapping),
    )


def _as_number(value: object) -> float | None:
    """Return *value* as float when it is a finite number."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and not _is_template(value):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _is_non_negative_number_string(value: str) -> bool:
    """Return True when *value* parses as a number >= 0."""
    try:
        return float(value) >= 0
    except ValueError:
        return False


def _result_sort_key(
    result: ValidationResult,
) -> tuple[
    ObjectType,
    str,
    ValidationType,
    ValidationSeverity,
    str,
]:
    """Deterministic sort key matching validation model ordering."""
    return (
        result.object_type,
        result.object_id,
        result.validation_type,
        result.severity,
        result.message,
    )


def _sort_results(
    results: Iterable[ValidationResult],
) -> tuple[ValidationResult, ...]:
    """Deduplicate and return a deterministically sorted immutable tuple."""
    return tuple(sorted(set(results), key=_result_sort_key))
