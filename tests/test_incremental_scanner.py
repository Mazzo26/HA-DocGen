"""Tests for incremental scanning, hashing and project fingerprints."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from tools.ha_docgen.config import ProjectConfig
from tools.ha_docgen.incremental import (
    CacheStatus,
    FileHasher,
    IncrementalScanner,
    build_project_fingerprint,
)
from tools.ha_docgen.scanner import Scanner


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


def test_file_hasher_uses_exact_bytes(tmp_path: Path) -> None:
    """SHA-256 hashing is independent from text and platform conventions."""
    path = tmp_path / "binary"
    contents = b"one\r\ntwo\n\x00"
    path.write_bytes(contents)

    assert FileHasher().hash(path) == hashlib.sha256(contents).hexdigest()


def test_project_fingerprint_is_stable_and_tracks_relevant_configuration(
    tmp_path: Path,
) -> None:
    """Equivalent configuration hashes equally and relevant changes invalidate it."""
    config = _config(tmp_path)

    first = build_project_fingerprint(config)
    second = build_project_fingerprint(config)
    changed = build_project_fingerprint(replace(config, version="2.0"))
    external = build_project_fingerprint(
        replace(config, configuration=tmp_path.parent / "external.yaml")
    )

    assert first == second
    assert changed != first
    assert external != first


def test_incremental_scanner_handles_empty_repository(tmp_path: Path) -> None:
    """An empty first scan creates a valid cache and selects no files."""
    result = IncrementalScanner().scan(_config(tmp_path))

    assert result.files == ()
    assert result.changes.files_to_process == ()
    assert result.changes.full_scan_required is True
    assert result.cache_status is CacheStatus.MISSING


def test_incremental_scanner_first_and_identical_second_run(tmp_path: Path) -> None:
    """The first run selects all files and an identical run skips all files."""
    (tmp_path / "b.yaml").write_text("b", encoding="utf-8")
    (tmp_path / "a.yaml").write_text("a", encoding="utf-8")
    config = _config(tmp_path)
    scanner = IncrementalScanner()

    first = scanner.scan(config)
    second = scanner.scan(config)

    assert tuple(item.relative_path for item in first.files) == ("a.yaml", "b.yaml")
    assert first.changes.files_to_process == ("a.yaml", "b.yaml")
    assert second.cache_status is CacheStatus.FOUND
    assert second.changes.files_to_process == ()
    assert second.changes.skipped == ("a.yaml", "b.yaml")


def test_incremental_scanner_detects_modified_new_and_deleted_files(
    tmp_path: Path,
) -> None:
    """Only changed and new current files are selected; deletion is retained."""
    changed = tmp_path / "changed.yaml"
    deleted = tmp_path / "deleted.yaml"
    changed.write_text("old", encoding="utf-8")
    deleted.write_text("old", encoding="utf-8")
    config = _config(tmp_path)
    scanner = IncrementalScanner()
    scanner.scan(config)

    changed.write_text("new", encoding="utf-8")
    deleted.unlink()
    (tmp_path / "added.yaml").write_text("new", encoding="utf-8")
    result = scanner.scan(config)

    assert result.changes.changed == ("changed.yaml",)
    assert result.changes.added == ("added.yaml",)
    assert result.changes.deleted == ("deleted.yaml",)
    assert result.changes.files_to_process == ("added.yaml", "changed.yaml")


def test_incremental_scanner_force_and_clean_cache_require_full_scan(
    tmp_path: Path,
) -> None:
    """Force ignores valid cache and clean removes it before comparison."""
    (tmp_path / "file.yaml").write_text("value", encoding="utf-8")
    config = _config(tmp_path)
    scanner = IncrementalScanner()
    scanner.scan(config)

    forced = scanner.scan(config, force=True)
    cleaned = scanner.scan(config, clean_cache=True)

    assert forced.changes.full_scan_required is True
    assert forced.changes.files_to_process == ("file.yaml",)
    assert cleaned.cache_status is CacheStatus.MISSING
    assert cleaned.changes.full_scan_required is True


def test_incremental_scanner_replaces_corrupt_cache(tmp_path: Path) -> None:
    """Corrupt cache causes a full scan and is replaced with valid content."""
    config = _config(tmp_path)
    config.cache.parent.mkdir()
    config.cache.write_text("{", encoding="utf-8")

    first = IncrementalScanner().scan(config)
    second = IncrementalScanner().scan(config)

    assert first.cache_status is CacheStatus.CORRUPT
    assert first.changes.full_scan_required is True
    assert second.cache_status is CacheStatus.FOUND
    assert second.changes.full_scan_required is False


def test_existing_scanner_processes_only_explicit_incremental_files(
    tmp_path: Path,
) -> None:
    """An explicit selection bypasses unchanged files in existing scanners."""
    package = tmp_path / "packages/changed.yaml"
    unchanged = tmp_path / "dashboards/unchanged.yaml"
    component = tmp_path / "custom_components/example/manifest.json"
    for path in (package, unchanged, component):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("value", encoding="utf-8")
    config = _config(tmp_path)

    full = Scanner(config).scan()
    incremental = Scanner(config).scan((package,))

    assert full.scan.yaml_files == 2
    assert full.scan.json_files == 1
    assert full.scan.custom_component_count == 1
    assert incremental.scan.yaml_files == 1
    assert incremental.scan.json_files == 0
    assert incremental.scan.package_count == 1
    assert incremental.scan.dashboard_count == 0
    assert incremental.scan.custom_component_count == 0
    folders = {folder.name: folder.file_count for folder in incremental.folders}
    assert folders["Packages"] == 1
    assert folders["Dashboards"] == 0
