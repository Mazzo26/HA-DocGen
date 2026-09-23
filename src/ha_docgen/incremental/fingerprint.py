"""Deterministic project fingerprint creation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..config import ProjectConfig
from .models import ProjectFingerprint


def build_project_fingerprint(config: ProjectConfig) -> ProjectFingerprint:
    """Hash configuration values that influence project processing."""
    payload = {
        "project_name": config.project_name,
        "version": config.version,
        "paths": sorted(_relevant_paths(config)),
    }
    serialized = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return ProjectFingerprint(hashlib.sha256(serialized.encode("utf-8")).hexdigest())


def _relevant_paths(config: ProjectConfig) -> tuple[str, ...]:
    """Return normalized configured input paths."""
    paths = (
        config.configuration,
        config.packages,
        config.dashboards,
        config.esphome,
        config.docs,
        config.themes,
        config.custom_components,
        config.www,
        config.storage,
        config.entity_registry,
        config.device_registry,
        config.area_registry,
        config.floor_registry,
        config.config_entries,
    )
    return tuple(_normalized_path(path, config.root) for path in paths)


def _normalized_path(path: Path, root: Path) -> str:
    """Return a POSIX path, relative to root whenever possible."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
