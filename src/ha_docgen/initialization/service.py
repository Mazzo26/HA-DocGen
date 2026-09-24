"""Filesystem orchestration for first-run project initialization.

Writes a default ``config.yaml`` using :class:`ConfigRenderer`.
Contains filesystem logic only; rendering stays in the renderer.
"""

from __future__ import annotations

import os
from pathlib import Path

from ..constants import DEFAULT_ENCODING
from .renderer import ConfigRenderer

CONFIG_FILE_NAME = "config.yaml"


class ConfigurationExistsError(Exception):
    """Raised when initialization would overwrite an existing configuration."""


class InitializationError(Exception):
    """Raised when configuration creation fails."""


class InitializationService:
    """Create a default configuration file for a new HA-DocGen project.

    Stateless aside from the explicit directory and renderer arguments.
    """

    def initialize(
        self,
        directory: Path,
        *,
        renderer: ConfigRenderer | None = None,
    ) -> Path:
        """Write ``config.yaml`` under *directory* and return its path.

        Raises:
            ConfigurationExistsError: when the target file already exists.
            InitializationError: when the file cannot be written.
        """
        config_path = directory / CONFIG_FILE_NAME
        if config_path.exists():
            raise ConfigurationExistsError("Configuration already exists.")
        content = (renderer or ConfigRenderer()).render()
        try:
            self._write_atomic(config_path, content)
        except OSError as exc:
            raise InitializationError(str(exc)) from exc
        return config_path

    def _write_atomic(self, path: Path, content: str) -> None:
        """Write *content* to *path* without leaving a partial target file."""
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            temporary.write_text(content, encoding=DEFAULT_ENCODING, newline="\n")
            os.replace(temporary, path)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise
