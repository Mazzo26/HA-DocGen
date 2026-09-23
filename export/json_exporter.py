"""Stateless JSON rendering for an immutable Prompt.

Emits stored prompt fields only. Object keys are sorted. Sequence order
is kept. Nothing is written to disk.
"""

from __future__ import annotations

import json

from ..prompt import Prompt
from ._payload import prompt_data


class JsonExporter:
    """Render a ``Prompt`` as deterministic JSON."""

    def export(self, prompt: Prompt) -> str:
        """Return JSON for ``prompt`` without changing it."""
        rendered = json.dumps(
            prompt_data(prompt),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )
        return f"{rendered}\n"
