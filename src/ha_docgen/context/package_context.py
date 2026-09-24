"""Project package context from an AnalysisModel.

Maps packages already stored on the YAML aggregate. Members are domain
objects that already reference that package. Dashboards have no package
reference, so they are not members. Resolves entities, scripts, scenes
and dashboards only through existing relationships. Missing targets
stay unresolved ids.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import NamedTuple, Protocol, TypeVar

from ..analysis import AnalysisModel
from ..automation import Automation
from ..dashboard.models import Dashboard
from ..helper.models import Helper
from ..packages import Package
from ..registries.models import Entity
from ..relationships import ObjectType, Relationship, RelationshipRepository
from ..scene import Scene
from ..script import Script
from ..template.models import Template
from ..yaml import YamlRepository
from .models import PackageContext, _package_context_key
from .ordering import relationship_sort_key

_Resolved = TypeVar("_Resolved")

_RELATED = (
    ObjectType.ENTITY,
    ObjectType.SCRIPT,
    ObjectType.SCENE,
    ObjectType.DASHBOARD,
)


class _HasPackage(Protocol):
    """Domain object that already stores package provenance."""

    package: Package


_Member = TypeVar("_Member", bound=_HasPackage)


class _Members(NamedTuple):
    """Package members selected from the YAML aggregate."""

    automations: tuple[Automation, ...]
    scripts: tuple[Script, ...]
    scenes: tuple[Scene, ...]
    helpers: tuple[Helper, ...]
    templates: tuple[Template, ...]


class _References(NamedTuple):
    """Resolved relationship targets and the ids that did not resolve."""

    entities: tuple[Entity, ...]
    missing_entities: tuple[str, ...]
    scripts: tuple[Script, ...]
    missing_scripts: tuple[str, ...]
    scenes: tuple[Scene, ...]
    missing_scenes: tuple[str, ...]
    dashboards: tuple[Dashboard, ...]
    missing_dashboards: tuple[str, ...]


def project_package_contexts(analysis: AnalysisModel) -> tuple[PackageContext, ...]:
    """Return one context per package, ordered by identity."""
    contexts = tuple(
        _project_package(package, analysis) for package in analysis.yaml_repository.packages
    )
    return tuple(sorted(contexts, key=_package_context_key))


def _project_package(package: Package, analysis: AnalysisModel) -> PackageContext:
    """Project one package without copying its YAML object."""
    relationships = _relationships(analysis.relationship_repository, package.name)
    return _assemble(package, analysis, relationships)


def _relationships(
    repository: RelationshipRepository,
    name: str,
) -> tuple[Relationship, ...]:
    """Return unique entity, script, scene and dashboard edges for this package."""
    combined = (
        *repository.by_source(ObjectType.PACKAGE, name),
        *repository.by_target(ObjectType.PACKAGE, name),
    )
    selected = [item for item in combined if _is_related(item, name)]
    return tuple(sorted(set(selected), key=relationship_sort_key))


def _is_related(relationship: Relationship, name: str) -> bool:
    """Return True when the other endpoint is a referenced object type."""
    return _other_endpoint(relationship, name)[0] in _RELATED


def _other_endpoint(
    relationship: Relationship,
    name: str,
) -> tuple[ObjectType, str]:
    """Return the endpoint that is not this package."""
    if _outgoing(relationship, name):
        return (relationship.target_type, relationship.target_id)
    return (relationship.source_type, relationship.source_id)


def _outgoing(relationship: Relationship, name: str) -> bool:
    """Return True when this package is the relationship source."""
    return relationship.source_type is ObjectType.PACKAGE and relationship.source_id == name


def _assemble(
    package: Package,
    analysis: AnalysisModel,
    relationships: tuple[Relationship, ...],
) -> PackageContext:
    """Build one package context from stored members and relationships."""
    members = _members(analysis.yaml_repository, package)
    references = _references(analysis, relationships, package.name)
    return PackageContext(
        package=package,
        automations=members.automations,
        scripts=members.scripts,
        scenes=members.scenes,
        helpers=members.helpers,
        templates=members.templates,
        dashboards=(),
        relationships=relationships,
        referenced_entities=references.entities,
        unresolved_entity_ids=references.missing_entities,
        referenced_scripts=references.scripts,
        unresolved_script_ids=references.missing_scripts,
        referenced_scenes=references.scenes,
        unresolved_scene_ids=references.missing_scenes,
        referenced_dashboards=references.dashboards,
        unresolved_dashboard_ids=references.missing_dashboards,
    )


def _members(repository: YamlRepository, package: Package) -> _Members:
    """Return domain objects that already reference this package."""
    return _Members(
        automations=_owned(repository.automations, package, _automation_key),
        scripts=_owned(repository.scripts, package, _script_key),
        scenes=_owned(repository.scenes, package, _scene_key),
        helpers=_owned(repository.helpers, package, _helper_key),
        templates=_owned(repository.templates, package, _template_key),
    )


def _owned(  # noqa: UP047
    items: Sequence[_Member],
    package: Package,
    key: Callable[[_Member], tuple[str, ...]],
) -> tuple[_Member, ...]:
    """Return objects whose package reference is *package*, ordered by identity."""
    selected = [item for item in items if item.package is package]
    return tuple(sorted(selected, key=key))


def _references(
    analysis: AnalysisModel,
    relationships: tuple[Relationship, ...],
    name: str,
) -> _References:
    """Resolve referenced endpoints into objects and unresolved ids."""
    repository = analysis.yaml_repository
    return _References(
        *_lookup(relationships, name, ObjectType.ENTITY, analysis.home_assistant_model.get_entity),
        *_lookup(relationships, name, ObjectType.SCRIPT, repository.get_script),
        *_lookup(relationships, name, ObjectType.SCENE, repository.get_scene),
        *_lookup(relationships, name, ObjectType.DASHBOARD, repository.get_dashboard),
    )


def _lookup(  # noqa: UP047
    relationships: tuple[Relationship, ...],
    name: str,
    object_type: ObjectType,
    resolve: Callable[[str], _Resolved | None],
) -> tuple[tuple[_Resolved, ...], tuple[str, ...]]:
    """Resolve one endpoint type through an existing repository lookup."""
    return _resolve(_identifiers(relationships, name, object_type), resolve)


def _identifiers(
    relationships: tuple[Relationship, ...],
    name: str,
    object_type: ObjectType,
) -> tuple[str, ...]:
    """Return sorted unique ids of *object_type* linked to this package."""
    found = {
        endpoint[1]
        for relationship in relationships
        if (endpoint := _other_endpoint(relationship, name))[0] is object_type
    }
    return tuple(sorted(found))


def _resolve(  # noqa: UP047
    identifiers: tuple[str, ...],
    resolve: Callable[[str], _Resolved | None],
) -> tuple[tuple[_Resolved, ...], tuple[str, ...]]:
    """Split ids into existing objects and unresolved ids, preserving order."""
    resolved: list[_Resolved] = []
    missing: list[str] = []
    for identifier in identifiers:
        item = resolve(identifier)
        if item is None:
            missing.append(identifier)
        else:
            resolved.append(item)
    return tuple(resolved), tuple(missing)


def _automation_key(automation: Automation) -> tuple[str, ...]:
    """Sort automations by id and alias."""
    return (automation.id or "", automation.alias or "")


def _script_key(script: Script) -> tuple[str, ...]:
    """Sort scripts by id and alias."""
    return (script.id or "", script.alias or "")


def _scene_key(scene: Scene) -> tuple[str, ...]:
    """Sort scenes by id and name."""
    return (scene.id or "", scene.name or "")


def _helper_key(helper: Helper) -> tuple[str, ...]:
    """Sort helpers by type and id."""
    return (helper.type, helper.id)


def _template_key(template: Template) -> tuple[str, ...]:
    """Sort templates by kind, source and path."""
    path = "" if template.path is None else template.path.as_posix()
    return (template.kind, template.source, path)
