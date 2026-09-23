"""Filesystem export of documentation repositories to Markdown files.

Writes already-generated ``Document`` objects from a
``DocumentRepository`` as ``.md`` files via ``MarkdownBuilder``.
Performs no generation, analysis or repository mutation.
"""

from __future__ import annotations

import re
from pathlib import Path

from .builder import MarkdownBuilder
from .models import Document
from .repository import DocumentRepository

_MULTI_DASH = re.compile(r"-{2,}")


class MarkdownExporter:
    """Export a DocumentRepository to Markdown files on disk.

    Fully stateless: no instance state, no caching, no configuration
    and no side effects beyond the explicit ``export`` write.
    """

    def export(
        self,
        repository: DocumentRepository,
        output_directory: Path,
    ) -> None:
        """Write one Markdown file per document plus ``index.md``."""
        output_directory.mkdir(parents=True, exist_ok=True)
        builder = MarkdownBuilder()
        entries: list[tuple[str, str]] = []
        for document in repository.documents:
            filename = _filename_from_title(document.title)
            entries.append((document.title, filename))
            _write_document(output_directory, filename, builder, document)
        _write_index(output_directory, entries)


def _filename_from_title(title: str) -> str:
    """Return a deterministic safe Markdown filename from a title."""
    name = title.lower().replace(":", "").replace("/", "-").replace(" ", "-")
    name = _MULTI_DASH.sub("-", name).strip("-")
    return f"{name}.md"


def _write_document(
    output_directory: Path,
    filename: str,
    builder: MarkdownBuilder,
    document: Document,
) -> None:
    """Render ``document`` and write it under ``output_directory``."""
    (output_directory / filename).write_text(
        builder.build(document),
        encoding="utf-8",
    )


def _write_index(
    output_directory: Path,
    entries: list[tuple[str, str]],
) -> None:
    """Write ``index.md`` linking each exported document by title."""
    chunks: list[str] = ["# Documentation\n\n"]
    for title, filename in entries:
        chunks.append(f"- [{title}]({filename})\n")
    (output_directory / "index.md").write_text(
        "".join(chunks),
        encoding="utf-8",
    )
