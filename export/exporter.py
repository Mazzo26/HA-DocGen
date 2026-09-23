"""Dispatch an immutable Prompt to one format exporter.

Stateless. The prompt is the only input. No repository, analysis model
or filesystem access.
"""

from __future__ import annotations

from collections.abc import Mapping

from ..prompt import Prompt
from .json_exporter import JsonExporter
from .markdown_exporter import MarkdownExporter
from .models import ExportFormat
from .plain_text_exporter import PlainTextExporter

_EXPORTERS: Mapping[ExportFormat, type[MarkdownExporter | JsonExporter | PlainTextExporter]] = {
    ExportFormat.MARKDOWN: MarkdownExporter,
    ExportFormat.JSON: JsonExporter,
    ExportFormat.PLAIN_TEXT: PlainTextExporter,
}


class PromptExporter:
    """Render a ``Prompt`` in one ``ExportFormat``.

    Fully stateless: no instance state, no caching and no side effects.
    """

    def export(self, prompt: Prompt, export_format: ExportFormat) -> str:
        """Return ``prompt`` rendered as ``export_format``."""
        exporter_type = _EXPORTERS.get(export_format)
        if exporter_type is None:
            raise ValueError(f"Unsupported export format: {export_format!r}")
        return exporter_type().export(prompt)
