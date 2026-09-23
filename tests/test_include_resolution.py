"""Include directives resolve against an existing ProjectTree."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ha_docgen.project import (
    ProjectFile,
    ProjectTree,
    project_files,
    project_tree_from_files,
    root_yaml_files,
)
from ha_docgen.project.builder import ProjectTreeBuilder
from ha_docgen.project.filesystem_entry import FilesystemEntry
from ha_docgen.project.walker import FilesystemWalker
from ha_docgen.yaml import (
    IncludeDirective,
    IncludeNode,
    YamlDocument,
    YamlLoadError,
    YamlLoader,
    resolve_includes,
)

pytestmark = pytest.mark.unit

_DIRECTORY_DIRECTIVES: tuple[IncludeDirective, ...] = (
    IncludeDirective.INCLUDE_DIR_LIST,
    IncludeDirective.INCLUDE_DIR_NAMED,
    IncludeDirective.INCLUDE_DIR_MERGE_LIST,
    IncludeDirective.INCLUDE_DIR_MERGE_NAMED,
)

_INCLUDE_TAGS: tuple[tuple[str, IncludeDirective], ...] = (
    ("!include", IncludeDirective.INCLUDE),
    ("!include_dir_list", IncludeDirective.INCLUDE_DIR_LIST),
    ("!include_dir_named", IncludeDirective.INCLUDE_DIR_NAMED),
    ("!include_dir_merge_list", IncludeDirective.INCLUDE_DIR_MERGE_LIST),
    ("!include_dir_merge_named", IncludeDirective.INCLUDE_DIR_MERGE_NAMED),
)


def test_include_resolves_an_existing_file() -> None:
    """``!include`` returns the stored ProjectFile and does not copy it."""
    tree = _repository_tree()
    document = _document("configuration.yaml", _node(IncludeDirective.INCLUDE, "automations.yaml"))

    reference = resolve_includes(tree, document)[0]

    assert reference.resolved is True
    assert reference.files == (_file(tree, "automations.yaml"),)
    assert reference.files[0] is _file(tree, "automations.yaml")
    assert reference.target.name == "automations.yaml"


def test_missing_include_is_unresolved() -> None:
    """A file that is not in the ProjectTree stays an unresolved reference."""
    tree = _repository_tree()
    document = _document("configuration.yaml", _node(IncludeDirective.INCLUDE, "missing.yaml"))

    reference = resolve_includes(tree, document)[0]

    assert reference.resolved is False
    assert reference.files == ()
    assert reference.raw_path == "missing.yaml"
    assert reference.target.name == "missing.yaml"


def test_relative_include_uses_the_containing_document() -> None:
    """Relative paths join to the document directory, not the repository root."""
    tree = _repository_tree()
    document = _document(
        "packages/lighting.yaml",
        {
            "room": _node(IncludeDirective.INCLUDE, "includes/extra.yaml"),
            "shared": _node(IncludeDirective.INCLUDE, "../automations.yaml"),
        },
    )

    references = resolve_includes(tree, document)

    assert _resolved_names(references) == (
        "packages/includes/extra.yaml",
        "automations.yaml",
    )
    assert references[0].files[0] is _file(tree, "packages/includes/extra.yaml")
    assert references[1].files[0] is _file(tree, "automations.yaml")


def test_include_outside_the_repository_is_unresolved() -> None:
    """A relative path that leaves the repository is not searched elsewhere."""
    tree = _repository_tree()
    document = _document("configuration.yaml", _node(IncludeDirective.INCLUDE, "../outside.yaml"))

    reference = resolve_includes(tree, document)[0]

    assert reference.resolved is False
    assert reference.files == ()
    assert reference.target.name == "outside.yaml"


@pytest.mark.parametrize("directive", _DIRECTORY_DIRECTIVES)
def test_directory_include_resolves_direct_yaml_files(directive: IncludeDirective) -> None:
    """Directory directives return direct YAML children and ignore their contents."""
    tree = _repository_tree()
    document = _document("configuration.yaml", {"sensor": _node(directive, "sensors")})

    reference = resolve_includes(tree, document)[0]

    assert reference.directive is directive
    assert reference.resolved is True
    assert _names(reference.files) == ("sensors/a.yaml", "sensors/b.yaml", "sensors/b.yml")


def test_missing_directory_include_is_unresolved() -> None:
    """A directory that is not in the ProjectTree is unresolved."""
    tree = _repository_tree()
    document = _document(
        "configuration.yaml",
        _node(IncludeDirective.INCLUDE_DIR_LIST, "missing"),
    )

    reference = resolve_includes(tree, document)[0]

    assert reference.resolved is False
    assert reference.files == ()
    assert reference.target.name == "missing"


def test_directory_include_of_the_repository_root() -> None:
    """A directory include of '.' resolves root YAML files only."""
    tree = _repository_tree()
    document = _document("configuration.yaml", _node(IncludeDirective.INCLUDE_DIR_LIST, "."))

    reference = resolve_includes(tree, document)[0]

    assert reference.resolved is True
    assert _names(reference.files) == (
        "automations.yaml",
        "configuration.yaml",
        "scripts.yaml",
    )


def test_empty_directory_include_is_resolved_without_files() -> None:
    """A known directory with no YAML children is resolved and empty."""
    tree = _repository_tree()
    document = _document("configuration.yaml", _node(IncludeDirective.INCLUDE_DIR_NAMED, "empty"))

    reference = resolve_includes(tree, document)[0]

    assert reference.resolved is True
    assert reference.files == ()


def test_include_kind_must_match_the_stored_entry() -> None:
    """A file directive does not match a directory, or the reverse."""
    tree = _repository_tree()
    document = _document(
        "configuration.yaml",
        {
            "file": _node(IncludeDirective.INCLUDE, "sensors"),
            "directory": _node(IncludeDirective.INCLUDE_DIR_LIST, "automations.yaml"),
        },
    )

    references = resolve_includes(tree, document)

    assert [item.resolved for item in references] == [False, False]
    assert all(item.files == () for item in references)


def test_resolution_order_is_deterministic() -> None:
    """Directives keep source order and directory files keep relative-path order."""
    tree = _repository_tree()
    _folder(tree, "sensors").files.reverse()
    document = _document(
        "configuration.yaml",
        {
            "z": _node(IncludeDirective.INCLUDE, "scripts.yaml"),
            "a": [
                _node(IncludeDirective.INCLUDE, "automations.yaml"),
                _node(IncludeDirective.INCLUDE_DIR_LIST, "sensors"),
            ],
        },
    )

    references = resolve_includes(tree, document)

    assert [item.raw_path for item in references] == ["scripts.yaml", "automations.yaml", "sensors"]
    assert _names(references[2].files) == ("sensors/a.yaml", "sensors/b.yaml", "sensors/b.yml")


def test_repeated_resolution_is_identical() -> None:
    """Resolving the same document twice returns equal results."""
    tree = _repository_tree()
    document = _document(
        "configuration.yaml",
        {
            "automation": _node(IncludeDirective.INCLUDE, "automations.yaml"),
            "sensor": _node(IncludeDirective.INCLUDE_DIR_MERGE_LIST, "sensors"),
        },
    )

    first = resolve_includes(tree, document)
    second = resolve_includes(tree, document)

    assert first == second
    assert first is not second
    assert first[0].files[0] is second[0].files[0]
    assert first[1].files == second[1].files


def test_resolution_does_not_modify_the_document() -> None:
    """Parsed content stays the original object."""
    tree = _repository_tree()
    data = {"automation": _node(IncludeDirective.INCLUDE, "automations.yaml")}
    document = _document("configuration.yaml", data)

    resolve_includes(tree, document)

    assert document.data is data


def test_resolution_uses_only_the_project_tree(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolution does not discover, walk or open the repository."""
    tree = _repository_tree()
    document = _document("configuration.yaml", _node(IncludeDirective.INCLUDE, "missing.yaml"))
    _reject_filesystem(monkeypatch)

    reference = resolve_includes(tree, document)[0]

    assert reference.resolved is False
    assert reference.files == ()


def test_resolution_preserves_existing_discovery() -> None:
    """Root, package and dashboard queries stay unchanged after resolution."""
    tree = _repository_tree()
    root = root_yaml_files(tree)
    packages = _under(tree, "packages/")
    dashboards = _under(tree, "dashboards/")
    document = _document("configuration.yaml", _node(IncludeDirective.INCLUDE, "automations.yaml"))

    resolve_includes(tree, document)

    assert root_yaml_files(tree) == root
    assert _under(tree, "packages/") == packages
    assert _under(tree, "dashboards/") == dashboards
    assert packages == ("packages/includes/extra.yaml", "packages/lighting.yaml")
    assert dashboards == ("dashboards/main.yaml",)


def test_absolute_include_resolves_inside_the_tree(tmp_path: Path) -> None:
    """An absolute path matches a stored file and does not search around it."""
    configuration = tmp_path / "configuration.yaml"
    automations = tmp_path / "automations.yaml"
    configuration.write_text("automation: []\n", encoding="utf-8")
    automations.write_text("[]\n", encoding="utf-8")
    tree = project_tree_from_files(tmp_path, (configuration, automations))
    document = YamlDocument(
        configuration,
        "",
        {"automation": _node(IncludeDirective.INCLUDE, str(automations))},
    )

    reference = resolve_includes(tree, document)[0]

    assert reference.resolved is True
    assert reference.files[0].relative_path.as_posix() == "automations.yaml"


def test_loaded_include_is_not_merged_or_expanded(tmp_path: Path) -> None:
    """Loading one document keeps the include node and skips nested targets."""
    configuration = tmp_path / "configuration.yaml"
    automations = tmp_path / "automations.yaml"
    other = tmp_path / "other.yaml"
    configuration.write_text("automation: !include automations.yaml\n", encoding="utf-8")
    automations.write_text("alias: !include other.yaml\n", encoding="utf-8")
    other.write_text("name: other\n", encoding="utf-8")
    tree = project_tree_from_files(tmp_path, (configuration, automations, other))

    document = YamlLoader().load(configuration)
    references = resolve_includes(tree, document)

    assert document.text == "automation: !include automations.yaml\n"
    assert document.data == {
        "automation": IncludeNode(IncludeDirective.INCLUDE, "automations.yaml"),
    }
    assert len(references) == 1
    assert references[0].resolved is True
    assert references[0].files[0].name == "automations.yaml"


def test_loader_reads_only_the_source_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The loader does not open the path named by an include directive."""
    source = tmp_path / "configuration.yaml"
    included = tmp_path / "automations.yaml"
    source.write_text("automation: !include automations.yaml\n", encoding="utf-8")
    included.write_text("id: kitchen\n", encoding="utf-8")
    reads: list[str] = []
    original = Path.read_text

    def track(self: Path, *args: object, **kwargs: object) -> str:
        reads.append(self.name)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", track)
    document = YamlLoader().load(source)

    assert reads == ["configuration.yaml"]
    assert document.data == {
        "automation": IncludeNode(IncludeDirective.INCLUDE, "automations.yaml"),
    }


@pytest.mark.parametrize(("tag", "directive"), _INCLUDE_TAGS)
def test_loader_records_each_include_directive(
    tmp_path: Path,
    tag: str,
    directive: IncludeDirective,
) -> None:
    """Each supported tag becomes an IncludeNode and keeps the source text."""
    path = tmp_path / "configuration.yaml"
    text = f"value: {tag} target\n"
    path.write_text(text, encoding="utf-8")

    document = YamlLoader().load(path)

    assert document.text == text
    assert document.data == {"value": IncludeNode(directive, "target")}


def test_loader_keeps_a_quoted_include_path(tmp_path: Path) -> None:
    """Quotes around an include path are YAML syntax, not part of the path."""
    path = tmp_path / "configuration.yaml"
    path.write_text('automation: !include "my automations.yaml"\n', encoding="utf-8")

    document = YamlLoader().load(path)

    node = document.data["automation"]
    assert isinstance(node, IncludeNode)
    assert node.raw_path == "my automations.yaml"


def test_quoted_text_is_not_an_include_directive(tmp_path: Path) -> None:
    """An include tag inside a string is text, not a directive."""
    path = tmp_path / "configuration.yaml"
    path.write_text(
        'note: "use !include fake.yaml"\nautomation: !include automations.yaml\n',
        encoding="utf-8",
    )

    document = YamlLoader().load(path)

    assert document.data["note"] == "use !include fake.yaml"
    assert document.data["automation"] == IncludeNode(IncludeDirective.INCLUDE, "automations.yaml")


def test_loader_rejects_a_non_scalar_include(tmp_path: Path) -> None:
    """An include tag on a mapping is invalid YAML for this module."""
    path = tmp_path / "configuration.yaml"
    path.write_text("value: !include\n  path: target.yaml\n", encoding="utf-8")

    with pytest.raises(YamlLoadError, match="Failed to parse YAML"):
        YamlLoader().load(path)


def test_loader_still_rejects_other_custom_tags(tmp_path: Path) -> None:
    """Tags other than the include directives still fail safe parsing."""
    path = tmp_path / "configuration.yaml"
    path.write_text("token: !secret api_key\n", encoding="utf-8")

    with pytest.raises(YamlLoadError, match="Failed to parse YAML"):
        YamlLoader().load(path)


def test_blank_include_path_is_unresolved() -> None:
    """A blank path does not match the repository root."""
    tree = _repository_tree()
    document = _document("configuration.yaml", _node(IncludeDirective.INCLUDE, "   "))

    reference = resolve_includes(tree, document)[0]

    assert reference.resolved is False
    assert reference.files == ()


def test_document_without_includes_has_no_references() -> None:
    """Ordinary YAML produces an empty resolution result."""
    tree = _repository_tree()
    document = _document("configuration.yaml", {"name": "Kitchen"})

    assert resolve_includes(tree, document) == ()


def _repository_tree() -> ProjectTree:
    """Build a repository tree without reading or writing the filesystem."""
    root = Path("repository")
    relatives = (
        "automations.yaml",
        "configuration.yaml",
        "scripts.yaml",
        "README.md",
        "packages",
        "packages/lighting.yaml",
        "packages/includes",
        "packages/includes/extra.yaml",
        "sensors",
        "sensors/b.yaml",
        "sensors/a.yaml",
        "sensors/readme.md",
        "sensors/nested",
        "sensors/nested/c.yaml",
        "sensors/b.yml",
        "empty",
        "dashboards",
        "dashboards/main.yaml",
    )
    directories = {
        "packages",
        "packages/includes",
        "sensors",
        "sensors/nested",
        "empty",
        "dashboards",
    }
    entries = [
        _entry(root, relative, is_dir=relative in directories) for relative in relatives
    ]
    return ProjectTreeBuilder().build(root, entries)


def _entry(root: Path, relative: str, *, is_dir: bool) -> FilesystemEntry:
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
        modified=datetime(2026, 1, 1, tzinfo=UTC),
    )


def _document(relative: str, data: object) -> YamlDocument:
    """Build a loaded document whose path sits inside the synthetic repository."""
    return YamlDocument(Path("repository") / relative, "", data)


def _node(directive: IncludeDirective, raw_path: str) -> IncludeNode:
    """Build one include node."""
    return IncludeNode(directive=directive, raw_path=raw_path)


def _file(tree: ProjectTree, relative: str) -> ProjectFile:
    """Return one stored file by relative POSIX path."""
    found = {item.relative_path.as_posix(): item for item in project_files(tree)}
    return found[relative]


def _folder(tree: ProjectTree, relative: str) -> object:
    """Return one stored folder by relative POSIX path."""
    for folder in tree.folders:
        if folder.relative_path.as_posix() == relative:
            return folder
    raise KeyError(relative)


def _names(files: tuple[ProjectFile, ...]) -> tuple[str, ...]:
    """Return relative POSIX paths for stored files."""
    return tuple(item.relative_path.as_posix() for item in files)


def _resolved_names(references: tuple[object, ...]) -> tuple[str, ...]:
    """Return the relative path of each resolved file reference."""
    names: list[str] = []
    for reference in references:
        assert isinstance(reference, tuple) or hasattr(reference, "files")
        for item in reference.files:
            names.append(item.relative_path.as_posix())
    return tuple(names)


def _under(tree: ProjectTree, prefix: str) -> tuple[str, ...]:
    """Return stored relative paths below one directory prefix."""
    return tuple(
        item.relative_path.as_posix()
        for item in project_files(tree)
        if item.relative_path.as_posix().startswith(prefix)
    )


def _reject_filesystem(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail when code discovers, stats, opens or loads a file."""

    def rejected(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("include resolution touched the filesystem")

    for name in (
        "exists",
        "is_file",
        "is_dir",
        "stat",
        "lstat",
        "rglob",
        "glob",
        "iterdir",
        "open",
        "read_text",
        "read_bytes",
        "resolve",
    ):
        monkeypatch.setattr(Path, name, rejected)
    monkeypatch.setattr(FilesystemWalker, "walk", rejected)
    monkeypatch.setattr("ha_docgen.project.discovery.discover_project", rejected)
    monkeypatch.setattr("ha_docgen.project.discover_project", rejected)
    monkeypatch.setattr(YamlLoader, "load", rejected)
