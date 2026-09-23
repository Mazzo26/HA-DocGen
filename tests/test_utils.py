"""Unit tests for generic filesystem utility functions."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from tools.ha_docgen.utils import (
    count_files,
    create_directory,
    directory_exists,
    file_exists,
    find_files,
    find_json_files,
    find_python_files,
    find_yaml_files,
    read_json,
    read_text,
    read_yaml,
    write_json,
    write_text,
    write_yaml,
)


def test_path_predicates_distinguish_files_directories_and_missing_paths(
    tmp_path: Path,
) -> None:
    file_path = tmp_path / "item.txt"
    directory = tmp_path / "directory"
    file_path.write_text("content", encoding="utf-8")
    directory.mkdir()

    assert file_exists(file_path) is True
    assert file_exists(directory) is False
    assert directory_exists(directory) is True
    assert directory_exists(file_path) is False
    assert file_exists(tmp_path / "missing") is False
    assert directory_exists(tmp_path / "missing") is False


def test_create_directory_creates_parents_and_is_idempotent(tmp_path: Path) -> None:
    directory = tmp_path / "nested" / "output"

    create_directory(directory)
    create_directory(directory)

    assert directory.is_dir()


def test_text_round_trip_preserves_unicode(tmp_path: Path) -> None:
    path = tmp_path / "unicode.txt"

    write_text(path, "café — temperatuur")

    assert read_text(path) == "café — temperatuur"


def test_yaml_round_trip_preserves_data_and_key_order(tmp_path: Path) -> None:
    path = tmp_path / "data.yaml"
    data = {"second": "café", "first": [1, 2]}

    write_yaml(path, data)

    assert read_yaml(path) == data
    assert path.read_text(encoding="utf-8").splitlines()[0] == "second: café"


def test_json_round_trip_is_unicode_friendly_and_indented(tmp_path: Path) -> None:
    path = tmp_path / "data.json"
    data = {"label": "café", "enabled": True}

    write_json(path, data)

    assert read_json(path) == data
    text = path.read_text(encoding="utf-8")
    assert '"label": "café"' in text
    assert "\n  " in text


@pytest.mark.parametrize(
    ("name", "reader", "error"),
    (
        ("invalid.yaml", read_yaml, yaml.YAMLError),
        ("invalid.json", read_json, json.JSONDecodeError),
    ),
)
def test_structured_readers_propagate_parse_errors(
    tmp_path: Path,
    name: str,
    reader: Callable[[Path], object],
    error: type[Exception],
) -> None:
    path = tmp_path / name
    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(error):
        reader(path)


def test_find_files_is_recursive_and_deterministically_sorted(tmp_path: Path) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    second = nested / "b.txt"
    first = tmp_path / "a.txt"
    ignored = nested / "c.yaml"
    for path in (second, first, ignored):
        path.write_text("", encoding="utf-8")

    assert find_files(tmp_path, "*.txt") == sorted((first, second))
    assert count_files(tmp_path, "*.txt") == 2


def test_extension_specific_finders_return_only_matching_files(tmp_path: Path) -> None:
    paths = {
        "yaml": tmp_path / "config.yaml",
        "yml": tmp_path / "excluded.yml",
        "json": tmp_path / "data.json",
        "python": tmp_path / "module.py",
        "text": tmp_path / "notes.txt",
    }
    for path in paths.values():
        path.write_text("", encoding="utf-8")

    assert find_yaml_files(tmp_path) == [paths["yaml"]]
    assert find_json_files(tmp_path) == [paths["json"]]
    assert find_python_files(tmp_path) == [paths["python"]]
