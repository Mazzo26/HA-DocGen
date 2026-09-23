"""Project a Home Assistant inventory from an AnalysisModel.

Reads packages, blueprints and parsed objects already stored on the
analysis aggregate. Performs no discovery, parsing, filesystem access
or modification of that aggregate.
"""

from __future__ import annotations

from collections.abc import Callable

from ..analysis import AnalysisModel
from ..automation import Automation
from ..blueprint import Blueprint
from ..helper import Helper
from ..registries import Label
from ..scene import Scene
from ..script import Script
from ..yaml import YamlRepository
from .home_assistant_inventory import DiscoveredFile, HomeAssistantInventory


class HomeAssistantInventoryGenerator:
    """Project ``AnalysisModel`` into an immutable inventory.

    Fully stateless: no instance state, no caching and no side effects.
    The same analysis aggregate always yields an equal inventory.
    """

    def generate(self, analysis_model: AnalysisModel) -> HomeAssistantInventory:
        """Return parsed objects and the source paths already stored."""
        repository = analysis_model.yaml_repository
        return HomeAssistantInventory(
            discovered_files=_discovered_files(repository),
            automations=_ordered(repository.automations, _automation_key),
            scripts=_ordered(repository.scripts, _script_key),
            scenes=_ordered(repository.scenes, _scene_key),
            blueprints=_ordered(repository.blueprints, _blueprint_key),
            helpers=_ordered(repository.helpers, _helper_key),
            labels=_ordered(analysis_model.home_assistant_model.labels, _label_key),
        )


def _discovered_files(repository: YamlRepository) -> tuple[DiscoveredFile, ...]:
    """Return package and blueprint paths, one entry per POSIX path."""
    files = _package_files(repository) + _blueprint_files(repository)
    return _unique_files(files)


def _package_files(repository: YamlRepository) -> tuple[DiscoveredFile, ...]:
    """Reference each package path already stored on the repository."""
    return tuple(DiscoveredFile(package.path) for package in repository.packages)


def _blueprint_files(repository: YamlRepository) -> tuple[DiscoveredFile, ...]:
    """Reference blueprint paths that the repository already stores."""
    return tuple(
        DiscoveredFile(blueprint.path)
        for blueprint in repository.blueprints
        if blueprint.path is not None
    )


def _unique_files(files: tuple[DiscoveredFile, ...]) -> tuple[DiscoveredFile, ...]:
    """Keep the first path for each POSIX key after a stable sort."""
    unique: list[DiscoveredFile] = []
    seen: set[str] = set()
    for item in sorted(files, key=_file_key):
        key = _file_key(item)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return tuple(unique)


def _file_key(item: DiscoveredFile) -> str:
    """Return the POSIX path already stored on the file."""
    return item.path.as_posix()


def _ordered[Item](
    items: tuple[Item, ...],
    key: Callable[[Item], tuple[object, ...]],
) -> tuple[Item, ...]:
    """Return the original objects in deterministic order."""
    return tuple(sorted(items, key=key))


def _automation_key(automation: Automation) -> tuple[bool, str, bool, str, str, str]:
    """Sort automations by id, alias, package name and package path."""
    return (
        automation.id is None,
        automation.id or "",
        automation.alias is None,
        automation.alias or "",
        automation.package.name,
        automation.package.path.as_posix(),
    )


def _script_key(script: Script) -> tuple[bool, str, bool, str, str, str]:
    """Sort scripts by id, alias, package name and package path."""
    return (
        script.id is None,
        script.id or "",
        script.alias is None,
        script.alias or "",
        script.package.name,
        script.package.path.as_posix(),
    )


def _scene_key(scene: Scene) -> tuple[bool, str, bool, str, str, str]:
    """Sort scenes by id, name, package name and package path."""
    return (
        scene.id is None,
        scene.id or "",
        scene.name is None,
        scene.name or "",
        scene.package.name,
        scene.package.path.as_posix(),
    )


def _blueprint_key(blueprint: Blueprint) -> tuple[bool, str, bool, str, bool, str]:
    """Sort blueprints by path, name and domain. Missing paths sort last."""
    path = "" if blueprint.path is None else blueprint.path.as_posix()
    return (
        blueprint.path is None,
        path,
        blueprint.name is None,
        blueprint.name or "",
        blueprint.domain is None,
        blueprint.domain or "",
    )


def _helper_key(helper: Helper) -> tuple[str, str, str, str]:
    """Sort helpers by type, id, package name and package path."""
    return (
        helper.type,
        helper.id,
        helper.package.name,
        helper.package.path.as_posix(),
    )


def _label_key(label: Label) -> tuple[str, str]:
    """Sort labels by registry id and name."""
    return (label.registry_id, label.name)
