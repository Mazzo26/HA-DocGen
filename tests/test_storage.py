"""Unit tests for storage metadata, inventory and discovery."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ha_docgen.policy import IgnoreRules, ScanPolicy
from ha_docgen.project.walker import FilesystemWalker
from ha_docgen.storage import StorageFile, StorageInventory, StorageScanner
from tests.support import build_project_tree, write_text_files


def _storage_file(root: Path, name: str) -> StorageFile:
    """Build deterministic storage metadata for an isolated test root."""
    return StorageFile(
        name=name,
        path=root / ".storage" / name,
        relative_path=Path(".storage") / name,
        size=len(name),
        modified=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_storage_file_has_value_equality_and_slots(tmp_path: Path) -> None:
    """Storage metadata compares by value and has no dynamic attributes."""
    first = _storage_file(tmp_path, "core.entity_registry")
    second = _storage_file(tmp_path, "core.entity_registry")

    assert first == second
    assert not hasattr(first, "__dict__")


def test_storage_inventory_freezes_input_and_supports_queries(tmp_path: Path) -> None:
    """Inventory collections are copied to tuples and queried consistently."""
    entity = _storage_file(tmp_path, "core.entity_registry")
    device = _storage_file(tmp_path, "core.device_registry")
    source = [entity, device]

    inventory = StorageInventory(tmp_path / ".storage", source)
    source.clear()

    assert inventory.files == (entity, device)
    assert inventory.all_files() == (entity, device)
    assert tuple(inventory) == (entity, device)
    assert len(inventory) == 2
    assert inventory.get("core.entity_registry") is entity
    assert inventory.get("missing") is None
    assert inventory.has("core.device_registry") is True
    assert "core.device_registry" in inventory
    assert "missing" not in inventory
    with pytest.raises(AttributeError):
        inventory.files.append(entity)  # type: ignore[attr-defined]


def test_storage_inventory_duplicate_name_lookup_is_deterministic(
    tmp_path: Path,
) -> None:
    """When names collide, lookup consistently returns the final file."""
    first = _storage_file(tmp_path / "first", "registry")
    second = _storage_file(tmp_path / "second", "registry")

    inventory = StorageInventory(tmp_path / ".storage", (first, second))

    assert inventory.all_files() == (first, second)
    assert inventory.get("registry") is second


def test_storage_scanner_walks_only_temporary_storage_root(tmp_path: Path) -> None:
    """A direct scan discovers nested files and orders them by relative path."""
    storage_root = tmp_path / ".storage"
    write_text_files(
        storage_root,
        {
            "z_registry": "{}",
            "nested/a_registry": "{}",
        },
    )

    inventory = StorageScanner(storage_root).scan()

    assert [item.name for item in inventory] == ["a_registry", "z_registry"]
    assert [item.relative_path for item in inventory] == [
        Path(".storage/nested/a_registry"),
        Path(".storage/z_registry"),
    ]


def test_storage_scanner_returns_empty_inventory_for_missing_root(
    tmp_path: Path,
) -> None:
    """A missing storage directory is represented by an empty inventory."""
    storage_root = tmp_path / ".storage"

    inventory = StorageScanner(storage_root).scan()

    assert inventory.storage_root == storage_root
    assert inventory.all_files() == ()


def test_storage_scanner_reuses_project_tree_without_filesystem_access(
    tmp_path: Path,
) -> None:
    """Tree-based discovery filters non-storage files and preserves metadata."""
    write_text_files(
        tmp_path,
        {
            ".storage/core.entity_registry": "{}",
            ".storage/nested/registry": "{}",
            "configuration.yaml": "homeassistant:",
        },
    )
    tree = build_project_tree(tmp_path)

    inventory = StorageScanner(tmp_path / ".storage").scan_from_tree(tree)

    assert [item.relative_path for item in inventory] == [
        Path(".storage/core.entity_registry"),
        Path(".storage/nested/registry"),
    ]


def test_storage_scanner_filters_entries_with_policy(tmp_path: Path) -> None:
    """Entry-based discovery uses project scope, file type and scan policy."""
    write_text_files(
        tmp_path,
        {
            ".storage/core.entity_registry": "{}",
            ".storage/ignored": "{}",
            "outside.json": "{}",
        },
    )
    entries = FilesystemWalker().walk(tmp_path)
    policy = ScanPolicy(
        IgnoreRules(
            directories=frozenset(),
            filenames=frozenset({"ignored"}),
            filename_patterns=frozenset(),
        )
    )

    inventory = StorageScanner(tmp_path / ".storage", policy).scan_from_entries(
        entries,
        root=tmp_path,
    )

    assert [item.name for item in inventory] == ["core.entity_registry"]


def test_storage_scanner_accepts_entries_scoped_to_storage_root(
    tmp_path: Path,
) -> None:
    """Storage-scoped walker entries receive project-relative storage paths."""
    storage_root = tmp_path / ".storage"
    write_text_files(storage_root, {"nested/registry": "{}"})
    entries = FilesystemWalker().walk(storage_root)

    inventory = StorageScanner(storage_root).scan_from_entries(
        entries,
        root=storage_root,
    )

    assert inventory.all_files()[0].relative_path == Path(".storage/nested/registry")
