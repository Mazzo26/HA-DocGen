"""Pure scanner diagnostics over an existing ProjectTree.

The derivation reads ``project_files()`` and caller-supplied facts.
It does not walk the repository, load YAML, or decide ownership.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from enum import StrEnum

from ..project import ProjectFile, ProjectTree, project_files


class DiagnosticType(StrEnum):
    """Kind of one scanner diagnostic.

    Values sort alphabetically: inventory, unclaimed file, load failure.
    """

    REPOSITORY_INVENTORY = "repository_inventory"
    UNCLAIMED_FILE = "unclaimed_file"
    YAML_LOAD_FAILURE = "yaml_load_failure"


@dataclass(frozen=True, slots=True)
class YamlLoadFailure:
    """One YAML load failure supplied by the caller.

    ``project_file`` is the file the caller attempted to load.
    ``message`` is the failure text the caller already captured.
    """

    project_file: ProjectFile
    message: str


@dataclass(frozen=True, slots=True)
class ScannerDiagnostic:
    """One immutable scan fact.

    ``project_file`` is an existing ``ProjectFile``. Metadata is not copied.
    """

    diagnostic_type: DiagnosticType
    project_file: ProjectFile
    message: str


@dataclass(frozen=True, slots=True)
class ScannerDiagnostics:
    """Deterministic collection of scan facts."""

    diagnostics: tuple[ScannerDiagnostic, ...] = ()


def scanner_diagnostics(
    tree: ProjectTree,
    claim_set: Collection[ProjectFile] = (),
    load_failures: Collection[YamlLoadFailure] = (),
) -> ScannerDiagnostics:
    """Derive scan facts from *tree* and caller-supplied inputs.

    A file is claimed only when its ``ProjectFile`` instance is in
    *claim_set*. Inventory and unclaimed files are the instances from
    ``project_files()``.
    """
    files = project_files(tree)
    records = (
        *_inventory(files),
        *_unclaimed(files, claim_set),
        *_failures(load_failures),
    )
    return ScannerDiagnostics(_ordered(records))


def _inventory(files: tuple[ProjectFile, ...]) -> tuple[ScannerDiagnostic, ...]:
    """Reference every stored file once."""
    return tuple(_record(DiagnosticType.REPOSITORY_INVENTORY, item, "") for item in files)


def _unclaimed(
    files: tuple[ProjectFile, ...],
    claim_set: Collection[ProjectFile],
) -> tuple[ScannerDiagnostic, ...]:
    """Return stored files whose identity is absent from *claim_set*."""
    claimed = {id(item) for item in claim_set}
    pending = (item for item in files if id(item) not in claimed)
    return tuple(_record(DiagnosticType.UNCLAIMED_FILE, item, "") for item in pending)


def _failures(
    load_failures: Collection[YamlLoadFailure],
) -> tuple[ScannerDiagnostic, ...]:
    """Reference each supplied failure without reading the file."""
    return tuple(
        _record(DiagnosticType.YAML_LOAD_FAILURE, item.project_file, item.message)
        for item in load_failures
    )


def _record(
    diagnostic_type: DiagnosticType,
    project_file: ProjectFile,
    message: str,
) -> ScannerDiagnostic:
    """Build one diagnostic around an existing ProjectFile."""
    return ScannerDiagnostic(diagnostic_type, project_file, message)


def _ordered(records: tuple[ScannerDiagnostic, ...]) -> tuple[ScannerDiagnostic, ...]:
    """Sort and drop repeated type, path and message combinations."""
    ordered = sorted(records, key=_sort_key)
    unique: list[ScannerDiagnostic] = []
    seen: set[tuple[str, str, str]] = set()
    for record in ordered:
        key = _sort_key(record)
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return tuple(unique)


def _sort_key(record: ScannerDiagnostic) -> tuple[str, str, str]:
    """Return diagnostic type, relative POSIX path, then message."""
    relative = record.project_file.relative_path.as_posix()
    return (record.diagnostic_type.value, relative, record.message)
