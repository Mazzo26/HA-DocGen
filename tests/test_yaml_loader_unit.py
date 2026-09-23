"""Unit tests for the public YAML document and loader API."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from ha_docgen.yaml import YamlDocument, YamlLoader, YamlLoadError

pytestmark = pytest.mark.unit


def test_yaml_document_is_frozen() -> None:
    """YamlDocument rejects mutation after construction."""
    document = YamlDocument(Path("sample.yaml"), "value: 1\n", {"value": 1})

    with pytest.raises(FrozenInstanceError):
        document.text = "changed"  # type: ignore[misc]


def test_loader_preserves_path_text_and_parsed_data(tmp_path: Path) -> None:
    """A valid file retains exact source provenance and parsed content."""
    path = tmp_path / "valid.yaml"
    text = "name: Kitchen\nitems:\n  - one\n  - two\n"
    path.write_text(text, encoding="utf-8")

    document = YamlLoader().load(path)

    assert document.path == path
    assert document.text == text
    assert document.data == {"name": "Kitchen", "items": ["one", "two"]}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("", None),
        ("null\n", None),
        ("[]\n", []),
        ("{}\n", {}),
        ("enabled: true\n", {"enabled": True}),
    ],
)
def test_loader_handles_minimal_and_empty_documents(
    tmp_path: Path,
    text: str,
    expected: object,
) -> None:
    """Minimal YAML values load without domain interpretation."""
    path = tmp_path / "minimal.yaml"
    path.write_text(text, encoding="utf-8")

    assert YamlLoader().load(path).data == expected


def test_loader_wraps_missing_file_error(tmp_path: Path) -> None:
    """A missing file raises the public loader exception with its cause."""
    path = tmp_path / "missing.yaml"

    with pytest.raises(YamlLoadError, match="YAML file not found") as error:
        YamlLoader().load(path)

    assert isinstance(error.value.__cause__, FileNotFoundError)


def test_loader_wraps_malformed_yaml_error(tmp_path: Path) -> None:
    """Malformed YAML raises the public loader exception with its cause."""
    path = tmp_path / "malformed.yaml"
    path.write_text("root: [unterminated\n", encoding="utf-8")

    with pytest.raises(YamlLoadError, match="Failed to parse YAML") as error:
        YamlLoader().load(path)

    assert error.value.__cause__ is not None
