"""Tests for authoritative HA-DocGen version management."""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys
import tarfile
import tomllib
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from ha_docgen import (
    APP_NAME,
    VERSION,
    InvalidVersionError,
    SemanticVersion,
    get_version,
    parse_version,
    validate_version,
)
from ha_docgen import main as cli
from ha_docgen.diagnostics import collect_diagnostics
from ha_docgen.version import __version__ as module_version
from tests.support.paths import REPOSITORY_ROOT

_PYPROJECT = REPOSITORY_ROOT / "pyproject.toml"
_VERSION_SOURCE = REPOSITORY_ROOT / "src" / "ha_docgen" / "version.py"
_DISTRIBUTION_NAME = "ha-docgen"


def test_authoritative_version_is_valid_semver() -> None:
    """The single version constant is a valid semantic version."""
    assert validate_version(VERSION) == VERSION
    assert str(parse_version(VERSION)) == VERSION


def test_public_surfaces_share_the_same_version() -> None:
    """Package, module and retrieval API all expose VERSION."""
    import ha_docgen

    assert get_version() == VERSION
    assert module_version == VERSION
    assert ha_docgen.VERSION == VERSION
    assert ha_docgen.__version__ == VERSION
    assert ha_docgen.get_version() == VERSION


def test_installed_distribution_metadata_matches_application_version() -> None:
    """Package metadata installed in the environment matches VERSION."""
    assert importlib.metadata.version(_DISTRIBUTION_NAME) == VERSION


def test_pyproject_reads_version_from_the_application_module() -> None:
    """Build metadata has no duplicate version string."""
    if not _PYPROJECT.is_file():
        pytest.skip("pyproject.toml is not present until packaging (Phase 2)")
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    assert data["project"]["dynamic"] == ["version"]
    assert "version" not in data["project"]
    assert (
        data["tool"]["setuptools"]["dynamic"]["version"]["attr"]
        == "ha_docgen.version.VERSION"
    )


def test_version_module_does_not_consult_git() -> None:
    """Version discovery stays independent of repository metadata."""
    source = _VERSION_SOURCE.read_text(encoding="utf-8")
    assert "import git" not in source
    assert "subprocess" not in source
    assert "importlib.metadata" not in source


@pytest.mark.parametrize(
    ("value", "expected"),
    (
        ("1.2.3", SemanticVersion(1, 2, 3)),
        ("0.2.0", SemanticVersion(0, 2, 0)),
        ("1.0.0-alpha.1", SemanticVersion(1, 0, 0, prerelease="alpha.1")),
        ("1.0.0+build.5", SemanticVersion(1, 0, 0, build="build.5")),
        (
            "2.0.1-rc.2+exp.sha",
            SemanticVersion(2, 0, 1, prerelease="rc.2", build="exp.sha"),
        ),
    ),
)
def test_parse_version_accepts_semantic_versions(
    value: str,
    expected: SemanticVersion,
) -> None:
    """Supported SemVer forms parse into immutable components."""
    parsed = parse_version(value)
    assert parsed == expected
    assert str(parsed) == value


@pytest.mark.parametrize(
    "value",
    ("1.0", "v1.0.0", "1.0.0.0", "01.0.0", "", "latest"),
)
def test_validate_version_rejects_invalid_values(value: str) -> None:
    """Non-SemVer strings fail with a dedicated error type."""
    with pytest.raises(InvalidVersionError, match="Invalid semantic version"):
        validate_version(value)


def test_cli_version_uses_authoritative_version(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI version output is the application name plus VERSION."""
    monkeypatch.setattr(cli, "load_config", Mock())

    assert cli.main(("--version",)) == cli.EXIT_SUCCESS
    assert capsys.readouterr().out == f"{APP_NAME} {VERSION}\n"


def test_diagnostics_use_authoritative_version() -> None:
    """Runtime diagnostics report the same application version."""
    assert collect_diagnostics().app_version == VERSION


@pytest.mark.integration
def test_built_distributions_use_authoritative_version(tmp_path: Path) -> None:
    """sdist and wheel metadata match VERSION without Git."""
    if not _PYPROJECT.is_file():
        pytest.skip("pyproject.toml is not present until packaging (Phase 2)")
    subprocess.run(
        (sys.executable, "-m", "build", "--sdist", "--wheel", "--outdir", str(tmp_path)),
        check=True,
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
    )
    wheels = tuple(tmp_path.glob("*.whl"))
    sdists = tuple(tmp_path.glob("*.tar.gz"))
    assert len(wheels) == 1
    assert len(sdists) == 1
    assert _metadata_version(wheels[0]) == VERSION
    assert _sdist_version(sdists[0]) == VERSION
    assert VERSION in wheels[0].name
    assert VERSION in sdists[0].name


def _metadata_version(wheel: Path) -> str:
    """Return the Version field from wheel METADATA."""
    with zipfile.ZipFile(wheel) as archive:
        metadata_name = next(
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        )
        text = archive.read(metadata_name).decode("utf-8")
    return _field(text, "Version")


def _sdist_version(sdist: Path) -> str:
    """Return the Version field from sdist PKG-INFO."""
    with tarfile.open(sdist, "r:gz") as archive:
        member = next(name for name in archive.getnames() if name.endswith("PKG-INFO"))
        extracted = archive.extractfile(member)
        assert extracted is not None
        text = extracted.read().decode("utf-8")
    return _field(text, "Version")


def _field(text: str, name: str) -> str:
    """Return one RFC 822 metadata field."""
    prefix = f"{name}: "
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.removeprefix(prefix)
    raise AssertionError(f"Missing metadata field: {name}")
