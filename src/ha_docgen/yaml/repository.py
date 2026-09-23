"""Central read-only YAML domain model repository.

Holds parsed YAML domain objects and provides O(1) lookups.
Performs no parsing, analysis or relationship assembly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from ..automation.models import Automation
from ..blueprint.models import Blueprint
from ..dashboard.models import Dashboard
from ..esphome.models import ESPHomeDevice
from ..helper.models import Helper
from ..packages.models import Package, PackageStructure
from ..scene.models import Scene
from ..script.models import Script
from ..template.models import Template


@dataclass(frozen=True, slots=True)
class YamlRepository:
    """Immutable aggregate of Home Assistant YAML domain objects.

    Accepts only already-parsed domain objects. Lookups return
    ``None`` when an identifier is unknown — never raise.
    """

    packages: tuple[Package, ...] = ()
    package_structures: tuple[PackageStructure, ...] = ()
    automations: tuple[Automation, ...] = ()
    scripts: tuple[Script, ...] = ()
    scenes: tuple[Scene, ...] = ()
    helpers: tuple[Helper, ...] = ()
    dashboards: tuple[Dashboard, ...] = ()
    blueprints: tuple[Blueprint, ...] = ()
    templates: tuple[Template, ...] = ()
    esphome_devices: tuple[ESPHomeDevice, ...] = ()

    _package_index: Mapping[str, Package] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _package_structure_index: Mapping[str, PackageStructure] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _automation_index: Mapping[str, Automation] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _script_index: Mapping[str, Script] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _scene_index: Mapping[str, Scene] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _helper_index: Mapping[str, Helper] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _dashboard_index: Mapping[str, Dashboard] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _blueprint_index: Mapping[str, Blueprint] = field(
        init=False,
        repr=False,
        compare=False,
    )
    _esphome_device_index: Mapping[str, ESPHomeDevice] = field(
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        """Freeze collections and build immutable O(1) lookup indexes."""
        self._freeze_collections()
        self._order_esphome_devices()
        self._build_indexes()

    def _freeze_collections(self) -> None:
        """Ensure every public collection is stored as a tuple."""
        for name in (
            "packages",
            "package_structures",
            "automations",
            "scripts",
            "scenes",
            "helpers",
            "dashboards",
            "blueprints",
            "templates",
            "esphome_devices",
        ):
            object.__setattr__(self, name, tuple(getattr(self, name)))

    def _order_esphome_devices(self) -> None:
        """Store ESPHome devices by name, then source path."""
        object.__setattr__(
            self,
            "esphome_devices",
            tuple(sorted(self.esphome_devices, key=_esphome_device_key)),
        )

    def _build_indexes(self) -> None:
        """Populate MappingProxyType indexes for identifiable collections."""
        for name, mapping in self._index_mappings().items():
            object.__setattr__(self, name, MappingProxyType(mapping))

    def _index_mappings(self) -> dict[str, dict[str, object]]:
        """Return identifier indexes for collections that have stable keys."""
        return {
            "_package_index": {p.name: p for p in self.packages},
            "_package_structure_index": {
                ps.package.name: ps for ps in self.package_structures
            },
            "_automation_index": {
                a.id: a for a in self.automations if a.id is not None
            },
            "_script_index": {
                s.id: s for s in self.scripts if s.id is not None
            },
            "_scene_index": {
                sc.id: sc for sc in self.scenes if sc.id is not None
            },
            "_helper_index": {h.id: h for h in self.helpers},
            "_dashboard_index": {
                d.id: d for d in self.dashboards if d.id is not None
            },
            "_blueprint_index": {
                str(b.path): b for b in self.blueprints if b.path is not None
            },
            "_esphome_device_index": {
                device.name: device
                for device in self.esphome_devices
                if device.name is not None
            },
        }

    def get_package(self, name: str) -> Package | None:
        """Return the package with the given name, if present."""
        return self._package_index.get(name)

    def get_package_structure(self, name: str) -> PackageStructure | None:
        """Return the package structure for the given package name."""
        return self._package_structure_index.get(name)

    def get_automation(self, automation_id: str) -> Automation | None:
        """Return the automation with the given id, if present."""
        return self._automation_index.get(automation_id)

    def get_script(self, script_id: str) -> Script | None:
        """Return the script with the given id, if present."""
        return self._script_index.get(script_id)

    def get_scene(self, scene_id: str) -> Scene | None:
        """Return the scene with the given id, if present."""
        return self._scene_index.get(scene_id)

    def get_helper(self, helper_id: str) -> Helper | None:
        """Return the helper with the given YAML mapping key, if present."""
        return self._helper_index.get(helper_id)

    def get_dashboard(self, dashboard_id: str) -> Dashboard | None:
        """Return the dashboard with the given id, if present."""
        return self._dashboard_index.get(dashboard_id)

    def get_blueprint(self, path: str) -> Blueprint | None:
        """Return the blueprint with the given source path, if present."""
        return self._blueprint_index.get(path)

    def get_esphome_device(self, name: str) -> ESPHomeDevice | None:
        """Return the ESPHome device with the given name, if present."""
        return self._esphome_device_index.get(name)


def _esphome_device_key(device: ESPHomeDevice) -> tuple[bool, str, str]:
    """Sort named devices first, then by name and POSIX path."""
    path = "" if device.path is None else device.path.as_posix()
    return (device.name is None, device.name or "", path)
