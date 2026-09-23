"""Unit tests for DocumentRepository and MarkdownExporter."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from tools.ha_docgen.document import (
    Document,
    DocumentRepository,
    MarkdownExporter,
    Paragraph,
    Section,
)


def _document(title: str, text: str = "Body") -> Document:
    return Document(title, (Section("Content", (Paragraph(text),)),))


def test_repository_deduplicates_and_sorts_documents_by_title() -> None:
    alpha = _document("Alpha")
    zulu = _document("Zulu")

    repository = DocumentRepository((zulu, alpha, zulu))

    assert repository.documents == (alpha, zulu)
    assert isinstance(repository.documents, tuple)


def test_repository_looks_up_first_and_all_documents_by_exact_title() -> None:
    first = _document("Shared", "First")
    second = _document("Shared", "Second")
    repository = DocumentRepository((first, second))

    assert repository.document("Shared") in (first, second)
    assert set(repository.documents_by_title("Shared")) == {first, second}
    assert repository.document("shared") is None
    assert repository.documents_by_title("Missing") == ()


def test_repository_empty_behavior_and_immutability() -> None:
    repository = DocumentRepository()

    assert repository.documents == ()
    assert repository.document("Missing") is None
    with pytest.raises(FrozenInstanceError):
        repository.documents = ()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        repository.documents.append(_document("Other"))  # type: ignore[attr-defined]


def test_repository_does_not_mutate_supplied_collection() -> None:
    document = _document("One")
    supplied = [document, document]

    repository = DocumentRepository(supplied)  # type: ignore[arg-type]

    assert supplied == [document, document]
    assert repository.documents == (document,)


def test_exporter_writes_rendered_documents_and_deterministic_index(
    tmp_path: Path,
) -> None:
    repository = DocumentRepository(
        (
            _document("Package: Living / Room", "Lights"),
            _document("Automation: Arrival", "Welcome"),
        )
    )
    output = tmp_path / "nested" / "docs"

    MarkdownExporter().export(repository, output)

    assert sorted(path.name for path in output.iterdir()) == [
        "automation-arrival.md",
        "index.md",
        "package-living-room.md",
    ]
    assert (output / "automation-arrival.md").read_text(encoding="utf-8") == (
        "# Automation: Arrival\n\n## Content\n\nWelcome\n\n"
    )
    assert (output / "package-living-room.md").read_text(encoding="utf-8") == (
        "# Package: Living / Room\n\n## Content\n\nLights\n\n"
    )
    assert (output / "index.md").read_text(encoding="utf-8") == (
        "# Documentation\n\n"
        "- [Automation: Arrival](automation-arrival.md)\n"
        "- [Package: Living / Room](package-living-room.md)\n"
    )


def test_exporter_collapses_repeated_dashes_in_filenames(tmp_path: Path) -> None:
    repository = DocumentRepository((_document("Room: A / B"),))

    MarkdownExporter().export(repository, tmp_path)

    assert (tmp_path / "room-a-b.md").is_file()
    assert "--" not in next(path.name for path in tmp_path.iterdir() if path.name != "index.md")


def test_exporter_empty_repository_writes_only_empty_index(tmp_path: Path) -> None:
    MarkdownExporter().export(DocumentRepository(), tmp_path)

    assert tuple(path.name for path in tmp_path.iterdir()) == ("index.md",)
    assert (tmp_path / "index.md").read_text(encoding="utf-8") == ("# Documentation\n\n")


def test_exporter_is_stateless_and_does_not_mutate_repository(
    tmp_path: Path,
) -> None:
    repository = DocumentRepository((_document("Stable"),))
    before = repository.documents
    exporter = MarkdownExporter()

    exporter.export(repository, tmp_path)

    assert vars(exporter) == {}
    assert repository.documents == before
