"""Generic recursive YAML tree traversal helpers.

Walks mappings and sequences without interpreting Home Assistant
semantics. Shared by relationship analyzers (Modules 6.4+).

Also exposes generic extraction of explicit identity values,
service/action names and ``target`` entity ids — still without
building relationships or applying domain rules.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Final

KEY_ENTITY: Final[str] = "entity"
KEY_ENTITIES: Final[str] = "entities"
KEY_ENTITY_ID: Final[str] = "entity_id"
KEY_DEVICE: Final[str] = "device"
KEY_DEVICE_ID: Final[str] = "device_id"
KEY_AREA_ID: Final[str] = "area_id"
KEY_SERVICE: Final[str] = "service"
KEY_ACTION: Final[str] = "action"
KEY_TARGET: Final[str] = "target"

SERVICE_SCRIPT_TURN_ON: Final[str] = "script.turn_on"
SERVICE_SCENE_TURN_ON: Final[str] = "scene.turn_on"

_JINJA_MARKERS: Final[tuple[str, ...]] = ("{{", "{%")


def iter_mappings(node: object) -> Iterator[Mapping[object, object]]:
    """Yield every mapping in the YAML tree rooted at *node*."""
    if isinstance(node, Mapping):
        yield from _walk_mapping(node)
    elif _is_sequence(node):
        yield from _walk_sequence(node)


def is_jinja_template(value: str) -> bool:
    """Return True when *value* contains Jinja markers."""
    return any(marker in value for marker in _JINJA_MARKERS)


def explicit_id_values(value: object) -> tuple[str, ...]:
    """Return explicit non-template id strings from a scalar or list."""
    if isinstance(value, str):
        return () if is_jinja_template(value) else (value,)
    if _is_sequence(value):
        return tuple(
            item
            for item in value
            if isinstance(item, str) and not is_jinja_template(item)
        )
    return ()


def explicit_service_name(mapping: Mapping[object, object]) -> str | None:
    """Return an explicit service/action string, or None."""
    for key in (KEY_SERVICE, KEY_ACTION):
        value = mapping.get(key)
        if isinstance(value, str) and not is_jinja_template(value):
            return value
    return None


def target_entity_ids(mapping: Mapping[object, object]) -> tuple[str, ...]:
    """Collect entity ids from *mapping* and its direct ``target``."""
    ids = list(explicit_id_values(mapping.get(KEY_ENTITY_ID)))
    target = mapping.get(KEY_TARGET)
    if isinstance(target, Mapping):
        ids.extend(explicit_id_values(target.get(KEY_ENTITY_ID)))
    elif _is_sequence(target):
        for item in target:
            if isinstance(item, Mapping):
                ids.extend(explicit_id_values(item.get(KEY_ENTITY_ID)))
    return tuple(ids)


def _walk_mapping(
    mapping: Mapping[object, object],
) -> Iterator[Mapping[object, object]]:
    """Yield *mapping* and every nested mapping under its values."""
    yield mapping
    for value in mapping.values():
        yield from iter_mappings(value)


def _walk_sequence(
    sequence: Sequence[object],
) -> Iterator[Mapping[object, object]]:
    """Yield every mapping nested under *sequence* items."""
    for item in sequence:
        yield from iter_mappings(item)


def _is_sequence(node: object) -> bool:
    """Return True for list-like YAML nodes (not str/bytes/Mapping)."""
    return isinstance(node, Sequence) and not isinstance(
        node, (str, bytes, bytearray, Mapping)
    )
