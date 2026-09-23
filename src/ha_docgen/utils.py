"""
HA-DocGen - Utility functies

Deze module bevat uitsluitend generieke hulpfuncties.
Er mag geen Home Assistant specifieke logica in voorkomen.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .constants import (
    DEFAULT_ENCODING,
    GLOB_JSON,
    GLOB_PYTHON,
    GLOB_YAML,
)


# ==========================================================
# Bestand functies
# ==========================================================

def file_exists(path: Path) -> bool:
    """Controleer of een bestand bestaat."""
    return path.is_file()


def directory_exists(path: Path) -> bool:
    """Controleer of een map bestaat."""
    return path.is_dir()


def create_directory(path: Path) -> None:
    """Maak een map aan indien deze nog niet bestaat."""
    path.mkdir(parents=True, exist_ok=True)


# ==========================================================
# Tekst
# ==========================================================

def read_text(path: Path) -> str:
    """Lees een tekstbestand."""
    return path.read_text(encoding=DEFAULT_ENCODING)


def write_text(path: Path, text: str) -> None:
    """Schrijf tekst naar een bestand."""
    path.write_text(text, encoding=DEFAULT_ENCODING)


# ==========================================================
# YAML
# ==========================================================

def read_yaml(path: Path) -> dict[str, Any]:
    """Lees een YAML-bestand."""
    with path.open("r", encoding=DEFAULT_ENCODING) as file:
        return yaml.safe_load(file)


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    """Schrijf een YAML-bestand."""
    with path.open("w", encoding=DEFAULT_ENCODING) as file:
        yaml.safe_dump(
            data,
            file,
            allow_unicode=True,
            sort_keys=False,
        )


# ==========================================================
# JSON
# ==========================================================

def read_json(path: Path) -> Any:
    """Lees een JSON-bestand."""
    with path.open("r", encoding=DEFAULT_ENCODING) as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> None:
    """Schrijf een JSON-bestand."""
    with path.open("w", encoding=DEFAULT_ENCODING) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


# ==========================================================
# Zoeken
# ==========================================================

def find_files(root: Path, pattern: str) -> list[Path]:
    """Zoek bestanden met een glob-patroon."""
    return sorted(root.rglob(pattern))


def find_yaml_files(root: Path) -> list[Path]:
    """Zoek alle YAML-bestanden."""
    return find_files(root, GLOB_YAML)


def find_json_files(root: Path) -> list[Path]:
    """Zoek alle JSON-bestanden."""
    return find_files(root, GLOB_JSON)


def find_python_files(root: Path) -> list[Path]:
    """Zoek alle Python-bestanden."""
    return find_files(root, GLOB_PYTHON)


# ==========================================================
# Statistieken
# ==========================================================

def count_files(root: Path, pattern: str) -> int:
    """Tel bestanden op basis van een patroon."""
    return len(find_files(root, pattern))