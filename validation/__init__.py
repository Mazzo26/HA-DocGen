"""Immutable validation models and validators for HA-DocGen.

``ValidationResult`` is a generic finding identity.
``ValidationCollection`` holds results and exposes O(1) object,
severity and type lookups. ``ValidationRepository`` is the central
immutable store with read-only lookups. ``ValidationReport``
aggregates repository findings into an immutable summary.
``EntityValidator``, ``AutomationValidator`` and ``ScriptValidator``
apply explicit integrity checks. ``PackageValidator`` reports
project-wide duplicate identifiers. ``MQTTValidator`` reports MQTT
structural consistency findings. No validation engine or Home
Assistant write coupling.
"""

from __future__ import annotations

from .automation_validator import AutomationValidator
from .entity_validator import EntityValidator
from .models import (
    ValidationCollection,
    ValidationResult,
    ValidationSeverity,
    ValidationType,
)
from .mqtt_validator import MQTTValidator
from .package_validator import PackageValidator
from .report import ValidationReport
from .repository import ValidationRepository
from .script_validator import ScriptValidator

__all__ = [
    "AutomationValidator",
    "EntityValidator",
    "MQTTValidator",
    "PackageValidator",
    "ScriptValidator",
    "ValidationCollection",
    "ValidationReport",
    "ValidationRepository",
    "ValidationResult",
    "ValidationSeverity",
    "ValidationType",
]
