"""Build a Document for exactly one Home Assistant dashboard.

Transforms one Dashboard and an explicit Relationship tuple into an
immutable ``Document`` tree. Produces document models only — no
Markdown, filesystem, repository, graph or Home Assistant aggregate
coupling.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from ..dashboard.models import Dashboard
from ..relationships.models import Relationship
from .models import BulletList, Document, Paragraph, Section


class DashboardDocumentGenerator:
    """Generate a Document for one Dashboard.

    Fully stateless: no instance state, no caching, no filesystem and
    no side effects. Callers supply the Dashboard and already-resolved
    Relationship objects.
    """

    def generate(
        self,
        dashboard: Dashboard,
        relationships: tuple[Relationship, ...],
    ) -> Document:
        """Return a Document describing *dashboard* and *relationships*."""
        return Document(
            title=_title(dashboard),
            sections=(
                _build_overview(dashboard),
                _build_views(dashboard),
                _build_relationships(relationships),
            ),
        )


def _title(dashboard: Dashboard) -> str:
    """Return ``Dashboard: {title}`` or ``Dashboard: {id}``."""
    label = dashboard.title if dashboard.title is not None else dashboard.id
    return f"Dashboard: {label}"


def _build_overview(dashboard: Dashboard) -> Section:
    """Build Overview from present first-class Dashboard fields."""
    lines: list[str] = []
    _append_if_present(lines, "id", dashboard.id)
    _append_if_present(lines, "title", dashboard.title)
    _append_if_present(lines, "mode", dashboard.mode)
    _append_path_if_present(lines, dashboard.path)
    return Section(heading="Overview", content=(Paragraph("\n".join(lines)),))


def _build_views(dashboard: Dashboard) -> Section:
    """Build Views from ``Dashboard.views`` metadata only."""
    items = tuple(_view_label(view) for view in dashboard.views)
    return Section(heading="Views", content=(BulletList(items),))


def _build_relationships(
    relationships: tuple[Relationship, ...],
) -> Section:
    """Build Relationships from the given Relationship tuple as-is."""
    items = tuple(
        f"{relationship.relationship_type} → "
        f"{relationship.target_type}:{relationship.target_id}"
        for relationship in relationships
    )
    return Section(heading="Relationships", content=(BulletList(items),))


def _view_label(view: Mapping[str, object]) -> str:
    """Return the view title when present; otherwise ``Unnamed view``."""
    title = view.get("title")
    if isinstance(title, str) and title:
        return title
    return "Unnamed view"


def _append_if_present(items: list[str], label: str, value: str | None) -> None:
    """Append ``label: value`` when *value* is a non-empty string."""
    if value:
        items.append(f"{label}: {value}")


def _append_path_if_present(items: list[str], path: Path | None) -> None:
    """Append ``path: …`` when a dashboard path is set."""
    if path is not None:
        items.append(f"path: {path}")
