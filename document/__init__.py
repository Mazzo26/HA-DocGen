"""Immutable documentation models, Markdown builder and generators.

``Document``, ``Section`` and ``DocumentItem`` subtypes are pure
structural representations. ``MarkdownBuilder`` renders a ``Document``
to a Markdown string. ``PackageDocumentGenerator``,
``EntityDocumentGenerator``, ``AutomationDocumentGenerator`` and
``DashboardDocumentGenerator`` each build a ``Document`` from one
domain object. ``ConfigurationDocumentGenerator`` builds one
configuration-wide ``Document`` from existing aggregates.
``DocumentRepository`` is the central immutable store with read-only
title lookups. ``MarkdownExporter`` writes repository documents to
Markdown files via ``MarkdownBuilder``. No HTML, JSON or PDF.
"""

from __future__ import annotations

from .automation_generator import AutomationDocumentGenerator
from .builder import MarkdownBuilder
from .configuration_generator import ConfigurationDocumentGenerator
from .dashboard_generator import DashboardDocumentGenerator
from .entity_generator import EntityDocumentGenerator
from .exporter import MarkdownExporter
from .models import (
    BulletList,
    CodeBlock,
    Document,
    DocumentItem,
    Paragraph,
    Section,
    Table,
)
from .package_generator import PackageDocumentGenerator
from .repository import DocumentRepository

__all__ = [
    "AutomationDocumentGenerator",
    "BulletList",
    "CodeBlock",
    "ConfigurationDocumentGenerator",
    "DashboardDocumentGenerator",
    "Document",
    "DocumentItem",
    "DocumentRepository",
    "EntityDocumentGenerator",
    "MarkdownBuilder",
    "MarkdownExporter",
    "PackageDocumentGenerator",
    "Paragraph",
    "Section",
    "Table",
]
