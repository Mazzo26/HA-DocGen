"""Central read-only documentation repository.

Holds already-generated ``Document`` objects and provides O(1)
lookups. Performs no generation, rendering or filesystem access.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TypeVar

from .models import Document

_IndexKey = TypeVar("_IndexKey")


@dataclass(frozen=True, slots=True)
class DocumentRepository:
    """Immutable store of documents with read-only title lookups.

    Accepts only already-generated ``Document`` objects. Deduplicates
    and sorts deterministically during construction. Generator-agnostic:
    callers assemble documents before construction.
    """

    documents: tuple[Document, ...] = ()

    _by_title: Mapping[str, tuple[Document, ...]] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """Deduplicate, sort and build immutable lookup indexes."""
        object.__setattr__(
            self,
            "documents",
            _deduplicate_and_sort(self.documents),
        )
        self._build_indexes()

    def _build_indexes(self) -> None:
        """Populate MappingProxyType indexes for title lookups."""
        by_title: dict[str, list[Document]] = defaultdict(list)
        for document in self.documents:
            by_title[document.title].append(document)
        object.__setattr__(self, "_by_title", _freeze_index(by_title))

    def document(self, title: str) -> Document | None:
        """Return the first document with the given title, if present."""
        documents = self._by_title.get(title, ())
        return documents[0] if documents else None

    def documents_by_title(self, title: str) -> tuple[Document, ...]:
        """Return all documents with the given title."""
        return self._by_title.get(title, ())


def _document_sort_key(document: Document) -> str:
    """Deterministic sort key for reproducible repository contents."""
    return document.title


def _deduplicate_and_sort(
    documents: Iterable[Document],
) -> tuple[Document, ...]:
    """Remove duplicate documents and return a sorted immutable tuple."""
    return tuple(sorted(set(documents), key=_document_sort_key))


def _freeze_index(  # noqa: UP047
    index: dict[_IndexKey, list[Document]],
) -> Mapping[_IndexKey, tuple[Document, ...]]:
    """Convert a mutable list index into a read-only MappingProxyType."""
    return MappingProxyType({key: tuple(items) for key, items in index.items()})
