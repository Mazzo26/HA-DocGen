"""Scanner diagnostics are a pure derivation over an existing ProjectTree."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ha_docgen.policy import ScanPolicy
from ha_docgen.project import (
    ProjectFile,
    ProjectTree,
    discover_project,
    project_files,
    root_yaml_files,
)
from ha_docgen.project.builder import ProjectTreeBuilder
from ha_docgen.project.filesystem_entry import FilesystemEntry
from ha_docgen.project.walker import FilesystemWalker
from ha_docgen.scanners import (
    DiagnosticType,
    ScannerDiagnostic,
    ScannerDiagnostics,
    YamlLoadFailure,
    scanner_diagnostics,
)
from ha_docgen.scanners.filesystem import FilesystemScanner
from ha_docgen.yaml import (
    IncludeDirective,
    IncludeNode,
    YamlDocument,
    YamlLoader,
    YamlLoadError,
    resolve_includes,
)
from tests.support import write_text_files

pytestmark = pytest.mark.unit

_MODIFIED = datetime(2026, 1, 1, tzinfo=UTC)


def test_yaml_load_failures_keep_the_supplied_file_and_message() -> None:
    """A supplied failure is recorded without loading or replacing the file."""
    tree = _tree()
    target = _stored(tree, "configuration.yaml")
    failure = YamlLoadFailure(target, "Failed to parse YAML file: configuration.yaml")

    found = _of_type(
        scanner_diagnostics(tree, load_failures=(failure,)),
        DiagnosticType.YAML_LOAD_FAILURE,
    )

    assert found == (
        ScannerDiagnostic(DiagnosticType.YAML_LOAD_FAILURE, target, failure.message),
    )
    assert found[0].project_file is target


def test_yaml_loader_still_raises_on_invalid_yaml(tmp_path: Path) -> None:
    """YamlLoader keeps its exception contract; diagnostics only store supplied text."""
    path = tmp_path / "broken.yaml"
    path.write_text(":\n  - [", encoding="utf-8")
    tree = _tree()
    stored = _stored(tree, "broken.yaml")

    with pytest.raises(YamlLoadError, match="Failed to parse YAML"):
        YamlLoader().load(path)

    failure = YamlLoadFailure(stored, "Failed to parse YAML file: broken.yaml")
    found = _of_type(
        scanner_diagnostics(tree, load_failures=(failure,)),
        DiagnosticType.YAML_LOAD_FAILURE,
    )
    assert found[0].project_file is stored
    assert found[0].message == failure.message


def test_yaml_load_failures_are_ordered_by_path_then_message() -> None:
    """Failures sort by relative path and message, and repeated facts collapse."""
    tree = _tree()
    first = _stored(tree, "packages/lighting.yaml")
    second = _stored(tree, "configuration.yaml")
    failures = (
        YamlLoadFailure(first, "beta"),
        YamlLoadFailure(second, "zeta"),
        YamlLoadFailure(second, "alpha"),
        YamlLoadFailure(second, "alpha"),
    )

    found = _of_type(
        scanner_diagnostics(tree, load_failures=failures),
        DiagnosticType.YAML_LOAD_FAILURE,
    )

    assert [(item.project_file, item.message) for item in found] == [
        (second, "alpha"),
        (second, "zeta"),
        (first, "beta"),
    ]


def test_unclaimed_files_use_only_the_supplied_instances() -> None:
    """Ownership is identity in the claim set, including lookalike files."""
    tree = _tree()
    claimed = _stored(tree, "configuration.yaml")
    lookalike = replace(claimed)
    result = scanner_diagnostics(tree, claim_set=(claimed, lookalike))
    unclaimed = _of_type(result, DiagnosticType.UNCLAIMED_FILE)

    assert lookalike is not claimed
    assert _paths(unclaimed) == (
        "README.md",
        "broken.yaml",
        "dashboards/main.yaml",
        "nested/deeper/item.yaml",
        "nested/extra.yaml",
        "packages/lighting.yaml",
    )
    assert all(item.project_file is _stored(tree, _path(item)) for item in unclaimed)
    assert claimed not in tuple(item.project_file for item in unclaimed)


def test_empty_claim_set_leaves_every_stored_file_unclaimed() -> None:
    """An empty claim set claims nothing and does not classify directories."""
    tree = _tree()
    unclaimed = _of_type(scanner_diagnostics(tree), DiagnosticType.UNCLAIMED_FILE)

    assert _paths(unclaimed) == _paths(_inventory(scanner_diagnostics(tree)))


def test_repository_inventory_is_the_stored_project_files() -> None:
    """Inventory references project_files() and copies no file metadata."""
    tree = _tree()
    stored = project_files(tree)
    inventory = _inventory(scanner_diagnostics(tree, claim_set=stored))

    assert tuple(item.project_file for item in inventory) == stored
    assert all(
        record.project_file is original
        for record, original in zip(inventory, stored, strict=True)
    )
    assert [item.diagnostic_type for item in inventory] == (
        [DiagnosticType.REPOSITORY_INVENTORY] * len(stored)
    )
    assert {field for item in inventory for field in item.__slots__} == {
        "diagnostic_type",
        "project_file",
        "message",
    }


def test_diagnostics_are_deterministic_and_frozen() -> None:
    """The same inputs produce equal frozen results, in type, path, message order."""
    tree = _tree()
    claimed = _stored(tree, "README.md")
    failure = YamlLoadFailure(_stored(tree, "packages/lighting.yaml"), "parse")
    first = scanner_diagnostics(tree, (claimed,), (failure,))
    second = scanner_diagnostics(tree, (claimed,), (failure,))

    assert first == second
    assert first is not second
    assert _order_keys(first) == tuple(sorted(_order_keys(first)))
    with pytest.raises(FrozenInstanceError):
        first.diagnostics = ()  # type: ignore[misc]


def test_diagnostics_do_not_discover_or_load_files(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generation reads the supplied tree and does not walk, open or parse."""
    tree = _tree()
    failure = YamlLoadFailure(_stored(tree, "configuration.yaml"), "read")
    _reject_discovery(monkeypatch)

    result = scanner_diagnostics(tree, claim_set=(), load_failures=(failure,))

    assert _paths(_inventory(result)) == _names(project_files(tree))
    assert len(_of_type(result, DiagnosticType.YAML_LOAD_FAILURE)) == 1


def test_existing_queries_and_scanner_stay_unchanged() -> None:
    """Diagnostics leave ProjectTree, root YAML, includes and filesystem counts intact."""
    tree = _tree()
    document = _include_document()
    before_files = project_files(tree)
    before_root = root_yaml_files(tree)
    before_includes = resolve_includes(tree, document)
    before_scan = FilesystemScanner(tree.root, ScanPolicy()).scan(tree=tree)

    scanner_diagnostics(
        tree,
        claim_set=before_files[:1],
        load_failures=(YamlLoadFailure(before_files[0], "load"),),
    )

    assert project_files(tree) == before_files
    assert all(left is right for left, right in zip(project_files(tree), before_files, strict=True))
    assert root_yaml_files(tree) == before_root
    assert resolve_includes(tree, document) == before_includes
    assert FilesystemScanner(tree.root, ScanPolicy()).scan(tree=tree) == before_scan


def test_discover_project_stays_independent(tmp_path: Path) -> None:
    """A later diagnostic pass does not change a completed discovery result."""
    write_text_files(tmp_path, {"configuration.yaml": "homeassistant:\n"})
    discovered = discover_project(tmp_path, ScanPolicy())
    paths = _names(project_files(discovered))

    scanner_diagnostics(discovered)

    again = discover_project(tmp_path, ScanPolicy())
    assert _names(project_files(again)) == paths
    assert _names(project_files(discovered)) == paths


def _tree() -> ProjectTree:
    """Build a repository tree without reading or writing the filesystem."""
    root = Path("repository")
    relatives = (
        "README.md",
        "configuration.yaml",
        "broken.yaml",
        "packages",
        "packages/lighting.yaml",
        "dashboards",
        "dashboards/main.yaml",
        "nested",
        "nested/extra.yaml",
        "nested/deeper",
        "nested/deeper/item.yaml",
    )
    directories = {"packages", "dashboards", "nested", "nested/deeper"}
    entries = [_entry(root, relative, relative in directories) for relative in relatives]
    return ProjectTreeBuilder().build(root, entries)


def _entry(root: Path, relative: str, is_dir: bool) -> FilesystemEntry:
    """Build one filesystem entry from stored metadata only."""
    path = root / relative
    return FilesystemEntry(
        path=path,
        relative_path=Path(relative),
        name=path.name,
        is_file=not is_dir,
        is_dir=is_dir,
        extension="" if is_dir else path.suffix.lower(),
        size=0 if is_dir else 1,
        modified=_MODIFIED,
    )


def _include_document() -> YamlDocument:
    """Return one document that points at a file already stored in the tree."""
    node = IncludeNode(IncludeDirective.INCLUDE, "packages/lighting.yaml")
    return YamlDocument(
        Path("repository/configuration.yaml"),
        "automation: !include\n",
        {"automation": node},
    )


def _stored(tree: ProjectTree, relative: str) -> ProjectFile:
    """Return the stored ProjectFile for one relative POSIX path."""
    return next(item for item in project_files(tree) if item.relative_path.as_posix() == relative)


def _inventory(result: ScannerDiagnostics) -> tuple[ScannerDiagnostic, ...]:
    """Return the repository-inventory facts."""
    return _of_type(result, DiagnosticType.REPOSITORY_INVENTORY)


def _of_type(
    result: ScannerDiagnostics,
    diagnostic_type: DiagnosticType,
) -> tuple[ScannerDiagnostic, ...]:
    """Return facts of one type, preserving collection order."""
    return tuple(item for item in result.diagnostics if item.diagnostic_type is diagnostic_type)


def _paths(records: tuple[ScannerDiagnostic, ...]) -> tuple[str, ...]:
    """Return relative POSIX paths for diagnostic records."""
    return tuple(_path(item) for item in records)


def _path(record: ScannerDiagnostic) -> str:
    """Return the relative POSIX path referenced by one record."""
    return record.project_file.relative_path.as_posix()


def _order_keys(result: ScannerDiagnostics) -> tuple[tuple[str, str, str], ...]:
    """Return the public sort key of each diagnostic."""
    return tuple(
        (item.diagnostic_type.value, _path(item), item.message) for item in result.diagnostics
    )


def _names(files: tuple[ProjectFile, ...]) -> tuple[str, ...]:
    """Return relative POSIX paths for stored files."""
    return tuple(item.relative_path.as_posix() for item in files)


def _reject_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail when code discovers, stats, opens or loads a file."""

    def rejected(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("scanner diagnostics touched discovery or YAML loading")

    names = (
        "exists",
        "is_file",
        "is_dir",
        "stat",
        "lstat",
        "rglob",
        "iterdir",
        "open",
        "read_text",
        "read_bytes",
    )
    for name in names:
        monkeypatch.setattr(Path, name, rejected)
    monkeypatch.setattr(FilesystemWalker, "walk", rejected)
    monkeypatch.setattr("ha_docgen.project.discovery.discover_project", rejected)
    monkeypatch.setattr(YamlLoader, "load", rejected)
