"""Validate duplicate Home Assistant identifiers across packages.

Produces immutable ``ValidationResult`` tuples only. Consumes already
parsed YAML domain data — no YAML loading, CLI coupling or reuse of
object-specific integrity checks from other validators.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Final

from ..automation.models import Automation
from ..helper.models import Helper
from ..packages.models import PackageStructure
from ..relationships.models import ObjectType
from ..script.models import Script
from ..yaml.repository import YamlRepository
from .models import (
    ValidationCollection,
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)

_HELPER_TYPES: Final[frozenset[str]] = frozenset(
    {
        "counter",
        "input_boolean",
        "input_button",
        "input_counter",
        "input_datetime",
        "input_number",
        "input_select",
        "input_text",
    }
)
_TEMPLATE_PLATFORMS: Final[frozenset[str]] = frozenset(
    {
        "binary_sensor",
        "number",
        "select",
        "sensor",
        "switch",
    }
)
_TEMPLATE_SECTION: Final[str] = "template"


class PackageValidator:
    """Stateless validator for project-wide duplicate identifiers.

    Accepts an already-populated ``YamlRepository``. Emits duplicate
    findings only; does not parse YAML or inspect object contents.
    """

    def validate(
        self,
        repository: YamlRepository,
    ) -> tuple[ValidationResult, ...]:
        """Return sorted duplicate findings for *repository*."""
        results: list[ValidationResult] = []
        results.extend(_duplicate_automations(repository.automations))
        results.extend(_duplicate_scripts(repository.scripts))
        results.extend(_duplicate_helpers(repository.helpers))
        results.extend(_duplicate_templates(repository.package_structures))
        return ValidationCollection(results=tuple(results)).results


def _duplicate_automations(
    automations: tuple[Automation, ...],
) -> tuple[ValidationResult, ...]:
    """Flag automation IDs that appear more than once."""
    return _findings(
        ObjectType.AUTOMATION,
        "automation ID",
        (
            (_object_id(automation.id), _path_location(automation.package.path))
            for automation in automations
        ),
    )


def _duplicate_scripts(
    scripts: tuple[Script, ...],
) -> tuple[ValidationResult, ...]:
    """Flag script IDs that appear more than once."""
    return _findings(
        ObjectType.SCRIPT,
        "script ID",
        (
            (_object_id(script.id), _path_location(script.package.path))
            for script in scripts
        ),
    )


def _duplicate_helpers(
    helpers: tuple[Helper, ...],
) -> tuple[ValidationResult, ...]:
    """Flag helper IDs that appear more than once per helper type."""
    return _findings(
        ObjectType.HELPER,
        "helper ID",
        (
            (f"{helper.type}.{helper.id}", _path_location(helper.package.path))
            for helper in helpers
            if helper.type in _HELPER_TYPES and helper.id != ""
        ),
    )


def _duplicate_templates(
    structures: tuple[PackageStructure, ...],
) -> tuple[ValidationResult, ...]:
    """Flag template entity IDs that appear more than once."""
    items: list[tuple[str, str]] = []
    for structure in structures:
        section = structure.get_section(_TEMPLATE_SECTION)
        if section is None:
            continue
        items.extend(_template_ids(section.data, structure.package.path))
    return _findings(ObjectType.TEMPLATE, "template entity ID", items)


def _template_ids(
    node: object,
    path: Path,
) -> tuple[tuple[str, str], ...]:
    """Collect template entity IDs from already-parsed section data."""
    found: list[tuple[str, str]] = []
    _collect_template_ids(node, path, found)
    return tuple(found)


def _collect_template_ids(
    node: object,
    path: Path,
    found: list[tuple[str, str]],
) -> None:
    """Walk mappings and lists for template platform identifiers."""
    if isinstance(node, Mapping):
        _collect_from_mapping(node, path, found)
        return
    if isinstance(node, list):
        for item in node:
            _collect_template_ids(item, path, found)


def _collect_from_mapping(
    mapping: Mapping[object, object],
    path: Path,
    found: list[tuple[str, str]],
) -> None:
    """Collect entity IDs from template platform keys in *mapping*."""
    for key, value in mapping.items():
        if isinstance(key, str) and key in _TEMPLATE_PLATFORMS:
            found.extend(_ids_from_platform(value, path))
            continue
        _collect_template_ids(value, path, found)


def _ids_from_platform(
    value: object,
    path: Path,
) -> tuple[tuple[str, str], ...]:
    """Return entity IDs declared on one template platform value."""
    location = _path_location(path)
    if isinstance(value, Mapping):
        entity_id = _template_entity_id(value)
        return ((entity_id, location),) if entity_id else ()
    if not isinstance(value, list):
        return ()
    return tuple(
        (entity_id, location)
        for item in value
        if isinstance(item, Mapping)
        for entity_id in (_template_entity_id(item),)
        if entity_id
    )


def _template_entity_id(mapping: Mapping[object, object]) -> str | None:
    """Return an explicit template entity_id, if present."""
    value = mapping.get("entity_id")
    if isinstance(value, str) and value != "":
        return value
    return None


def _findings(
    object_type: ObjectType,
    label: str,
    items: Iterable[tuple[str, str]],
) -> tuple[ValidationResult, ...]:
    """Build one duplicate finding per identifier that occurs more than once."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for object_id, location in items:
        if object_id == "":
            continue
        grouped[object_id].append(location)
    return tuple(
        ValidationResult(
            object_type=object_type,
            object_id=object_id,
            validation_type=ValidationType.DUPLICATE,
            severity=ValidationSeverity.ERROR,
            message=_duplicate_message(label, locations),
        )
        for object_id, locations in sorted(grouped.items())
        if len(locations) > 1
    )


def _duplicate_message(label: str, locations: Sequence[str]) -> str:
    """Return a duplicate message with file locations."""
    available = tuple(sorted(set(locations)))
    return f"Duplicate {label}. Locations: {', '.join(available)}."


def _object_id(value: str | None) -> str:
    """Return a non-empty identifier string, or an empty skip marker."""
    return value if value is not None else ""


def _path_location(path: Path) -> str:
    """Return a deterministic POSIX path string for findings."""
    return path.as_posix()
