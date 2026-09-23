"""Unit tests for export models."""

from __future__ import annotations

import json

import pytest

from ha_docgen.export import ExportFormat


def test_export_format_order_is_stable() -> None:
    assert tuple(ExportFormat) == (
        ExportFormat.MARKDOWN,
        ExportFormat.JSON,
        ExportFormat.PLAIN_TEXT,
    )


def test_export_format_values_are_provider_neutral() -> None:
    assert [item.value for item in ExportFormat] == ["markdown", "json", "plain_text"]
    assert ExportFormat.PLAIN_TEXT == "plain_text"


def test_export_format_serializes_deterministically() -> None:
    encoded = json.dumps([item.value for item in ExportFormat])
    assert encoded == '["markdown", "json", "plain_text"]'
    assert json.dumps(ExportFormat.JSON) == '"json"'


def test_export_format_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        ExportFormat("openai")


def test_export_format_member_is_immutable() -> None:
    with pytest.raises(AttributeError):
        ExportFormat.MARKDOWN.value = "html"  # type: ignore[misc]
