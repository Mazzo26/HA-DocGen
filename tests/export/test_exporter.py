"""Unit tests for PromptExporter."""

from __future__ import annotations

import pytest

from ha_docgen.export import (
    ExportFormat,
    JsonExporter,
    MarkdownExporter,
    PlainTextExporter,
    PromptExporter,
)
from tests.export.factory import empty_prompt, populated_prompt


def test_prompt_exporter_matches_each_format() -> None:
    prompt = populated_prompt()
    exporter = PromptExporter()
    assert exporter.export(prompt, ExportFormat.MARKDOWN) == MarkdownExporter().export(prompt)
    assert exporter.export(prompt, ExportFormat.JSON) == JsonExporter().export(prompt)
    assert exporter.export(prompt, ExportFormat.PLAIN_TEXT) == PlainTextExporter().export(prompt)


def test_prompt_exporter_is_stateless() -> None:
    exporter = PromptExporter()
    assert exporter.__dict__ == {}
    first = exporter.export(empty_prompt(), ExportFormat.JSON)
    _ = exporter.export(populated_prompt(), ExportFormat.MARKDOWN)
    assert exporter.export(empty_prompt(), ExportFormat.JSON) == first
    assert exporter.__dict__ == {}


def test_prompt_exporter_rejects_an_unknown_format() -> None:
    with pytest.raises(ValueError, match="Unsupported export format"):
        PromptExporter().export(empty_prompt(), "html")  # type: ignore[arg-type]
