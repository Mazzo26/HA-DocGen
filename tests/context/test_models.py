"""Unit tests for AI context domain models."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, asdict, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ha_docgen.context import (
    AIContext,
    ContextMetadata,
    ContextSection,
    ContextSectionKind,
    DashboardContext,
    EntityContext,
    ESPHomeDeviceContext,
    ESPHomeSensorContext,
    PackageContext,
)
from ha_docgen.dashboard import Dashboard
from ha_docgen.esphome import ESPHomeDevice, ESPHomeSensor
from ha_docgen.packages import Package
from ha_docgen.registries.models import Entity
from ha_docgen.yaml import YamlDocument


def _entity(entity_id: str) -> Entity:
    return Entity(registry_id=entity_id, entity_id=entity_id, unique_id=entity_id)


def _metadata(
    *,
    repository_name: str | None = None,
    project_path: Path | None = None,
    version: str | None = None,
    generated_at: datetime | None = None,
) -> ContextMetadata:
    return ContextMetadata(
        repository_name=repository_name,
        project_path=project_path,
        version=version,
        generated_at=generated_at,
    )


def _section(
    *,
    kind: ContextSectionKind = ContextSectionKind.ENTITIES,
    title: str = "Entities",
    items: tuple[Entity, ...] = (),
) -> ContextSection:
    return ContextSection(kind=kind, title=title, items=items or (_entity("light.kitchen"),))


def _context(
    *,
    metadata: ContextMetadata | None = None,
    sections: tuple[ContextSection, ...] | None = None,
) -> AIContext:
    return AIContext(
        metadata=metadata or _metadata(),
        sections=sections if sections is not None else (_section(),),
    )


def test_section_kind_members() -> None:
    assert set(ContextSectionKind) == {
        ContextSectionKind.ENTITIES,
        ContextSectionKind.DEVICES,
        ContextSectionKind.AREAS,
        ContextSectionKind.LABELS,
        ContextSectionKind.FLOORS,
        ContextSectionKind.CONFIG_ENTRIES,
    }
    assert ContextSectionKind.ENTITIES == "entities"
    assert isinstance(ContextSectionKind.DEVICES, str)


def test_section_kind_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        ContextSectionKind("packages")


def test_metadata_defaults_are_empty() -> None:
    metadata = ContextMetadata()
    assert metadata.repository_name is None
    assert metadata.project_path is None
    assert metadata.version is None
    assert metadata.generated_at is None


def test_metadata_creation() -> None:
    generated_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    metadata = _metadata(
        repository_name="home",
        project_path=Path("/config"),
        version="1.2.3",
        generated_at=generated_at,
    )
    assert metadata.repository_name == "home"
    assert metadata.project_path == Path("/config")
    assert metadata.version == "1.2.3"
    assert metadata.generated_at == generated_at


def test_metadata_immutable_and_hashable() -> None:
    metadata = _metadata(repository_name="home")
    assert hash(metadata) == hash(_metadata(repository_name="home"))
    with pytest.raises(FrozenInstanceError):
        metadata.version = "9.9.9"  # type: ignore[misc]


def test_section_keeps_original_objects_in_input_order() -> None:
    first = _entity("light.b")
    second = _entity("light.a")
    section = ContextSection(
        kind=ContextSectionKind.ENTITIES,
        title="Entities",
        items=[first, second],  # type: ignore[arg-type]
    )
    assert section.items == (first, second)
    assert section.items[0] is first
    assert section.items[1] is second


def test_section_default_items_are_empty() -> None:
    section = ContextSection(kind=ContextSectionKind.AREAS, title="Areas")
    assert section.items == ()


def test_section_immutable() -> None:
    section = _section()
    with pytest.raises(FrozenInstanceError):
        section.title = "Changed"  # type: ignore[misc]


def test_section_equality() -> None:
    left = _section(items=(_entity("light.a"), _entity("light.b")))
    right = _section(items=(_entity("light.b"), _entity("light.a")))
    assert left != right
    assert left == _section(items=(_entity("light.a"), _entity("light.b")))


def test_context_orders_sections_by_kind_then_title() -> None:
    entities = _section()
    areas_b = ContextSection(
        kind=ContextSectionKind.AREAS,
        title="B",
        items=(),
    )
    areas_a = ContextSection(kind=ContextSectionKind.AREAS, title="A")
    context = _context(sections=(entities, areas_b, areas_a))
    assert [section.title for section in context.sections] == ["A", "B", "Entities"]


def test_context_default_sections_are_empty() -> None:
    context = AIContext(metadata=ContextMetadata())
    assert context.sections == ()
    assert context.entity_contexts == ()
    assert context.automation_contexts == ()
    assert context.dashboard_contexts == ()
    assert context.package_contexts == ()
    assert context.esphome_contexts == ()
    assert hash(context) == hash(AIContext(metadata=ContextMetadata()))


def test_context_without_domain_collections_matches_explicit_empty() -> None:
    metadata = ContextMetadata()
    assert AIContext(metadata=metadata) == AIContext(
        metadata=metadata,
        sections=(),
        entity_contexts=(),
        automation_contexts=(),
        dashboard_contexts=(),
        package_contexts=(),
        esphome_contexts=(),
    )


def test_context_public_fields_extend_registry_entity_and_automation() -> None:
    assert set(AIContext.__dataclass_fields__) == {
        "metadata",
        "sections",
        "entity_contexts",
        "automation_contexts",
        "dashboard_contexts",
        "package_contexts",
        "esphome_contexts",
    }


def test_context_orders_entity_contexts_by_identity() -> None:
    later = EntityContext(entity=_entity("light.b"))
    earlier = EntityContext(entity=_entity("light.a"))
    context = AIContext(metadata=ContextMetadata(), entity_contexts=(later, earlier))
    assert [item.entity.entity_id for item in context.entity_contexts] == [
        "light.a",
        "light.b",
    ]
    assert context.entity_contexts[0].entity is earlier.entity


def test_context_orders_dashboard_contexts_by_identity() -> None:
    later = DashboardContext(dashboard=Dashboard(id="b", title="B"))
    earlier = DashboardContext(dashboard=Dashboard(id="a", title="A"))
    context = AIContext(metadata=ContextMetadata(), dashboard_contexts=(later, earlier))
    assert [item.dashboard.id for item in context.dashboard_contexts] == ["a", "b"]
    assert context.dashboard_contexts[0].dashboard is earlier.dashboard


def test_context_orders_package_contexts_by_identity() -> None:
    document = YamlDocument(path=Path("packages/a.yaml"), text="", data={})
    later = PackageContext(
        package=Package(name="zeta", path=Path("packages/zeta.yaml"), document=document)
    )
    earlier = PackageContext(
        package=Package(name="alpha", path=Path("packages/alpha.yaml"), document=document)
    )
    context = AIContext(metadata=ContextMetadata(), package_contexts=(later, earlier))
    assert [item.package.name for item in context.package_contexts] == ["alpha", "zeta"]
    assert context.package_contexts[0].package is earlier.package


def test_context_orders_esphome_contexts_by_name_then_path() -> None:
    unnamed = ESPHomeDeviceContext(device=ESPHomeDevice(path=Path("esphome/z.yaml")))
    zeta = ESPHomeDeviceContext(device=ESPHomeDevice(name="zeta", path=Path("esphome/a.yaml")))
    alpha_b = ESPHomeDeviceContext(device=ESPHomeDevice(name="alpha", path=Path("esphome/b.yaml")))
    alpha_a = ESPHomeDeviceContext(device=ESPHomeDevice(name="alpha", path=Path("esphome/a.yaml")))
    context = AIContext(
        metadata=ContextMetadata(),
        esphome_contexts=(unnamed, zeta, alpha_b, alpha_a),
    )
    assert [(item.device.name, _path(item)) for item in context.esphome_contexts] == [
        ("alpha", "esphome/a.yaml"),
        ("alpha", "esphome/b.yaml"),
        ("zeta", "esphome/a.yaml"),
        (None, "esphome/z.yaml"),
    ]
    assert context.esphome_contexts[0].device is alpha_a.device


def _path(context: ESPHomeDeviceContext) -> str:
    path = context.device.path
    return "" if path is None else path.as_posix()


def test_sensor_contexts_are_ordered_and_immutable() -> None:
    later = ESPHomeSensorContext(sensor=ESPHomeSensor(identity="b", platform="gpio"))
    earlier = ESPHomeSensorContext(sensor=ESPHomeSensor(identity="a", platform="template"))
    same_identity = ESPHomeSensorContext(sensor=ESPHomeSensor(identity="a", platform="adc"))
    context = ESPHomeDeviceContext(
        device=ESPHomeDevice(name="alpha"),
        sensors=[later, earlier, same_identity],  # type: ignore[arg-type]
    )
    assert [item.sensor.identity for item in context.sensors] == ["a", "a", "b"]
    assert [item.sensor.platform for item in context.sensors] == ["adc", "template", "gpio"]
    assert context.sensors[1].sensor is earlier.sensor
    assert context.relationships == ()
    with pytest.raises(FrozenInstanceError):
        context.device = ESPHomeDevice(name="changed")  # type: ignore[misc]


def test_context_immutable() -> None:
    context = _context()
    with pytest.raises(FrozenInstanceError):
        context.metadata = ContextMetadata(version="9.9.9")  # type: ignore[misc]


def test_context_equality() -> None:
    left = _context()
    right = replace(left)
    other = _context(metadata=_metadata(version="9.0.0"))
    assert left == right
    assert left != other


def test_metadata_and_empty_context_asdict_round_trip() -> None:
    generated_at = datetime(2026, 9, 22, 16, 0, tzinfo=UTC)
    context = AIContext(
        metadata=_metadata(
            repository_name="home",
            project_path=Path("/config"),
            version="0.2.0",
            generated_at=generated_at,
        )
    )
    payload = asdict(context)
    encoded = json.dumps(payload, default=str)
    assert "home" in encoded
    restored = AIContext(
        metadata=ContextMetadata(**payload["metadata"]),
        sections=tuple(payload["sections"]),
    )
    assert restored == context
    assert restored.metadata.generated_at == generated_at
