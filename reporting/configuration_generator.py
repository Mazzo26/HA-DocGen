"""Build a Configuration Report from existing project analysis.

Aggregates ``HomeAssistantModel`` and ``YamlRepository`` into immutable
report models. Performs no scanning, parsing, rendering or filesystem
writes.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

from ..automation.models import Automation
from ..helper.models import Helper
from ..registries.home_assistant_model import HomeAssistantModel
from ..registries.models import Entity
from ..script.models import Script
from ..yaml.repository import YamlRepository
from .models import Report, ReportMetadata, ReportSection, Severity

_TITLE = "Configuration Report"
_DESCRIPTION = "Configuration overview derived from existing registry and YAML analysis."
_NAMED_DOMAINS: tuple[tuple[str, str], ...] = (
    ("sensor", "Sensor"),
    ("binary_sensor", "Binary Sensor"),
    ("switch", "Switch"),
    ("light", "Light"),
    ("cover", "Cover"),
    ("climate", "Climate"),
    ("camera", "Camera"),
)
_NAMED_DOMAIN_SET = frozenset(domain for domain, _ in _NAMED_DOMAINS)


class ConfigurationReportGenerator:
    """Generate a Configuration Report from already-analysed project data."""

    def generate(
        self,
        model: HomeAssistantModel,
        yaml_repository: YamlRepository,
        metadata: ReportMetadata,
    ) -> Report:
        """Return an output-independent Configuration Report."""
        statistics = _statistics(model, yaml_repository)
        return Report(
            title=_TITLE,
            metadata=metadata,
            description=_DESCRIPTION,
            sections=_sections(model, yaml_repository, statistics),
            statistics=statistics,
            recommendations=_recommendations(statistics),
            summary=_summary(statistics),
        )


def _statistics(
    model: HomeAssistantModel,
    repository: YamlRepository,
) -> dict[str, int | float]:
    """Build deterministic configuration statistics from existing totals."""
    domains = _domain_counts(model.entities)
    statistics = _registry_statistics(model, domains)
    statistics.update(_yaml_statistics(repository))
    return statistics


def _registry_statistics(
    model: HomeAssistantModel,
    domains: dict[str, int],
) -> dict[str, int | float]:
    """Aggregate registry and domain-derived totals."""
    return {
        "total_areas": len(model.areas),
        "total_binary_sensors": domains.get("binary_sensor", 0),
        "total_cameras": domains.get("camera", 0),
        "total_climate": domains.get("climate", 0),
        "total_config_entries": len(model.config_entries),
        "total_covers": domains.get("cover", 0),
        "total_devices": len(model.devices),
        "total_domains": len(domains),
        "total_entities": len(model.entities),
        "total_floors": len(model.floors),
        "total_labels": len(model.labels),
        "total_lights": domains.get("light", 0),
        "total_mqtt_entities": len(_mqtt_entities(model.entities)),
        "total_sensors": domains.get("sensor", 0),
        "total_switches": domains.get("switch", 0),
        "total_template_entities": len(_template_entities(model.entities)),
    }


def _yaml_statistics(repository: YamlRepository) -> dict[str, int | float]:
    """Aggregate YAML repository totals."""
    return {
        "total_automations": len(repository.automations),
        "total_blueprints": len(repository.blueprints),
        "total_dashboards": len(repository.dashboards),
        "total_helpers": len(repository.helpers),
        "total_packages": len(repository.packages),
        "total_scenes": len(repository.scenes),
        "total_scripts": len(repository.scripts),
        "total_templates": len(repository.templates),
    }


def _domain_counts(entities: tuple[Entity, ...]) -> dict[str, int]:
    """Count entities per domain from already-parsed entity identifiers."""
    counts: dict[str, int] = defaultdict(int)
    for entity in entities:
        counts[entity.domain] += 1
    return dict(counts)


def _platform(entity: Entity) -> str | None:
    """Return platform from registry ``extra`` when it is a string."""
    value = entity.extra.get("platform")
    return value if isinstance(value, str) else None


def _mqtt_entities(entities: tuple[Entity, ...]) -> tuple[Entity, ...]:
    """Return entities already identified as MQTT via domain or platform."""
    return tuple(
        entity for entity in entities if entity.domain == "mqtt" or _platform(entity) == "mqtt"
    )


def _template_entities(entities: tuple[Entity, ...]) -> tuple[Entity, ...]:
    """Return entities already identified as template via platform."""
    return tuple(entity for entity in entities if _platform(entity) == "template")


def _other_entities(entities: tuple[Entity, ...]) -> tuple[Entity, ...]:
    """Return entities whose domain is outside the named inventory domains."""
    return tuple(
        entity
        for entity in entities
        if entity.domain not in _NAMED_DOMAIN_SET and entity.domain != "mqtt"
    )


def _summary(statistics: Mapping[str, int | float]) -> str:
    """Build the overall project and configuration summary."""
    if statistics["total_entities"] == 0 and statistics["total_packages"] == 0:
        return "No configuration information is available."
    return (
        f"Configuration overview: {statistics['total_packages']} package(s), "
        f"{statistics['total_entities']} entities, "
        f"{statistics['total_automations']} automation(s), "
        f"{statistics['total_scripts']} script(s), and "
        f"{statistics['total_helpers']} helper(s)."
    )


def _sections(
    model: HomeAssistantModel,
    repository: YamlRepository,
    statistics: Mapping[str, int | float],
) -> tuple[ReportSection, ...]:
    """Build summary, inventory and statistics sections."""
    if all(value == 0 for value in statistics.values()):
        return ()
    return (
        _summary_section(statistics),
        _inventory_section(model, repository),
        _statistics_section(statistics),
    )


def _summary_section(statistics: Mapping[str, int | float]) -> ReportSection:
    """Build the configuration overview section."""
    return ReportSection(
        title="Summary",
        severity=Severity.INFO,
        description="Overall project summary and configuration overview.",
        items=(
            f"Packages: {statistics['total_packages']}",
            f"Entities: {statistics['total_entities']}",
            f"Automations: {statistics['total_automations']}",
            f"Scripts: {statistics['total_scripts']}",
            f"Helpers: {statistics['total_helpers']}",
            f"Devices: {statistics['total_devices']}",
            f"Config entries: {statistics['total_config_entries']}",
        ),
    )


def _inventory_section(
    model: HomeAssistantModel,
    repository: YamlRepository,
) -> ReportSection:
    """Build the configuration inventory from existing collections."""
    return ReportSection(
        title="Configuration Inventory",
        severity=Severity.INFO,
        description="Discovered configuration objects by category.",
        items=_yaml_inventory(repository) + _entity_inventory(model.entities),
    )


def _yaml_inventory(repository: YamlRepository) -> tuple[str, ...]:
    """List packages, automations, scripts and helpers from YamlRepository."""
    items = [
        f"Package: {package.name}"
        for package in sorted(repository.packages, key=lambda item: item.name)
    ]
    items.extend(
        f"Automation: {_automation_label(automation)}"
        for automation in sorted(
            repository.automations,
            key=lambda item: (item.id or "", item.alias or ""),
        )
    )
    items.extend(
        f"Script: {_script_label(script)}"
        for script in sorted(
            repository.scripts,
            key=lambda item: (item.id or "", item.alias or ""),
        )
    )
    items.extend(_helper_items(repository.helpers))
    return tuple(items)


def _helper_items(helpers: tuple[Helper, ...]) -> tuple[str, ...]:
    """List helpers deterministically."""
    return tuple(
        f"Helper: {helper.type}.{helper.id}"
        for helper in sorted(helpers, key=lambda item: (item.type, item.id))
    )


def _automation_label(automation: Automation) -> str:
    """Return a stable automation label from id or alias."""
    if automation.id:
        return automation.id
    if automation.alias:
        return automation.alias
    return "(unnamed)"


def _script_label(script: Script) -> str:
    """Return a stable script label from id or alias."""
    if script.id:
        return script.id
    if script.alias:
        return script.alias
    return "(unnamed)"


def _entity_inventory(entities: tuple[Entity, ...]) -> tuple[str, ...]:
    """List named domains, MQTT, template and other discovered entities."""
    items: list[str] = []
    for domain, label in _NAMED_DOMAINS:
        items.extend(
            f"{label}: {entity.entity_id}" for entity in _entities_for_domain(entities, domain)
        )
    items.extend(_labeled_entities("MQTT entity", _mqtt_entities(entities)))
    items.extend(_labeled_entities("Template entity", _template_entities(entities)))
    items.extend(
        f"Other ({entity.domain}): {entity.entity_id}"
        for entity in sorted(
            _other_entities(entities),
            key=lambda item: (item.domain, item.entity_id),
        )
    )
    return tuple(items)


def _labeled_entities(prefix: str, entities: tuple[Entity, ...]) -> tuple[str, ...]:
    """Format entity identifiers with a shared prefix."""
    return tuple(
        f"{prefix}: {entity.entity_id}"
        for entity in sorted(entities, key=lambda item: item.entity_id)
    )


def _entities_for_domain(
    entities: tuple[Entity, ...],
    domain: str,
) -> tuple[Entity, ...]:
    """Return entities for one domain in deterministic order."""
    return tuple(
        sorted(
            (entity for entity in entities if entity.domain == domain),
            key=lambda item: item.entity_id,
        )
    )


def _statistics_section(statistics: Mapping[str, int | float]) -> ReportSection:
    """Build a plain-text statistics section."""
    return ReportSection(
        title="Statistics",
        severity=Severity.INFO,
        items=tuple(f"{key}: {value}" for key, value in sorted(statistics.items())),
    )


def _recommendations(statistics: Mapping[str, int | float]) -> tuple[str, ...]:
    """Derive recommendations only from existing configuration totals."""
    recommendations: list[str] = []
    if statistics["total_packages"] == 0 and statistics["total_entities"] > 0:
        recommendations.append(
            "Consider organising configuration into packages for maintainability."
        )
    if statistics["total_automations"] == 0 and statistics["total_packages"] > 0:
        recommendations.append("No automations were found in analysed packages.")
    if statistics["total_helpers"] == 0 and statistics["total_automations"] > 0:
        recommendations.append("No helpers were found alongside analysed automations.")
    return tuple(recommendations)
