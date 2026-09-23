"""Plain-text rendering of JSON-compatible prompt values.

Mapping keys are sorted. Sequence order is kept. The text uses no
Markdown markers.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..prompt import Prompt, PromptType

_TITLES: Mapping[PromptType, str] = {
    PromptType.GENERIC: "Generic Prompt",
    PromptType.PROGRAMMING: "Programming Prompt",
    PromptType.REFACTORING: "Refactoring Prompt",
    PromptType.DOCUMENTATION: "Documentation Prompt",
}


def prompt_title(prompt: Prompt) -> str:
    """Return the stable display title for ``prompt``."""
    return _TITLES[prompt.prompt_type]


def render_data(value: object) -> str:
    """Return deterministic plain text for one JSON-compatible value."""
    return "\n".join(_lines(value, 0))


def _lines(value: object, indent: int) -> list[str]:
    """Render one mapping or sequence at ``indent``."""
    if isinstance(value, dict):
        return _mapping(value, indent)
    if isinstance(value, list):
        return _sequence(value, indent)
    raise TypeError(f"Unsupported export value: {type(value).__name__}")


def _mapping(value: Mapping[str, object], indent: int) -> list[str]:
    """Render mapping keys in alphabetical order."""
    if not value:
        return [_pad(indent, "{}")]
    lines: list[str] = []
    prefix = "  " * indent
    for key in sorted(value):
        lines.extend(_item(prefix, key, value[key], indent))
    return lines


def _sequence(value: list[object], indent: int) -> list[str]:
    """Render sequence items in their existing order."""
    if not value:
        return [_pad(indent, "[]")]
    lines: list[str] = []
    prefix = "  " * indent
    for index, item in enumerate(value):
        lines.extend(_item(prefix, f"[{index}]", item, indent))
    return lines


def _item(prefix: str, key: str, value: object, indent: int) -> list[str]:
    """Render one named value."""
    if isinstance(value, dict):
        return _nested(prefix, key, value, indent)
    if isinstance(value, list):
        return _nested(prefix, key, value, indent)
    return _keyed_scalar(prefix, key, value)


def _nested(
    prefix: str,
    key: str,
    value: Mapping[str, object] | list[object],
    indent: int,
) -> list[str]:
    """Render a mapping or sequence under its key."""
    if isinstance(value, dict):
        body = _mapping(value, indent + 1)
    else:
        body = _sequence(value, indent + 1)
    if not value:
        return [f"{prefix}{key}: {body[0].lstrip()}"]
    return [f"{prefix}{key}:", *body]


def _keyed_scalar(prefix: str, key: str, value: object) -> list[str]:
    """Render a scalar, keeping embedded newlines indented."""
    text = _scalar(value)
    if "\n" not in text:
        return [f"{prefix}{key}: {text}"]
    pad = f"{prefix}  "
    return [f"{prefix}{key}:", *[f"{pad}{line}" for line in text.split("\n")]]


def _scalar(value: object) -> str:
    """Return one deterministic scalar token."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    return str(value)


def _pad(indent: int, text: str) -> str:
    """Indent ``text`` by two spaces per level."""
    return f"{'  ' * indent}{text}"
