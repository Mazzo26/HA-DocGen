"""Build a Document for exactly one Home Assistant automation.

Transforms one Automation and an explicit Relationship tuple into an
immutable ``Document`` tree. Produces document models only — no
Markdown, filesystem, repository, graph or Home Assistant aggregate
coupling.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..automation.models import Automation
from ..relationships.models import Relationship
from .models import BulletList, Document, Paragraph, Section

_TRIGGER_TYPE_KEYS: tuple[str, ...] = ("trigger", "platform")
_CONDITION_TYPE_KEYS: tuple[str, ...] = ("condition",)
_ACTION_NAME_KEYS: tuple[str, ...] = ("action", "service")
_RAW_TRIGGER_KEYS: tuple[str, ...] = ("triggers", "trigger")
_RAW_CONDITION_KEYS: tuple[str, ...] = ("conditions", "condition")
_RAW_ACTION_KEYS: tuple[str, ...] = ("actions", "action")


class AutomationDocumentGenerator:
    """Generate a Document for one Automation.

    Fully stateless: no instance state, no caching, no filesystem and
    no side effects. Callers supply the Automation and already-resolved
    Relationship objects.
    """

    def generate(
        self,
        automation: Automation,
        relationships: tuple[Relationship, ...],
    ) -> Document:
        """Return a Document describing *automation* and *relationships*."""
        return Document(
            title=_title(automation),
            sections=(
                _build_overview(automation),
                _build_triggers(automation),
                _build_conditions(automation),
                _build_actions(automation),
                _build_relationships(relationships),
            ),
        )


def _title(automation: Automation) -> str:
    """Return ``Automation: {alias}`` or ``Automation: {id}``."""
    label = automation.alias if automation.alias is not None else automation.id
    return f"Automation: {label}"


def _build_overview(automation: Automation) -> Section:
    """Build Overview from present first-class Automation fields."""
    lines: list[str] = []
    _append_if_present(lines, "id", automation.id)
    _append_if_present(lines, "alias", automation.alias)
    _append_if_present(lines, "mode", automation.mode)
    _append_if_present(lines, "description", automation.description)
    return Section(heading="Overview", content=(Paragraph("\n".join(lines)),))


def _build_triggers(automation: Automation) -> Section:
    """Build Triggers from explicit trigger types in ``Automation.raw``."""
    items = _explicit_type_items(
        _raw_list(automation.raw, _RAW_TRIGGER_KEYS),
        _TRIGGER_TYPE_KEYS,
    )
    return Section(heading="Triggers", content=(BulletList(items),))


def _build_conditions(automation: Automation) -> Section:
    """Build Conditions from explicit condition types in ``Automation.raw``."""
    items = _explicit_type_items(
        _raw_list(automation.raw, _RAW_CONDITION_KEYS),
        _CONDITION_TYPE_KEYS,
    )
    return Section(heading="Conditions", content=(BulletList(items),))


def _build_actions(automation: Automation) -> Section:
    """Build Actions from explicit service/action names in ``Automation.raw``."""
    items = _explicit_type_items(
        _raw_list(automation.raw, _RAW_ACTION_KEYS),
        _ACTION_NAME_KEYS,
    )
    return Section(heading="Actions", content=(BulletList(items),))


def _build_relationships(
    relationships: tuple[Relationship, ...],
) -> Section:
    """Build Relationships from the given Relationship tuple as-is."""
    items = tuple(
        f"{relationship.relationship_type} → "
        f"{relationship.target_type}:{relationship.target_id}"
        for relationship in relationships
    )
    return Section(heading="Relationships", content=(BulletList(items),))


def _raw_list(
    raw: Mapping[str, object],
    keys: tuple[str, ...],
) -> object:
    """Return the first present raw field among *keys*, else empty tuple."""
    for key in keys:
        if key in raw:
            return raw[key]
    return ()


def _explicit_type_items(
    value: object,
    type_keys: tuple[str, ...],
) -> tuple[str, ...]:
    """Collect explicit string type/name values from YAML list or mapping."""
    items: list[str] = []
    for mapping in _as_mappings(value):
        label = _first_string(mapping, type_keys)
        if label is not None:
            items.append(label)
    return tuple(items)


def _as_mappings(value: object) -> tuple[Mapping[object, object], ...]:
    """Normalize a YAML list or single mapping to a mapping tuple."""
    if isinstance(value, Mapping):
        return (value,)
    if isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    ):
        return tuple(item for item in value if isinstance(item, Mapping))
    return ()


def _first_string(
    mapping: Mapping[object, object],
    keys: tuple[str, ...],
) -> str | None:
    """Return the first explicit string value for *keys*, or None."""
    for key in keys:
        candidate = mapping.get(key)
        if isinstance(candidate, str):
            return candidate
    return None


def _append_if_present(items: list[str], label: str, value: str | None) -> None:
    """Append ``label: value`` when *value* is a non-empty string."""
    if value:
        items.append(f"{label}: {value}")
