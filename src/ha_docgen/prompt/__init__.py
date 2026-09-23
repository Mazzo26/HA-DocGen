"""Provider-neutral prompts built from an existing AIContext.

``Prompt``, ``PromptSection`` and ``PromptType`` are immutable.
``PromptBuilder`` selects parts of an ``AIContext`` and keeps the
original objects. No parsers, exporters, providers or filesystem coupling.
"""

from __future__ import annotations

from .builder import PromptBuilder
from .models import Prompt, PromptSection, PromptSectionKind, PromptType

__all__ = [
    "Prompt",
    "PromptBuilder",
    "PromptSection",
    "PromptSectionKind",
    "PromptType",
]
