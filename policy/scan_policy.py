"""Central filesystem inclusion/exclusion policy.

Scanners delegate path decisions to ScanPolicy and must not embed
hardcoded ignore logic. IgnoreRules supply the rule sets; this module
evaluates them via the public include/exclude API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .ignore_rules import IgnoreRules


@dataclass(slots=True, frozen=True)
class ScanPolicy:
    """Decide which filesystem paths are included during a scan.

    Read-only: the policy never mutates the filesystem or its own rules.
    """

    rules: IgnoreRules = field(default_factory=IgnoreRules)

    def is_excluded(self, path: Path) -> bool:
        """Return True when the path matches any ignore rule."""
        return self.rules.matches(path)

    def is_included(self, path: Path) -> bool:
        """Return True when the path is not excluded by this policy."""
        return not self.is_excluded(path)
