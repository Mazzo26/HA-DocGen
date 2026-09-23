"""Export formats for an immutable prompt.

The format identifies Markdown, JSON or plain text. It does not name a
language-model provider and it does not render the prompt.
"""

from __future__ import annotations

from enum import StrEnum


class ExportFormat(StrEnum):
    """Deterministic export format for one ``Prompt``.

    Member order is the public order: Markdown, JSON, then plain text.
    """

    MARKDOWN = "markdown"
    JSON = "json"
    PLAIN_TEXT = "plain_text"
