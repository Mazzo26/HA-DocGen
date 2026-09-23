"""Production pipeline integration reuses the existing scanner architecture."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from tools.ha_docgen._pipeline import _build_project_analysis
from tools.ha_docgen.analysis.models import AnalysisModel
from tools.ha_docgen.automation import AutomationParser
from tools.ha_docgen.blueprint.parser import BlueprintParser
from tools.ha_docgen.config import ProjectConfig
from tools.ha_docgen.document import DocumentRepository
from tools.ha_docgen.project import ProjectTree, project_files, root_yaml_files
from tools.ha_docgen.project import discovery as project_discovery
from tools.ha_docgen.project.walker import FilesystemWalker
from tools.ha_docgen.registries.label_parser import LabelRegistryParser
from tools.ha_docgen.scanners import DiagnosticType, scanner_diagnostics
from tools.ha_docgen.storage import scanner as storage_scanner
from tools.ha_docgen.tests.support import write_text_files
from tools.ha_docgen.validation import EntityValidator, ValidationRepository
from tools.ha_docgen.yaml import IncludeReference, YamlLoadError, YamlLoader, resolve_includes
import tools.ha_docgen._pipeline as pipeline
import tools.ha_docgen.project as project_api

pytestmark = pytest.mark.unit

_LABEL_REGISTRY = '{"version":1,"data":{"labels":[{"label_id":"room","name":"Room"}]}}\n'


def test_pipeline_discovers_the_repository_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One analysis walks once and does not project a second tree."""
    calls, trees = _count_discovery(monkeypatch)

    analysis = _build_project_analysis(_config(_write_repository(tmp_path)))

    assert calls == {"walk": 1, "discover": 1, "project": 0}
    assert trees == [analysis.project_tree]


def test_pipeline_reuses_root_yaml_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The pipeline stores the root YAML query result and does not load those files."""
    loaded: list[Path] = []
    captured: dict[str, object] = {}
    _spy_loader(monkeypatch, loaded)
    _spy_named(monkeypatch, pipeline, "root_yaml_files", captured)

    analysis = _build_project_analysis(_config(_write_repository(tmp_path)))

    assert captured["calls"] == [analysis.project_tree]
    assert analysis.root_yaml is captured["result"]
    assert _names(analysis.root_yaml) == (
        "automations.yaml",
        "configuration.yaml",
        "groups.yaml",
    )
    assert _names(analysis.root_yaml) == _names(root_yaml_files(analysis.project_tree))
    assert {path.name for path in loaded}.isdisjoint(_names(analysis.root_yaml))


def test_pipeline_reuses_resolve_includes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Include references are the resolver result and their targets stay unloaded."""
    loaded: list[Path] = []
    captured: dict[str, object] = {}
    _spy_loader(monkeypatch, loaded)
    _spy_named(monkeypatch, pipeline, "resolve_includes", captured)

    analysis = _build_project_analysis(_config(_write_repository(tmp_path)))

    calls = captured["calls"]
    assert isinstance(calls, list)
    assert calls
    assert all(tree is analysis.project_tree for tree, _document in calls)
    assert analysis.includes == _flattened(captured["results"])
    assert all(isinstance(item, IncludeReference) for item in analysis.includes)
    reference = analysis.includes[0]
    assert reference is _flattened(captured["results"])[0]
    assert reference.raw_path == "../groups.yaml"
    assert reference.resolved is True
    assert _names(reference.files) == ("groups.yaml",)
    assert "groups.yaml" not in {path.name for path in loaded}
    document = next(item for _tree, item in calls if item.path.name == "includes.yaml")
    assert analysis.includes == resolve_includes(analysis.project_tree, document)


def test_pipeline_reuses_scanner_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Diagnostics are the returned collection, with no authored failures."""
    captured: dict[str, object] = {}
    _spy_named(monkeypatch, pipeline, "scanner_diagnostics", captured)

    analysis = _build_project_analysis(_config(_write_repository(tmp_path)))

    assert captured["calls"] == [(analysis.project_tree,)]
    assert captured["failures"] == ()
    assert analysis.diagnostics is captured["result"]
    claimed = captured["claimed"]
    assert isinstance(claimed, tuple)
    stored = {id(item): item for item in project_files(analysis.project_tree)}
    assert {id(item) for item in claimed} <= set(stored)
    assert all(stored[id(item)] is item for item in claimed)
    assert _names(claimed) == (
        "packages/includes.yaml",
        "packages/lighting.yaml",
        "dashboards/main.yaml",
    )
    assert analysis.diagnostics == scanner_diagnostics(analysis.project_tree, claimed)
    kinds = {item.diagnostic_type for item in analysis.diagnostics.diagnostics}
    assert DiagnosticType.YAML_LOAD_FAILURE not in kinds
    unclaimed = _unclaimed_names(analysis.diagnostics.diagnostics)
    assert {"configuration.yaml", "groups.yaml", "automations.yaml"} <= unclaimed
    record = analysis.diagnostics.diagnostics[0]
    with pytest.raises(FrozenInstanceError):
        record.message = "changed"  # type: ignore[misc]


def test_pipeline_preserves_existing_analysis(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parsers, repositories, validation and AnalysisModel keep their behaviour."""
    structures: list[object] = []
    validations: list[object] = []
    _spy_parser(monkeypatch, AutomationParser, "parse", structures)
    _spy_parser(monkeypatch, EntityValidator, "validate", validations)
    _reject(monkeypatch, AnalysisModel, "__init__")
    _reject(monkeypatch, LabelRegistryParser, "parse")
    _reject(monkeypatch, BlueprintParser, "parse")

    analysis = _build_project_analysis(_config(_write_repository(tmp_path)))

    assert tuple(item.id for item in analysis.yaml_repository.automations) == ("lamp",)
    assert analysis.yaml_repository.dashboards[0].title == "Main"
    assert analysis.yaml_repository.helpers == ()
    assert analysis.yaml_repository.blueprints == ()
    assert analysis.model.labels == ()
    assert analysis.model.entities == ()
    assert {package.name for package in analysis.yaml_repository.packages} == {
        "includes",
        "lighting",
    }
    assert len(structures) == 2
    assert validations and validations[0] == analysis.model.entities
    assert isinstance(analysis.validations, ValidationRepository)
    assert isinstance(analysis.documents, DocumentRepository)
    assert analysis.documents.documents


def test_yaml_load_failure_still_aborts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A YAML load error still stops the pipeline and does not add a walk."""
    root = _write_repository(tmp_path)
    (root / "packages" / "broken.yaml").write_text(":\n  - [", encoding="utf-8")
    calls, _trees = _count_discovery(monkeypatch)

    with pytest.raises(YamlLoadError, match="Failed to parse YAML"):
        _build_project_analysis(_config(root))

    assert calls == {"walk": 1, "discover": 1, "project": 0}


def _write_repository(root: Path) -> Path:
    """Write packages, root YAML, one dashboard and files the pipeline must ignore."""
    return write_text_files(
        root,
        {
            "configuration.yaml": "homeassistant:\n  name: House\n",
            "automations.yaml": "- id: root\n  alias: Root\n",
            "groups.yaml": "group: {}\n",
            "packages/lighting.yaml": "automation:\n  - id: lamp\n    alias: Lamp\n",
            "packages/includes.yaml": "input_boolean: !include ../groups.yaml\n",
            "dashboards/main.yaml": "title: Main\nviews: []\n",
            "blueprints/automation/lamp.yaml": (
                "blueprint:\n  name: Lamp\n  domain: automation\n"
            ),
            ".storage/core.label_registry": _LABEL_REGISTRY,
        },
    )


def _config(root: Path) -> ProjectConfig:
    """Return a complete configuration for an isolated project."""
    return ProjectConfig(
        project_name="Test",
        version="1.0",
        root=root,
        configuration=root / "configuration.yaml",
        packages=root / "packages",
        dashboards=root / "dashboards",
        esphome=root / "esphome",
        docs=root / "docs",
        themes=root / "themes",
        custom_components=root / "custom_components",
        www=root / "www",
        storage=root / ".storage",
        entity_registry=root / ".storage/core.entity_registry",
        device_registry=root / ".storage/core.device_registry",
        area_registry=root / ".storage/core.area_registry",
        floor_registry=root / ".storage/core.floor_registry",
        config_entries=root / ".storage/core.config_entries",
        readme=root / "README.md",
        ai_context=root / "AI_CONTEXT.md",
        entity_map=root / "ENTITY_MAP.md",
        output_docs=root / "docs/generated",
        cache=root / ".cache/ha-docgen.json",
    )


def _count_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict[str, int], list[ProjectTree]]:
    """Count walks, discovery and explicit tree projection during one run."""
    calls = {"walk": 0, "discover": 0, "project": 0}
    trees: list[ProjectTree] = []
    _patch_walk(monkeypatch, calls)
    _patch_discover(monkeypatch, calls, trees)
    _patch_projection(monkeypatch, calls)
    return calls, trees


def _patch_walk(monkeypatch: pytest.MonkeyPatch, calls: dict[str, int]) -> None:
    """Count FilesystemWalker.walk calls."""
    original = FilesystemWalker.walk

    def counting(self: FilesystemWalker, root: Path) -> list[object]:
        calls["walk"] += 1
        return original(self, root)

    monkeypatch.setattr(FilesystemWalker, "walk", counting)


def _patch_discover(
    monkeypatch: pytest.MonkeyPatch,
    calls: dict[str, int],
    trees: list[ProjectTree],
) -> None:
    """Count discover_project calls on every binding the pipeline can reach."""
    original = project_discovery.discover_project

    def counting(root: Path, policy: object = None, walker: object = None) -> ProjectTree:
        calls["discover"] += 1
        tree = original(root, policy, walker)  # type: ignore[arg-type]
        trees.append(tree)
        return tree

    for module in (pipeline, project_discovery, project_api, storage_scanner):
        monkeypatch.setattr(module, "discover_project", counting)


def _patch_projection(monkeypatch: pytest.MonkeyPatch, calls: dict[str, int]) -> None:
    """Count project_tree_from_files calls."""
    original = project_discovery.project_tree_from_files

    def counting(root: Path, files: tuple[Path, ...]) -> ProjectTree:
        calls["project"] += 1
        return original(root, files)

    monkeypatch.setattr(project_discovery, "project_tree_from_files", counting)
    monkeypatch.setattr(project_api, "project_tree_from_files", counting)


def _spy_loader(monkeypatch: pytest.MonkeyPatch, loaded: list[Path]) -> None:
    """Record YAML paths opened by the pipeline."""
    original = YamlLoader.load

    def spy(self: YamlLoader, path: Path) -> object:
        loaded.append(path)
        return original(self, path)

    monkeypatch.setattr(YamlLoader, "load", spy)


def _spy_named(
    monkeypatch: pytest.MonkeyPatch,
    module: object,
    name: str,
    captured: dict[str, object],
) -> None:
    """Record calls to one pipeline binding and return its original result."""
    original = getattr(module, name)
    captured["calls"] = []
    captured["results"] = []

    def spy(*args: object, **kwargs: object) -> object:
        calls = captured["calls"]
        results = captured["results"]
        assert isinstance(calls, list)
        assert isinstance(results, list)
        if name == "scanner_diagnostics":
            calls.append((args[0],))
            captured["claimed"] = tuple(args[1]) if len(args) > 1 else ()
            captured["failures"] = kwargs.get("load_failures", ())
        elif name == "resolve_includes":
            calls.append((args[0], args[1]))
        else:
            calls.append(args[0])
        result = original(*args, **kwargs)
        results.append(result)
        captured["result"] = result
        return result

    monkeypatch.setattr(module, name, spy)


def _spy_parser(
    monkeypatch: pytest.MonkeyPatch,
    cls: type,
    name: str,
    calls: list[object],
) -> None:
    """Record the first argument of one existing parser or validator call."""
    original = getattr(cls, name)

    def spy(self: object, first: object, *args: object, **kwargs: object) -> object:
        calls.append(first)
        return original(self, first, *args, **kwargs)

    monkeypatch.setattr(cls, name, spy)


def _reject(monkeypatch: pytest.MonkeyPatch, cls: type, name: str) -> None:
    """Fail when a component outside this module is invoked."""

    def rejected(self: object, *args: object, **kwargs: object) -> object:
        raise AssertionError(f"unexpected call to {cls.__name__}.{name}")

    monkeypatch.setattr(cls, name, rejected)


def _flattened(results: object) -> tuple[IncludeReference, ...]:
    """Concatenate include batches recorded by the resolver spy."""
    assert isinstance(results, list)
    return tuple(item for batch in results for item in batch)


def _names(files: tuple[object, ...]) -> tuple[str, ...]:
    """Return relative or stored names in their existing order."""
    return tuple(_file_name(item) for item in files)


def _file_name(item: object) -> str:
    """Return the relative POSIX path, or the path name when relative data is absent."""
    relative = getattr(item, "relative_path", None)
    if relative is not None:
        return relative.as_posix()
    return getattr(item, "name")


def _unclaimed_names(diagnostics: tuple[object, ...]) -> set[str]:
    """Return relative paths of unclaimed-file diagnostics."""
    return {
        item.project_file.relative_path.as_posix()
        for item in diagnostics
        if getattr(item, "diagnostic_type", None) is DiagnosticType.UNCLAIMED_FILE
    }
