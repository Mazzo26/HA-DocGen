"""Immutable aggregate of a completed analysis.

Holds references to the existing registry, YAML and relationship
aggregates. Performs no parsing, discovery, validation or copying.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..registries import HomeAssistantModel
from ..relationships import RelationshipRepository
from ..yaml import YamlRepository


@dataclass(frozen=True, slots=True)
class AnalysisModel:
    """Complete analysis result consumed by higher-level modules.

    Stores the three existing aggregates by reference. ESPHome devices
    are reached through ``yaml_repository``. Does not merge aggregate
    contents and does not add lookups or business logic.
    """

    home_assistant_model: HomeAssistantModel = field(default_factory=HomeAssistantModel)
    yaml_repository: YamlRepository = field(default_factory=YamlRepository)
    relationship_repository: RelationshipRepository = field(
        default_factory=RelationshipRepository,
    )
