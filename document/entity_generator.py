"""Build a Document for exactly one Home Assistant entity.

Transforms one Entity and an explicit Relationship tuple into an
immutable ``Document`` tree. Produces document models only — no
Markdown, filesystem, repository, graph or Home Assistant aggregate
coupling.
"""

from __future__ import annotations

from ..registries.models import Entity
from ..relationships.models import Relationship
from .models import BulletList, Document, Paragraph, Section


class EntityDocumentGenerator:
    """Generate a Document for one Entity.

    Fully stateless: no instance state, no caching, no filesystem and
    no side effects. Callers supply the Entity and already-resolved
    Relationship objects.
    """

    def generate(
        self,
        entity: Entity,
        relationships: tuple[Relationship, ...],
    ) -> Document:
        """Return a Document describing *entity* and *relationships*."""
        return Document(
            title=f"Entity: {entity.entity_id}",
            sections=(
                _overview_section(entity),
                _registry_section(entity),
                _relationships_section(relationships),
            ),
        )


def _overview_section(entity: Entity) -> Section:
    """Build the Overview section from available registry identity fields."""
    lines = [f"Entity ID: {entity.entity_id}"]
    friendly_name = _friendly_name(entity)
    if friendly_name is not None:
        lines.append(f"Friendly name: {friendly_name}")
    platform = _platform(entity)
    if platform is not None:
        lines.append(f"Platform: {platform}")
    lines.append(f"Domain: {entity.domain}")
    return Section(heading="Overview", content=(Paragraph("\n".join(lines)),))


def _registry_section(entity: Entity) -> Section:
    """Build the Registry section listing present first-class fields."""
    items: list[str] = []
    _append_if_present(items, "unique_id", entity.unique_id)
    _append_if_present(items, "device_id", entity.device_id)
    _append_if_present(items, "area_id", entity.area_id)
    _append_if_present(items, "disabled_by", entity.disabled_by)
    _append_if_present(items, "hidden_by", entity.hidden_by)
    _append_if_present(items, "config_entry_id", entity.config_entry_id)
    return Section(heading="Registry", content=(BulletList(tuple(items)),))


def _relationships_section(
    relationships: tuple[Relationship, ...],
) -> Section:
    """Build the Relationships section from the given Relationship tuple."""
    items = tuple(
        f"{relationship.relationship_type} → "
        f"{relationship.target_type}:{relationship.target_id}"
        for relationship in relationships
    )
    return Section(heading="Relationships", content=(BulletList(items),))


def _friendly_name(entity: Entity) -> str | None:
    """Return the user-set name when present; otherwise None."""
    return entity.name


def _platform(entity: Entity) -> str | None:
    """Return platform from registry ``extra`` when it is a string."""
    value = entity.extra.get("platform")
    return value if isinstance(value, str) else None


def _append_if_present(items: list[str], label: str, value: str | None) -> None:
    """Append ``label: value`` when *value* is a non-empty string."""
    if value:
        items.append(f"{label}: {value}")
