"""JSON-compatible copy of prompt values.

Public dataclass fields only. Properties, private fields and extra
summaries are omitted. Sequence order is kept. Cyclic containers fail
instead of emitting a synthetic reference.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from ..prompt import Prompt, PromptSection


def prompt_data(prompt: Prompt) -> dict[str, object]:
    """Return the stored prompt fields in a JSON-compatible form."""
    return {
        "formatting_hints": to_data(prompt.formatting_hints),
        "prompt_type": prompt.prompt_type.value,
        "sections": [_section_data(section) for section in prompt.sections],
        "system_instructions": prompt.system_instructions,
        "task_description": prompt.task_description,
    }


def to_data(value: object) -> object:
    """Return a JSON-compatible copy of ``value``."""
    return _to_data(value, set())


def _section_data(section: PromptSection) -> dict[str, object]:
    """Return one section's stored fields."""
    return {
        "content": to_data(section.content),
        "kind": section.kind.value,
        "title": section.title,
    }


def _to_data(value: object, active: set[int]) -> object:
    """Convert ``value`` without revisiting an active container."""
    found, simple = _simple(value)
    if found:
        return simple
    if isinstance(value, bytes | bytearray):
        raise TypeError(f"Unsupported export value: {type(value).__name__}")
    if is_dataclass(value) and not isinstance(value, type):
        return _dataclass_data(value, active)
    if isinstance(value, Mapping):
        return _mapping_data(value, active)
    if isinstance(value, Sequence):
        return _sequence_data(value, active)
    raise TypeError(f"Unsupported export value: {type(value).__name__}")


def _simple(value: object) -> tuple[bool, object]:
    """Return a primitive JSON value, or ``(False, None)``."""
    if isinstance(value, Enum):
        return True, value.value
    if value is None or isinstance(value, str | int | float | bool):
        return True, value
    if isinstance(value, Path):
        return True, value.as_posix()
    if isinstance(value, datetime):
        return True, value.isoformat()
    return False, None


def _dataclass_data(value: object, active: set[int]) -> dict[str, object]:
    """Copy public dataclass fields."""
    _enter(value, active)
    payload = {name: _to_data(getattr(value, name), active) for name in _field_names(value)}
    _leave(value, active)
    return payload


def _field_names(value: object) -> tuple[str, ...]:
    """Return public dataclass field names in definition order."""
    table = getattr(value, "__dataclass_fields__", {})
    return tuple(str(name) for name in table if not str(name).startswith("_"))


def _mapping_data(value: Mapping[object, object], active: set[int]) -> dict[str, object]:
    """Copy a mapping. Keys become strings."""
    _enter(value, active)
    payload = {_key(key): _to_data(item, active) for key, item in value.items()}
    _leave(value, active)
    return payload


def _sequence_data(value: Sequence[object], active: set[int]) -> list[object]:
    """Copy a sequence without sorting it."""
    _enter(value, active)
    payload = [_to_data(item, active) for item in value]
    _leave(value, active)
    return payload


def _enter(value: object, active: set[int]) -> None:
    """Mark ``value`` as active, or fail when it is already active."""
    marker = id(value)
    if marker in active:
        raise TypeError("Cyclic prompt content cannot be exported")
    active.add(marker)


def _leave(value: object, active: set[int]) -> None:
    """Allow a later sibling to copy the same shared object again."""
    active.remove(id(value))


def _key(key: object) -> str:
    """Return a stable string key."""
    if isinstance(key, Enum):
        return str(key.value)
    if isinstance(key, bool):
        return "true" if key else "false"
    if key is None:
        return "null"
    if isinstance(key, str | int | float):
        return str(key)
    raise TypeError(f"Unsupported export key: {type(key).__name__}")
