"""Load a single YAML file into an immutable YamlDocument.

Performs filesystem read and safe YAML parsing only. Include tags become
``IncludeNode`` values and are not opened. Domain interpretation belongs
in later modules.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from yaml.constructor import ConstructorError

from ..constants import DEFAULT_ENCODING
from .include import IncludeDirective, IncludeNode
from .models import YamlDocument


class YamlLoadError(Exception):
    """Raised when a YAML file cannot be found, read, or parsed."""


class YamlLoader:
    """Read one YAML file and return an immutable YamlDocument."""

    def load(self, path: Path) -> YamlDocument:
        """Load *path* and return path, text, and parsed data."""
        text = self._read_text(path)
        data = self._parse(text, path)
        return YamlDocument(path=path, text=text, data=data)

    def _read_text(self, path: Path) -> str:
        """Read file contents using DEFAULT_ENCODING."""
        try:
            return path.read_text(encoding=DEFAULT_ENCODING)
        except FileNotFoundError as exc:
            raise YamlLoadError(f"YAML file not found: {path}") from exc
        except OSError as exc:
            raise YamlLoadError(f"Failed to read YAML file: {path}") from exc

    def _parse(self, text: str, path: Path) -> object:
        """Parse YAML text without opening include targets."""
        try:
            return yaml.load(text, Loader=_IncludeLoader)
        except yaml.YAMLError as exc:
            raise YamlLoadError(f"Failed to parse YAML file: {path}") from exc


_INCLUDE_TAGS: dict[str, IncludeDirective] = {
    "!include": IncludeDirective.INCLUDE,
    "!include_dir_list": IncludeDirective.INCLUDE_DIR_LIST,
    "!include_dir_named": IncludeDirective.INCLUDE_DIR_NAMED,
    "!include_dir_merge_list": IncludeDirective.INCLUDE_DIR_MERGE_LIST,
    "!include_dir_merge_named": IncludeDirective.INCLUDE_DIR_MERGE_NAMED,
}


class _IncludeLoader(yaml.SafeLoader):
    """Safe loader that records include directives without reading them."""


def _attach_include_constructors() -> None:
    """Register include tags on the local safe loader."""
    for tag in _INCLUDE_TAGS:
        _IncludeLoader.add_constructor(tag, _include_constructor)


def _include_constructor(loader: yaml.SafeLoader, node: yaml.Node) -> IncludeNode:
    """Build an IncludeNode from one scalar include tag."""
    directive = _INCLUDE_TAGS[node.tag]
    return IncludeNode(directive=directive, raw_path=_include_path(loader, node))


def _include_path(loader: yaml.SafeLoader, node: yaml.Node) -> str:
    """Return the scalar path, rejecting sequences and mappings."""
    if not isinstance(node, yaml.ScalarNode):
        raise ConstructorError(
            None,
            None,
            "include directive requires a scalar path",
            node.start_mark,
        )
    return str(loader.construct_scalar(node))


_attach_include_constructors()
