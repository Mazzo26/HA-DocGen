"""Tests for GitHub Actions release version validation."""

from __future__ import annotations

import importlib.util
import io
import tarfile
import zipfile
from pathlib import Path
from types import ModuleType

import pytest

from tools.ha_docgen.version import VERSION

_REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPOSITORY_ROOT / ".github" / "scripts" / "validate_release_version.py"


def _load_script() -> ModuleType:
    """Load the release validation script without treating it as a package."""
    spec = importlib.util.spec_from_file_location("validate_release_version", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def release_script() -> ModuleType:
    """Return the standalone release validation module."""
    return _load_script()


def _metadata(version: str, name: str = "ha-docgen") -> str:
    """Return RFC 822 package metadata."""
    return f"Name: {name}\nVersion: {version}\n"


def _write_wheel(path: Path, version: str, name: str = "ha-docgen") -> None:
    """Write a minimal wheel containing METADATA."""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"ha_docgen-{version}.dist-info/METADATA", _metadata(version, name))


def _write_sdist(path: Path, version: str, name: str = "ha-docgen") -> None:
    """Write a minimal sdist containing PKG-INFO."""
    payload = _metadata(version, name).encode("utf-8")
    with tarfile.open(path, "w:gz") as archive:
        info = tarfile.TarInfo(name=f"ha_docgen-{version}/PKG-INFO")
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))


def test_normalize_tag_strips_version_prefix(release_script: ModuleType) -> None:
    """Release tags encode the application version after a v prefix."""
    assert release_script.normalize_tag("v0.2.0") == "0.2.0"
    assert release_script.normalize_tag("v1.0.0-rc.1") == "1.0.0-rc.1"
    assert release_script.normalize_tag("0.2.0") == "0.2.0"


def test_validate_release_accepts_matching_versions(
    release_script: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tag, package, wheel and sdist must share the application version."""
    monkeypatch.setattr(release_script.importlib.metadata, "version", lambda _name: VERSION)
    _write_wheel(tmp_path / f"ha_docgen-{VERSION}-py3-none-any.whl", VERSION)
    _write_sdist(tmp_path / f"ha_docgen-{VERSION}.tar.gz", VERSION)
    release_script.validate_release(f"v{VERSION}", tmp_path, VERSION)


def test_validate_release_rejects_tag_mismatch(
    release_script: ModuleType,
    tmp_path: Path,
) -> None:
    """A Git tag that does not match VERSION stops the release."""
    with pytest.raises(ValueError, match="Git tag"):
        release_script.validate_release("v9.9.9", tmp_path, VERSION)


def test_validate_release_rejects_wheel_mismatch(
    release_script: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wheel metadata must match VERSION."""
    monkeypatch.setattr(release_script.importlib.metadata, "version", lambda _name: VERSION)
    _write_wheel(tmp_path / "ha_docgen-9.9.9-py3-none-any.whl", "9.9.9")
    _write_sdist(tmp_path / f"ha_docgen-{VERSION}.tar.gz", VERSION)
    with pytest.raises(ValueError, match="wheel metadata"):
        release_script.validate_release(f"v{VERSION}", tmp_path, VERSION)


def test_validate_release_rejects_sdist_mismatch(
    release_script: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sdist metadata must match VERSION."""
    monkeypatch.setattr(release_script.importlib.metadata, "version", lambda _name: VERSION)
    _write_wheel(tmp_path / f"ha_docgen-{VERSION}-py3-none-any.whl", VERSION)
    _write_sdist(tmp_path / "ha_docgen-9.9.9.tar.gz", "9.9.9")
    with pytest.raises(ValueError, match="sdist metadata"):
        release_script.validate_release(f"v{VERSION}", tmp_path, VERSION)


def test_validate_release_rejects_package_metadata_mismatch(
    release_script: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Installed package metadata must match VERSION."""
    monkeypatch.setattr(release_script.importlib.metadata, "version", lambda _name: "9.9.9")
    _write_wheel(tmp_path / f"ha_docgen-{VERSION}-py3-none-any.whl", VERSION)
    _write_sdist(tmp_path / f"ha_docgen-{VERSION}.tar.gz", VERSION)
    with pytest.raises(ValueError, match="package metadata"):
        release_script.validate_release(f"v{VERSION}", tmp_path, VERSION)


def test_read_sdist_version_ignores_egg_info_pkg_info(
    release_script: ModuleType,
    tmp_path: Path,
) -> None:
    """Sdist version comes from the distribution root PKG-INFO only."""
    sdist = tmp_path / f"ha_docgen-{VERSION}.tar.gz"
    root = _metadata(VERSION).encode("utf-8")
    nested = _metadata("9.9.9").encode("utf-8")
    with tarfile.open(sdist, "w:gz") as archive:
        for name, payload in (
            (f"ha_docgen-{VERSION}/PKG-INFO", root),
            (f"ha_docgen-{VERSION}/ha_docgen.egg-info/PKG-INFO", nested),
        ):
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    assert release_script.read_sdist_version(sdist) == VERSION


def test_main_returns_error_on_mismatch(
    release_script: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI exits with status 1 when versions disagree."""
    status = release_script.main(["--tag", "v9.9.9", "--dist-dir", str(tmp_path)])
    captured = capsys.readouterr()
    assert status == 1
    assert "Git tag" in captured.err
