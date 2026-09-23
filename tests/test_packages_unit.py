"""Unit tests for package models, scanning, and structural parsing."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType

import pytest

from ha_docgen.packages import (
    Package,
    PackageParser,
    PackageScanner,
    PackageStructure,
    Section,
)
from tests.support import PackageBuilder
from ha_docgen.yaml import YamlDocument, YamlLoader

pytestmark = pytest.mark.unit


def test_package_model_preserves_document_provenance() -> None:
    """Package identity and document source refer to the configured path."""
    path = Path("packages") / "lighting.yaml"
    package = PackageBuilder("lighting").with_path(path).build()

    assert package.name == "lighting"
    assert package.path == path
    assert package.document.path == path


def test_package_model_is_frozen() -> None:
    """Package rejects field reassignment."""
    package = PackageBuilder().build()

    with pytest.raises(FrozenInstanceError):
        package.name = "changed"  # type: ignore[misc]


def test_scanner_loads_yaml_recursively_in_deterministic_order(
    tmp_path: Path,
) -> None:
    """Scanning includes both YAML suffixes and sorts paths recursively."""
    packages = tmp_path / "packages"
    nested = packages / "nested"
    nested.mkdir(parents=True)
    (packages / "z.yaml").write_text("name: z\n", encoding="utf-8")
    (nested / "a.YML").write_text("name: a\n", encoding="utf-8")
    (packages / "ignored.txt").write_text("ignored", encoding="utf-8")

    documents = PackageScanner(YamlLoader()).scan(packages)

    assert tuple(document.path.relative_to(packages).as_posix() for document in documents) == (
        "nested/a.YML",
        "z.yaml",
    )
    assert tuple(document.data for document in documents) == ({"name": "a"}, {"name": "z"})


@pytest.mark.parametrize("missing_name", ["missing", "file.yaml"])
def test_scanner_returns_empty_for_missing_or_non_directory(
    tmp_path: Path,
    missing_name: str,
) -> None:
    """Absent paths and regular files contain no package documents."""
    path = tmp_path / missing_name
    if path.suffix:
        path.write_text("value: 1\n", encoding="utf-8")

    assert PackageScanner(YamlLoader()).scan(path) == ()


def test_parser_sorts_sections_and_preserves_raw_values() -> None:
    """Structural parsing is deterministic and does not interpret values."""
    automation = [{"id": "one"}]
    path = Path("packages/sample.yaml")
    package = Package(
        name="sample",
        path=path,
        document=YamlDocument(
            path=path,
            text="",
            data={"template": None, "automation": automation, 3: "numeric"},
        ),
    )

    structure = PackageParser().parse(package)

    assert tuple(section.name for section in structure.sections) == (
        "3",
        "automation",
        "template",
    )
    assert structure.get_section("automation").data == automation  # type: ignore[union-attr]


@pytest.mark.parametrize("data", [None, [], "invalid", 42])
def test_parser_returns_empty_structure_for_non_mapping_root(data: object) -> None:
    """Empty and invalid package roots contain no sections."""
    path = Path("packages/sample.yaml")
    package = Package(
        name="sample",
        path=path,
        document=YamlDocument(path=path, text="", data=data),
    )

    structure = PackageParser().parse(package)

    assert structure.package is package
    assert structure.sections == ()


def test_structure_exposes_immutable_collection_and_lookup_index() -> None:
    """Sections are tuples and the private lookup mapping is read-only."""
    package = PackageBuilder().build()
    structure = PackageStructure(
        package=package,
        sections=(Section("script", {}), Section("automation", [])),
    )

    assert isinstance(structure.sections, tuple)
    assert isinstance(structure._index, MappingProxyType)
    assert structure.has_section("script")
    assert structure.get_section("missing") is None
    with pytest.raises(TypeError):
        structure._index["new"] = Section("new", {})  # type: ignore[index]
